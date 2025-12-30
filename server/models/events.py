"""WebSocket event models."""

import time
from typing import Literal, Optional
from pydantic import BaseModel, Field

from .game import GameState, AvailableActions, ParsedAction, Card


# =============================================================================
# Server to Client Events
# =============================================================================


class ConnectionAckEvent(BaseModel):
    """Connection acknowledged."""

    type: Literal["connection_ack"] = "connection_ack"
    session_id: str
    player_id: int


class GameStateEvent(BaseModel):
    """Full game state snapshot."""

    type: Literal["game_state"] = "game_state"
    state: GameState


class GameStateUpdateEvent(BaseModel):
    """Incremental game state update."""

    type: Literal["game_state_update"] = "game_state_update"
    hand_number: int
    street: str
    pot: int
    current_actor: Optional[int]
    community_cards: list[Card]
    player_stacks: list[int]
    player_bets: list[int]
    last_actions: list[Optional[str]]
    available_actions: Optional[AvailableActions] = None


class YourTurnEvent(BaseModel):
    """Prompt human player for action."""

    type: Literal["your_turn"] = "your_turn"
    available_actions: AvailableActions


class ThinkingStartEvent(BaseModel):
    """LLM started thinking."""

    type: Literal["thinking_start"] = "thinking_start"
    player_id: int
    player_name: str


class ThinkingTokenEvent(BaseModel):
    """Single token from LLM thinking stream."""

    type: Literal["thinking_token"] = "thinking_token"
    player_id: int
    token: str
    timestamp: float = Field(default_factory=time.time)


class ThinkingCompleteEvent(BaseModel):
    """LLM finished thinking."""

    type: Literal["thinking_complete"] = "thinking_complete"
    player_id: int
    action: ParsedAction
    full_text: str
    duration_ms: int


class TimerStartEvent(BaseModel):
    """Turn timer started."""

    type: Literal["timer_start"] = "timer_start"
    player_id: int
    total_seconds: int
    timestamp: float = Field(default_factory=time.time)


class TimerTickEvent(BaseModel):
    """Timer update."""

    type: Literal["timer_tick"] = "timer_tick"
    player_id: int
    remaining_seconds: int


class TimerExpiredEvent(BaseModel):
    """Timer expired, auto-action taken."""

    type: Literal["timer_expired"] = "timer_expired"
    player_id: int
    action_taken: str


class HandCompleteEvent(BaseModel):
    """Hand finished."""

    type: Literal["hand_complete"] = "hand_complete"
    winners: list[int]
    amounts: list[int]
    revealed_cards: dict[int, list[Card]]  # player_id -> cards


class SessionCompleteEvent(BaseModel):
    """Session ended."""

    type: Literal["session_complete"] = "session_complete"
    final_stacks: list[int]
    hands_played: int


class ErrorEvent(BaseModel):
    """Error notification."""

    type: Literal["error"] = "error"
    code: str
    message: str


# =============================================================================
# Client to Server Messages
# =============================================================================


class PlayerActionMessage(BaseModel):
    """Human player's action."""

    type: Literal["player_action"] = "player_action"
    action_type: str  # fold, check, call, raise, all_in
    amount: Optional[int] = None


class StartHandMessage(BaseModel):
    """Request to start next hand."""

    type: Literal["start_hand"] = "start_hand"


class EndSessionMessage(BaseModel):
    """Request to end session."""

    type: Literal["end_session"] = "end_session"


class PingMessage(BaseModel):
    """Keep-alive ping."""

    type: Literal["ping"] = "ping"
