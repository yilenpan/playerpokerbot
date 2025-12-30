"""PokerKit engine wrapper."""

import random
from typing import Optional

from pokerkit import NoLimitTexasHoldem, Automation

from ..models.game import (
    Card,
    Street,
    ActionType,
    ParsedAction,
    PlayerState,
    AvailableActions,
    GameState,
    GameConfig,
)


class PokerEngine:
    """Wrapper around PokerKit for game state management."""

    def __init__(self, config: GameConfig, num_players: int):
        self.config = config
        self.num_players = num_players
        self.stacks = [config.starting_stack] * num_players
        self.button = 0
        self.hand_number = 0

        # Current hand state
        self._state = None
        self._hole_cards: list[tuple[str, str]] = []
        self._board: list[str] = []
        self._deck: list = []

    def start_hand(self) -> bool:
        """Start a new hand. Returns False if hand cannot be started."""
        self.hand_number += 1
        self.button = (self.button + 1) % self.num_players

        # Check if we can start
        active_players = sum(1 for s in self.stacks if s > 0)
        if active_players < 2:
            return False

        try:
            self._state = NoLimitTexasHoldem.create_state(
                automations=(
                    Automation.ANTE_POSTING,
                    Automation.BET_COLLECTION,
                    Automation.BLIND_OR_STRADDLE_POSTING,
                    Automation.CARD_BURNING,
                    Automation.HOLE_DEALING,
                    Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
                    Automation.HAND_KILLING,
                    Automation.CHIPS_PUSHING,
                    Automation.CHIPS_PULLING,
                ),
                ante_trimming_status=True,
                raw_antes={-1: 0},
                raw_blinds_or_straddles=(self.config.small_blind, self.config.big_blind),
                min_bet=self.config.big_blind,
                raw_starting_stacks=self.stacks.copy(),
                player_count=self.num_players,
            )
        except Exception:
            return False

        # Get hole cards - use repr() for short format like "As", not str() which gives "ACE OF SPADES (As)"
        self._hole_cards = []
        for i in range(self.num_players):
            cards = self._state.hole_cards[i]
            if cards and len(cards) >= 2:
                self._hole_cards.append((repr(cards[0]), repr(cards[1])))
            else:
                raise RuntimeError(f"Failed to deal hole cards for player {i}")

        # Prepare deck for community cards
        dealable = list(self._state.get_dealable_cards())
        random.shuffle(dealable)
        self._deck = dealable
        self._board = []

        return True

    def deal_street(self) -> Optional[Street]:
        """Deal community cards for next street. Returns new street or None."""
        if self._state is None or not self._state.status:
            return None

        # Can only deal cards when no action is pending
        if self._state.actor_index is not None:
            return None

        current_street = self.get_street()

        if current_street == Street.PREFLOP and len(self._board) == 0:
            # Deal flop
            for _ in range(3):
                card = self._deck.pop()
                self._board.append(repr(card))
                self._state.deal_board(card)
            return Street.FLOP

        elif current_street == Street.FLOP and len(self._board) == 3:
            # Deal turn
            card = self._deck.pop()
            self._board.append(repr(card))
            self._state.deal_board(card)
            return Street.TURN

        elif current_street == Street.TURN and len(self._board) == 4:
            # Deal river
            card = self._deck.pop()
            self._board.append(repr(card))
            self._state.deal_board(card)
            return Street.RIVER

        return None

    def execute_action(self, action: ParsedAction) -> bool:
        """Execute an action. Returns True if successful."""
        if self._state is None:
            return False

        try:
            if action.action_type == ActionType.FOLD:
                self._state.fold()
            elif action.action_type in (ActionType.CHECK, ActionType.CALL):
                self._state.check_or_call()
            elif action.action_type == ActionType.RAISE:
                self._state.complete_bet_or_raise_to(action.amount)
            elif action.action_type == ActionType.ALL_IN:
                actor = self._state.actor_index
                stack = self._state.stacks[actor] + self._state.bets[actor]
                self._state.complete_bet_or_raise_to(stack)
            return True
        except Exception:
            # Fallback chain
            try:
                self._state.check_or_call()
                return True
            except Exception:
                try:
                    self._state.fold()
                    return True
                except Exception:
                    return False

    def get_street(self) -> Street:
        """Get current street."""
        if self._state is None:
            return Street.PREFLOP

        board_count = len(self._board)
        if board_count == 0:
            return Street.PREFLOP
        elif board_count == 3:
            return Street.FLOP
        elif board_count == 4:
            return Street.TURN
        elif board_count >= 5:
            return Street.RIVER
        return Street.PREFLOP

    def get_actor(self) -> Optional[int]:
        """Get current actor index, or None if no action needed."""
        if self._state is None:
            return None
        return self._state.actor_index

    def is_hand_complete(self) -> bool:
        """Check if hand is complete."""
        if self._state is None:
            return True
        return not self._state.status

    def needs_cards(self) -> bool:
        """Check if we need to deal more community cards."""
        if self._state is None or not self._state.status:
            return False

        # If no actor but hand is still active, we need cards
        if self._state.actor_index is None and self._state.status:
            return True
        return False

    def get_available_actions(self) -> Optional[AvailableActions]:
        """Get available actions for current actor."""
        if self._state is None or self._state.actor_index is None:
            return None

        actor = self._state.actor_index
        current_bet = max(self._state.bets) if self._state.bets else 0
        player_bet = self._state.bets[actor] if self._state.bets else 0
        to_call = current_bet - player_bet
        stack = self._state.stacks[actor]

        can_check = to_call == 0
        min_raise_attr = getattr(
            self._state, "min_completion_betting_or_raising_to_amount", None
        )
        min_raise = (
            min_raise_attr
            if min_raise_attr is not None
            else current_bet + self.config.big_blind
        )
        max_raise = stack + player_bet

        return AvailableActions(
            can_fold=not can_check,
            can_check=can_check,
            can_call=not can_check,
            call_amount=to_call,
            can_raise=stack > 0 and min_raise_attr is not None,
            min_raise=min_raise,
            max_raise=max_raise,
        )

    def get_hole_cards(self, player_idx: int) -> tuple[str, str]:
        """Get hole cards for a player."""
        if 0 <= player_idx < len(self._hole_cards):
            return self._hole_cards[player_idx]
        return ("??", "??")

    def get_board(self) -> list[str]:
        """Get community cards."""
        return self._board.copy()

    def get_pot(self) -> int:
        """Get current pot size."""
        if self._state is None:
            return 0
        return self._state.total_pot_amount if hasattr(self._state, "total_pot_amount") else 0

    def get_player_bet(self, player_idx: int) -> int:
        """Get a player's current bet."""
        if self._state is None or not self._state.bets:
            return 0
        if 0 <= player_idx < len(self._state.bets):
            return self._state.bets[player_idx]
        return 0

    def get_player_stack(self, player_idx: int) -> int:
        """Get a player's current stack."""
        if self._state is None:
            return self.stacks[player_idx] if 0 <= player_idx < len(self.stacks) else 0
        if 0 <= player_idx < len(self._state.stacks):
            return self._state.stacks[player_idx]
        return 0

    def finalize_hand(self) -> dict:
        """Finalize hand and update stacks. Returns result info."""
        if self._state is None:
            return {"winners": [], "amounts": [], "revealed_cards": {}}

        # Update stacks
        for i in range(self.num_players):
            self.stacks[i] = self._state.stacks[i]

        # For now, simple winner detection
        # In a real implementation, we'd track the actual winners from PokerKit
        result = {
            "winners": [],
            "amounts": [],
            "revealed_cards": {},
        }

        return result

    def get_position_name(self, player_idx: int) -> str:
        """Get position name for a player."""
        positions_2 = ["SB", "BB"]
        positions_3 = ["BTN", "SB", "BB"]
        positions_4 = ["BTN", "CO", "SB", "BB"]
        positions_6 = ["BTN", "CO", "HJ", "LJ", "SB", "BB"]

        if self.num_players == 2:
            positions = positions_2
        elif self.num_players == 3:
            positions = positions_3
        elif self.num_players <= 4:
            positions = positions_4
        else:
            positions = positions_6[: self.num_players]

        rel_pos = (player_idx - self.button) % self.num_players
        return positions[rel_pos] if rel_pos < len(positions) else f"P{player_idx}"

    def build_game_state(
        self,
        session_id: str,
        players: list[PlayerState],
    ) -> GameState:
        """Build complete game state for client."""
        # Update player states with current info
        for i, player in enumerate(players):
            player.stack = self.get_player_stack(i)
            player.current_bet = self.get_player_bet(i)
            if player.player_type == "human" and i < len(self._hole_cards):
                c1, c2 = self._hole_cards[i]
                player.hole_cards = [Card.from_string(c1), Card.from_string(c2)]
            player.is_active = self.stacks[i] > 0

        return GameState(
            session_id=session_id,
            hand_number=self.hand_number,
            street=self.get_street(),
            pot=self.get_pot(),
            community_cards=[Card.from_string(c) for c in self._board],
            button_position=self.button,
            current_actor=self.get_actor(),
            players=players,
            available_actions=self.get_available_actions() if self.get_actor() == 0 else None,
        )
