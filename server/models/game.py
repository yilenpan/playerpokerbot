"""Game state models."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class Street(str, Enum):
    """Betting round."""

    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"


class ActionType(str, Enum):
    """Player action types."""

    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"
    ALL_IN = "all_in"


class Card(BaseModel):
    """Playing card."""

    rank: str  # 2-9, T, J, Q, K, A
    suit: str  # c, d, h, s

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

    @classmethod
    def from_string(cls, s: str) -> "Card":
        """Parse card from string like 'As' or 'Th'."""
        s = s.strip()
        if len(s) >= 2:
            return cls(rank=s[0].upper(), suit=s[1].lower())
        raise ValueError(f"Invalid card string: {s}")


class ParsedAction(BaseModel):
    """Parsed poker action."""

    action_type: ActionType
    amount: Optional[int] = None

    def __str__(self) -> str:
        if self.action_type in (ActionType.FOLD, ActionType.CHECK, ActionType.CALL):
            return self.action_type.value.capitalize()
        elif self.amount:
            return f"{self.action_type.value.capitalize()} {self.amount}"
        return self.action_type.value.capitalize()


class PlayerState(BaseModel):
    """Player state within a hand."""

    id: int
    name: str
    player_type: str  # "human" or "llm"
    model: Optional[str] = None  # For LLM players
    stack: int
    current_bet: int = 0
    hole_cards: Optional[list[Card]] = None
    is_active: bool = True  # Still in this hand
    is_busted: bool = False  # Out of chips
    last_action: Optional[str] = None


class AvailableActions(BaseModel):
    """Actions available to the current actor."""

    can_fold: bool = True
    can_check: bool = False
    can_call: bool = False
    call_amount: int = 0
    can_raise: bool = True
    min_raise: int = 0
    max_raise: int = 0


class GameState(BaseModel):
    """Complete game state for client."""

    session_id: str
    hand_number: int
    street: Street
    pot: int
    community_cards: list[Card]
    button_position: int
    current_actor: Optional[int]
    players: list[PlayerState]
    available_actions: Optional[AvailableActions] = None


class GameConfig(BaseModel):
    """Game configuration."""

    starting_stack: int = 10000
    small_blind: int = 50
    big_blind: int = 100
    num_hands: int = 10
    turn_timeout_seconds: int = 30
