"""Game session management."""

import asyncio
import re
import time
import uuid
from typing import Optional

from ..config import settings
from ..models.game import (
    Card,
    Street,
    ActionType,
    ParsedAction,
    PlayerState,
    GameState,
    GameConfig,
)
from ..models.events import (
    ConnectionAckEvent,
    GameStateEvent,
    GameStateUpdateEvent,
    YourTurnEvent,
    ThinkingStartEvent,
    ThinkingTokenEvent,
    ThinkingCompleteEvent,
    TimerStartEvent,
    TimerTickEvent,
    TimerExpiredEvent,
    HandCompleteEvent,
    SessionCompleteEvent,
    ErrorEvent,
)
from ..models.api import OpponentConfig
from ..websocket_manager import WebSocketManager
from ..streaming import OllamaStreamingClient, TokenBatcher
from .engine import PokerEngine
from .timer import TurnTimer


# Action parsing regex (from original codebase)
RE_ACTION_TAG = re.compile(r"<action>\s*(.+?)\s*</action>", re.IGNORECASE | re.DOTALL)
RE_FOLD = re.compile(r"\b(f|fold)\b", re.IGNORECASE)
RE_CC = re.compile(r"\b(cc|call|check)\b", re.IGNORECASE)
RE_CBR = re.compile(r"\b(?:cbr|bet|raise)\s*(\d+)", re.IGNORECASE)
RE_ALL_IN = re.compile(r"\b(?:all.?in|allin|shove)\b", re.IGNORECASE)


def parse_action(response: str, can_check: bool, stack: int) -> ParsedAction:
    """Parse action from LLM response."""
    match = RE_ACTION_TAG.search(response)
    text = match.group(1).strip() if match else response

    if RE_ALL_IN.search(text):
        return ParsedAction(action_type=ActionType.ALL_IN, amount=stack)
    if RE_FOLD.search(text):
        return ParsedAction(action_type=ActionType.FOLD)
    if RE_CC.search(text):
        return ParsedAction(action_type=ActionType.CHECK if can_check else ActionType.CALL)

    match = RE_CBR.search(text)
    if match:
        return ParsedAction(action_type=ActionType.RAISE, amount=int(match.group(1)))

    # Default
    return ParsedAction(action_type=ActionType.CHECK if can_check else ActionType.FOLD)


class GameSession:
    """Manages a single poker game session."""

    def __init__(
        self,
        session_id: str,
        opponents: list[OpponentConfig],
        config: GameConfig,
    ):
        self.session_id = session_id
        self.config = config
        self.status = "waiting"  # waiting, in_progress, complete

        # Players: human at index 0, then opponents
        self.players: list[PlayerState] = []
        self._setup_players(opponents)

        # Components
        self.ws_manager = WebSocketManager()
        self.ollama_client = OllamaStreamingClient()
        self.engine = PokerEngine(config, len(self.players))
        self.turn_timer = TurnTimer(config.turn_timeout_seconds)

        # State
        self._pending_action: Optional[ParsedAction] = None
        self._action_event = asyncio.Event()
        self._last_actions: list[Optional[str]] = [None] * len(self.players)

    def _setup_players(self, opponents: list[OpponentConfig]) -> None:
        """Initialize player list."""
        # Human player at index 0
        self.players.append(
            PlayerState(
                id=0,
                name="You",
                player_type="human",
                stack=self.config.starting_stack,
            )
        )

        # LLM opponents
        for i, opp in enumerate(opponents):
            self.players.append(
                PlayerState(
                    id=i + 1,
                    name=opp.name,
                    player_type="llm",
                    model=opp.model,
                    stack=self.config.starting_stack,
                )
            )

    async def broadcast(self, event) -> None:
        """Broadcast event to all connected clients."""
        await self.ws_manager.broadcast(event)

    async def on_client_connect(self, websocket) -> None:
        """Handle new client connection."""
        await self.ws_manager.connect(websocket)

        # Send connection ack
        await self.ws_manager.send_event(
            websocket,
            ConnectionAckEvent(session_id=self.session_id, player_id=0),
        )

        # Always send initial game state (even before first hand starts)
        state = self._build_initial_state()
        await self.ws_manager.send_event(websocket, GameStateEvent(state=state))

    def _build_initial_state(self) -> GameState:
        """Build initial game state before hand starts."""
        players_state = []
        for player in self.players:
            players_state.append(
                PlayerState(
                    id=player.id,
                    name=player.name,
                    player_type=player.player_type,
                    model=player.model,
                    stack=player.stack,
                    current_bet=0,
                    is_active=True,
                    hole_cards=[],
                    last_action=None,
                )
            )

        return GameState(
            session_id=self.session_id,
            hand_number=0,
            street=Street.PREFLOP,
            pot=0,
            community_cards=[],
            button_position=0,
            current_actor=None,
            players=players_state,
            available_actions=None,
        )

    async def on_client_disconnect(self, websocket) -> None:
        """Handle client disconnection."""
        await self.ws_manager.disconnect(websocket)

    async def start_session(self) -> None:
        """Start the game session."""
        self.status = "in_progress"
        try:
            await self.play_hand()
        except Exception as e:
            import traceback
            print(f"ERROR in game session: {e}")
            traceback.print_exc()
            await self.broadcast(
                ErrorEvent(code="game_error", message=str(e))
            )

    async def play_hand(self) -> None:
        """Play a single hand."""
        if not self.engine.start_hand():
            await self.end_session()
            return

        # Reset last actions
        self._last_actions = [None] * len(self.players)

        # Broadcast initial state
        state = self.engine.build_game_state(self.session_id, self.players)
        await self.broadcast(GameStateEvent(state=state))

        # Main game loop
        while not self.engine.is_hand_complete():
            # Check if we need to deal cards
            if self.engine.needs_cards():
                new_street = self.engine.deal_street()
                if new_street:
                    await self._broadcast_state_update()

            actor = self.engine.get_actor()
            if actor is None:
                continue

            # Get action from player
            if actor == 0:
                action = await self._get_human_action()
            else:
                action = await self._get_llm_action(actor)

            if action is None:
                continue

            # Execute action
            self._last_actions[actor] = str(action)
            self.engine.execute_action(action)

            # Broadcast update
            await self._broadcast_state_update()

        # Hand complete
        result = self.engine.finalize_hand()
        await self.broadcast(
            HandCompleteEvent(
                winners=result["winners"],
                amounts=result["amounts"],
                revealed_cards={
                    k: [Card.from_string(c) for c in v]
                    for k, v in result.get("revealed_cards", {}).items()
                },
            )
        )

        # Check if session should continue
        if self.engine.hand_number >= self.config.num_hands:
            await self.end_session()
        else:
            # Wait a moment, then start next hand
            await asyncio.sleep(2)
            await self.play_hand()

    async def _get_human_action(self) -> Optional[ParsedAction]:
        """Get action from human player with timer."""
        available = self.engine.get_available_actions()
        if not available:
            return None

        # Notify it's human's turn
        await self.broadcast(YourTurnEvent(available_actions=available))

        # Start timer
        await self.broadcast(
            TimerStartEvent(
                player_id=0,
                total_seconds=self.config.turn_timeout_seconds,
            )
        )

        async def on_timeout():
            """Handle timeout - auto fold."""
            self._pending_action = ParsedAction(action_type=ActionType.FOLD)
            self._action_event.set()
            await self.broadcast(TimerExpiredEvent(player_id=0, action_taken="fold"))

        async def on_tick(remaining: int):
            """Send timer tick."""
            await self.broadcast(TimerTickEvent(player_id=0, remaining_seconds=remaining))

        await self.turn_timer.start(on_timeout=on_timeout, on_tick=on_tick)

        # Wait for action
        self._action_event.clear()
        await self._action_event.wait()

        # Cancel timer
        await self.turn_timer.cancel()

        action = self._pending_action
        self._pending_action = None
        return action

    async def receive_human_action(self, action_type: str, amount: Optional[int] = None) -> None:
        """Receive action from human player via WebSocket."""
        # Map action type string to enum
        type_map = {
            "fold": ActionType.FOLD,
            "check": ActionType.CHECK,
            "call": ActionType.CALL,
            "raise": ActionType.RAISE,
            "all_in": ActionType.ALL_IN,
        }

        action_enum = type_map.get(action_type.lower())
        if action_enum is None:
            return

        self._pending_action = ParsedAction(action_type=action_enum, amount=amount)
        self._action_event.set()

    async def _get_llm_action(self, player_idx: int) -> Optional[ParsedAction]:
        """Get action from LLM player with streaming."""
        player = self.players[player_idx]
        if player.model is None:
            return ParsedAction(action_type=ActionType.FOLD)

        # Notify thinking started
        await self.broadcast(
            ThinkingStartEvent(player_id=player_idx, player_name=player.name)
        )

        start_time = time.time()
        full_response = ""

        # Build prompt
        prompt = self._build_llm_prompt(player_idx)

        # Create token batcher
        async def broadcast_token(token: str):
            await self.broadcast(ThinkingTokenEvent(player_id=player_idx, token=token))

        batcher = TokenBatcher(broadcast_token, batch_size=5, max_delay_ms=50)

        try:
            full_response = await self.ollama_client.generate_streaming(
                model=player.model,
                prompt=prompt,
                on_token=batcher.add_token,
                temperature=0.6,
            )
            await batcher.flush()  # Flush remaining tokens

        except Exception as e:
            await self.broadcast(
                ErrorEvent(code="ollama_error", message=f"LLM error: {str(e)}")
            )
            return ParsedAction(action_type=ActionType.FOLD)

        # Parse action
        available = self.engine.get_available_actions()
        can_check = available.can_check if available else False
        stack = self.engine.get_player_stack(player_idx)
        action = parse_action(full_response, can_check, stack)

        duration_ms = int((time.time() - start_time) * 1000)

        # Notify thinking complete
        await self.broadcast(
            ThinkingCompleteEvent(
                player_id=player_idx,
                action=action,
                full_text=full_response,
                duration_ms=duration_ms,
            )
        )

        return action

    def _build_llm_prompt(self, player_idx: int) -> str:
        """Build prompt for LLM player."""
        hole_cards = self.engine.get_hole_cards(player_idx)
        board = self.engine.get_board()
        pot = self.engine.get_pot()
        available = self.engine.get_available_actions()
        stack = self.engine.get_player_stack(player_idx)
        position = self.engine.get_position_name(player_idx)

        to_call = available.call_amount if available else 0
        can_check = available.can_check if available else False

        c1, c2 = hole_cards
        lines = [
            f"Playing {len(self.players)}-handed No-Limit Hold'em.",
            f"Position: {position}",
            f"Stack: {stack} chips",
            "",
            f"Hole cards: {c1} {c2}",
        ]

        if board:
            lines.append(f"Board: {' '.join(board)}")
        else:
            lines.append("Preflop")

        lines.extend(["", f"Pot: {pot} chips"])

        if to_call > 0:
            lines.append(f"To call: {to_call} chips")
            lines.append(f"Actions: Fold, Call {to_call}, Raise")
        else:
            lines.append("Actions: Check, Bet")

        return "\n".join(lines)

    async def _broadcast_state_update(self) -> None:
        """Broadcast incremental state update."""
        state = self.engine.build_game_state(self.session_id, self.players)

        await self.broadcast(
            GameStateUpdateEvent(
                hand_number=state.hand_number,
                street=state.street.value,
                pot=state.pot,
                current_actor=state.current_actor,
                community_cards=state.community_cards,
                player_stacks=[p.stack for p in state.players],
                player_bets=[p.current_bet for p in state.players],
                last_actions=self._last_actions,
                available_actions=state.available_actions,
            )
        )

    async def end_session(self) -> None:
        """End the game session."""
        self.status = "complete"

        await self.broadcast(
            SessionCompleteEvent(
                final_stacks=[p.stack for p in self.players],
                hands_played=self.engine.hand_number,
            )
        )

    async def cleanup(self) -> None:
        """Cleanup session resources."""
        await self.turn_timer.cancel()
        await self.ws_manager.close_all()


class GameSessionManager:
    """Manages all active game sessions."""

    def __init__(self):
        self._sessions: dict[str, GameSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        opponents: list[OpponentConfig],
        config: GameConfig,
    ) -> GameSession:
        """Create a new game session."""
        async with self._lock:
            session_id = str(uuid.uuid4())[:8]
            session = GameSession(session_id, opponents, config)
            self._sessions[session_id] = session
            return session

    async def get_session(self, session_id: str) -> Optional[GameSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    async def remove_session(self, session_id: str) -> None:
        """Remove and cleanup a session."""
        async with self._lock:
            if session_id in self._sessions:
                await self._sessions[session_id].cleanup()
                del self._sessions[session_id]

    @property
    def active_session_count(self) -> int:
        """Number of active sessions."""
        return len(self._sessions)

    async def cleanup_all(self) -> None:
        """Cleanup all sessions."""
        async with self._lock:
            for session in self._sessions.values():
                await session.cleanup()
            self._sessions.clear()
