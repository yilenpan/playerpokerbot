"""Tests for game and event models."""

# Add project root to path for imports BEFORE other imports
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import time

import pytest
from pydantic import ValidationError

from server.models.game import (
    Card,
    Street,
    ActionType,
    ParsedAction,
    PlayerState,
    AvailableActions,
    GameState,
    GameConfig,
)
from server.models.events import (
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
    PlayerActionMessage,
    StartHandMessage,
    EndSessionMessage,
    PingMessage,
)


# =============================================================================
# Card Tests
# =============================================================================


class TestCard:
    """Tests for Card model."""

    @pytest.mark.parametrize(
        "rank,suit,expected_str",
        [
            ("A", "s", "As"),
            ("K", "h", "Kh"),
            ("Q", "d", "Qd"),
            ("J", "c", "Jc"),
            ("T", "s", "Ts"),
            ("9", "h", "9h"),
            ("2", "d", "2d"),
        ],
    )
    def test_card_str(self, rank: str, suit: str, expected_str: str):
        """Test card string representation."""
        card = Card(rank=rank, suit=suit)
        assert str(card) == expected_str

    @pytest.mark.parametrize(
        "card_string,expected_rank,expected_suit",
        [
            ("As", "A", "s"),
            ("Kh", "K", "h"),
            ("Qd", "Q", "d"),
            ("Jc", "J", "c"),
            ("Ts", "T", "s"),
            ("9h", "9", "h"),
            ("2d", "2", "d"),
            # Test case insensitivity
            ("as", "A", "s"),
            ("AS", "A", "s"),
            ("aS", "A", "s"),
            # Test with spaces
            (" As ", "A", "s"),
            ("  Kh", "K", "h"),
        ],
    )
    def test_card_from_string(
        self, card_string: str, expected_rank: str, expected_suit: str
    ):
        """Test parsing card from string."""
        card = Card.from_string(card_string)
        assert card.rank == expected_rank
        assert card.suit == expected_suit

    @pytest.mark.parametrize(
        "invalid_string",
        [
            "",
            "A",
            " ",
            "X",
        ],
    )
    def test_card_from_string_invalid(self, invalid_string: str):
        """Test parsing invalid card strings raises ValueError."""
        with pytest.raises(ValueError, match="Invalid card string"):
            Card.from_string(invalid_string)

    def test_card_serialization(self):
        """Test card JSON serialization."""
        card = Card(rank="A", suit="s")
        data = card.model_dump()
        assert data == {"rank": "A", "suit": "s"}

        # Test deserialization
        restored = Card.model_validate(data)
        assert restored.rank == "A"
        assert restored.suit == "s"


# =============================================================================
# Street Tests
# =============================================================================


class TestStreet:
    """Tests for Street enum."""

    def test_street_values(self):
        """Test street enum values."""
        assert Street.PREFLOP.value == "preflop"
        assert Street.FLOP.value == "flop"
        assert Street.TURN.value == "turn"
        assert Street.RIVER.value == "river"
        assert Street.SHOWDOWN.value == "showdown"

    def test_street_is_string_enum(self):
        """Test that Street is a string enum."""
        assert isinstance(Street.PREFLOP, str)
        assert Street.PREFLOP == "preflop"


# =============================================================================
# ActionType Tests
# =============================================================================


class TestActionType:
    """Tests for ActionType enum."""

    def test_action_type_values(self):
        """Test action type enum values."""
        assert ActionType.FOLD.value == "fold"
        assert ActionType.CHECK.value == "check"
        assert ActionType.CALL.value == "call"
        assert ActionType.RAISE.value == "raise"
        assert ActionType.ALL_IN.value == "all_in"

    def test_action_type_is_string_enum(self):
        """Test that ActionType is a string enum."""
        assert isinstance(ActionType.FOLD, str)
        assert ActionType.FOLD == "fold"


# =============================================================================
# ParsedAction Tests
# =============================================================================


class TestParsedAction:
    """Tests for ParsedAction model."""

    def test_fold_action_str(self, fold_action):
        """Test fold action string representation."""
        assert str(fold_action) == "Fold"

    def test_check_action_str(self, check_action):
        """Test check action string representation."""
        assert str(check_action) == "Check"

    def test_call_action_str(self, call_action):
        """Test call action string representation."""
        assert str(call_action) == "Call"

    def test_raise_action_str(self, raise_action):
        """Test raise action string representation."""
        assert str(raise_action) == "Raise 400"

    def test_all_in_action_str(self, all_in_action):
        """Test all-in action string representation."""
        assert str(all_in_action) == "All_in 10000"

    def test_raise_without_amount(self):
        """Test raise action without amount."""
        action = ParsedAction(action_type=ActionType.RAISE)
        assert str(action) == "Raise"

    def test_parsed_action_serialization(self, raise_action):
        """Test ParsedAction JSON serialization."""
        data = raise_action.model_dump()
        assert data == {"action_type": "raise", "amount": 400}

        restored = ParsedAction.model_validate(data)
        assert restored.action_type == ActionType.RAISE
        assert restored.amount == 400


# =============================================================================
# PlayerState Tests
# =============================================================================


class TestPlayerState:
    """Tests for PlayerState model."""

    def test_human_player_state(self, sample_player_state):
        """Test human player state creation."""
        assert sample_player_state.id == 0
        assert sample_player_state.name == "TestPlayer"
        assert sample_player_state.player_type == "human"
        assert sample_player_state.model is None
        assert sample_player_state.stack == 10000
        assert sample_player_state.current_bet == 100
        assert sample_player_state.is_active is True
        assert sample_player_state.is_busted is False

    def test_llm_player_state(self, sample_llm_player_state):
        """Test LLM player state creation."""
        assert sample_llm_player_state.id == 1
        assert sample_llm_player_state.name == "GPT-Bot"
        assert sample_llm_player_state.player_type == "llm"
        assert sample_llm_player_state.model == "llama2"
        assert sample_llm_player_state.stack == 9900
        assert sample_llm_player_state.current_bet == 200

    def test_player_state_with_hole_cards(self, hole_cards):
        """Test player state with hole cards."""
        card1, card2 = hole_cards
        player = PlayerState(
            id=0,
            name="Player",
            player_type="human",
            stack=10000,
            hole_cards=[card1, card2],
        )
        assert player.hole_cards is not None
        assert len(player.hole_cards) == 2
        assert player.hole_cards[0].rank == "A"

    def test_player_state_defaults(self):
        """Test player state default values."""
        player = PlayerState(
            id=0,
            name="Player",
            player_type="human",
            stack=10000,
        )
        assert player.current_bet == 0
        assert player.hole_cards is None
        assert player.is_active is True
        assert player.is_busted is False
        assert player.last_action is None


# =============================================================================
# AvailableActions Tests
# =============================================================================


class TestAvailableActions:
    """Tests for AvailableActions model."""

    def test_available_actions_defaults(self):
        """Test available actions default values."""
        actions = AvailableActions()
        assert actions.can_fold is True
        assert actions.can_check is False
        assert actions.can_call is False
        assert actions.call_amount == 0
        assert actions.can_raise is True
        assert actions.min_raise == 0
        assert actions.max_raise == 0

    def test_available_actions_custom(self, sample_available_actions):
        """Test custom available actions."""
        assert sample_available_actions.can_fold is True
        assert sample_available_actions.can_check is False
        assert sample_available_actions.can_call is True
        assert sample_available_actions.call_amount == 100
        assert sample_available_actions.can_raise is True
        assert sample_available_actions.min_raise == 200
        assert sample_available_actions.max_raise == 10000

    def test_check_scenario(self):
        """Test available actions when player can check."""
        actions = AvailableActions(
            can_fold=False,
            can_check=True,
            can_call=False,
            call_amount=0,
            can_raise=True,
            min_raise=100,
            max_raise=5000,
        )
        assert actions.can_check is True
        assert actions.can_call is False


# =============================================================================
# GameState Tests
# =============================================================================


class TestGameState:
    """Tests for GameState model."""

    def test_game_state_creation(self, sample_game_state):
        """Test game state creation."""
        assert sample_game_state.session_id == "abc123"
        assert sample_game_state.hand_number == 1
        assert sample_game_state.street == Street.FLOP
        assert sample_game_state.pot == 300
        assert len(sample_game_state.community_cards) == 3
        assert sample_game_state.button_position == 0
        assert sample_game_state.current_actor == 0
        assert len(sample_game_state.players) == 2

    def test_game_state_serialization(self, sample_game_state):
        """Test game state JSON serialization."""
        data = sample_game_state.model_dump()
        assert data["session_id"] == "abc123"
        assert data["street"] == "flop"
        assert len(data["players"]) == 2

        # Test round-trip
        restored = GameState.model_validate(data)
        assert restored.session_id == sample_game_state.session_id
        assert restored.street == sample_game_state.street


# =============================================================================
# GameConfig Tests
# =============================================================================


class TestGameConfig:
    """Tests for GameConfig model."""

    def test_game_config_defaults(self):
        """Test game config default values."""
        config = GameConfig()
        assert config.starting_stack == 10000
        assert config.small_blind == 50
        assert config.big_blind == 100
        assert config.num_hands == 10
        assert config.turn_timeout_seconds == 30

    def test_game_config_custom(self, sample_game_config):
        """Test custom game config."""
        assert sample_game_config.starting_stack == 10000
        assert sample_game_config.small_blind == 50
        assert sample_game_config.big_blind == 100


# =============================================================================
# Server to Client Event Tests
# =============================================================================


class TestServerEvents:
    """Tests for server-to-client events."""

    def test_connection_ack_event(self):
        """Test ConnectionAckEvent."""
        event = ConnectionAckEvent(session_id="abc123", player_id=0)
        assert event.type == "connection_ack"
        assert event.session_id == "abc123"
        assert event.player_id == 0

    def test_game_state_event(self, sample_game_state):
        """Test GameStateEvent."""
        event = GameStateEvent(state=sample_game_state)
        assert event.type == "game_state"
        assert event.state.session_id == "abc123"

    def test_game_state_update_event(self, community_cards, sample_available_actions):
        """Test GameStateUpdateEvent."""
        event = GameStateUpdateEvent(
            hand_number=1,
            street="flop",
            pot=300,
            current_actor=0,
            community_cards=community_cards,
            player_stacks=[10000, 9900],
            player_bets=[100, 200],
            last_actions=["Call", "Raise 200"],
            available_actions=sample_available_actions,
        )
        assert event.type == "game_state_update"
        assert event.hand_number == 1
        assert event.street == "flop"

    def test_your_turn_event(self, sample_available_actions):
        """Test YourTurnEvent."""
        event = YourTurnEvent(available_actions=sample_available_actions)
        assert event.type == "your_turn"
        assert event.available_actions.can_call is True

    def test_thinking_start_event(self):
        """Test ThinkingStartEvent."""
        event = ThinkingStartEvent(player_id=1, player_name="Bot-1")
        assert event.type == "thinking_start"
        assert event.player_id == 1
        assert event.player_name == "Bot-1"

    def test_thinking_token_event(self):
        """Test ThinkingTokenEvent."""
        before = time.time()
        event = ThinkingTokenEvent(player_id=1, token="Hello")
        after = time.time()

        assert event.type == "thinking_token"
        assert event.player_id == 1
        assert event.token == "Hello"
        assert before <= event.timestamp <= after

    def test_thinking_complete_event(self, raise_action):
        """Test ThinkingCompleteEvent."""
        event = ThinkingCompleteEvent(
            player_id=1,
            action=raise_action,
            full_text="I will raise <action>cbr 400</action>",
            duration_ms=1500,
        )
        assert event.type == "thinking_complete"
        assert event.player_id == 1
        assert event.action.action_type == ActionType.RAISE
        assert event.duration_ms == 1500

    def test_timer_start_event(self):
        """Test TimerStartEvent."""
        before = time.time()
        event = TimerStartEvent(player_id=0, total_seconds=30)
        after = time.time()

        assert event.type == "timer_start"
        assert event.player_id == 0
        assert event.total_seconds == 30
        assert before <= event.timestamp <= after

    def test_timer_tick_event(self):
        """Test TimerTickEvent."""
        event = TimerTickEvent(player_id=0, remaining_seconds=15)
        assert event.type == "timer_tick"
        assert event.player_id == 0
        assert event.remaining_seconds == 15

    def test_timer_expired_event(self):
        """Test TimerExpiredEvent."""
        event = TimerExpiredEvent(player_id=0, action_taken="fold")
        assert event.type == "timer_expired"
        assert event.player_id == 0
        assert event.action_taken == "fold"

    def test_hand_complete_event(self, sample_cards):
        """Test HandCompleteEvent."""
        event = HandCompleteEvent(
            winners=[0],
            amounts=[500],
            revealed_cards={0: sample_cards[:2], 1: sample_cards[2:4]},
        )
        assert event.type == "hand_complete"
        assert event.winners == [0]
        assert event.amounts == [500]
        assert len(event.revealed_cards) == 2

    def test_session_complete_event(self):
        """Test SessionCompleteEvent."""
        event = SessionCompleteEvent(
            final_stacks=[15000, 5000],
            hands_played=10,
        )
        assert event.type == "session_complete"
        assert event.final_stacks == [15000, 5000]
        assert event.hands_played == 10

    def test_error_event(self):
        """Test ErrorEvent."""
        event = ErrorEvent(code="invalid_action", message="Cannot fold when checking is free")
        assert event.type == "error"
        assert event.code == "invalid_action"
        assert event.message == "Cannot fold when checking is free"


# =============================================================================
# Client to Server Message Tests
# =============================================================================


class TestClientMessages:
    """Tests for client-to-server messages."""

    def test_player_action_message(self):
        """Test PlayerActionMessage."""
        msg = PlayerActionMessage(action_type="raise", amount=400)
        assert msg.type == "player_action"
        assert msg.action_type == "raise"
        assert msg.amount == 400

    def test_player_action_message_no_amount(self):
        """Test PlayerActionMessage without amount."""
        msg = PlayerActionMessage(action_type="fold")
        assert msg.type == "player_action"
        assert msg.action_type == "fold"
        assert msg.amount is None

    def test_start_hand_message(self):
        """Test StartHandMessage."""
        msg = StartHandMessage()
        assert msg.type == "start_hand"

    def test_end_session_message(self):
        """Test EndSessionMessage."""
        msg = EndSessionMessage()
        assert msg.type == "end_session"

    def test_ping_message(self):
        """Test PingMessage."""
        msg = PingMessage()
        assert msg.type == "ping"


# =============================================================================
# Event Serialization Tests
# =============================================================================


class TestEventSerialization:
    """Tests for event JSON serialization."""

    def test_all_events_serialize_to_json(self, sample_game_state, sample_available_actions):
        """Test that all events can be serialized to JSON."""
        events = [
            ConnectionAckEvent(session_id="abc", player_id=0),
            GameStateEvent(state=sample_game_state),
            YourTurnEvent(available_actions=sample_available_actions),
            ThinkingStartEvent(player_id=1, player_name="Bot"),
            ThinkingTokenEvent(player_id=1, token="test"),
            ThinkingCompleteEvent(
                player_id=1,
                action=ParsedAction(action_type=ActionType.FOLD),
                full_text="folding",
                duration_ms=100,
            ),
            TimerStartEvent(player_id=0, total_seconds=30),
            TimerTickEvent(player_id=0, remaining_seconds=20),
            TimerExpiredEvent(player_id=0, action_taken="fold"),
            HandCompleteEvent(winners=[0], amounts=[100], revealed_cards={}),
            SessionCompleteEvent(final_stacks=[10000], hands_played=5),
            ErrorEvent(code="error", message="test"),
        ]

        for event in events:
            # Should not raise
            json_str = event.model_dump_json()
            assert isinstance(json_str, str)

            # Should contain type field
            data = event.model_dump()
            assert "type" in data

    def test_events_include_type_field(self):
        """Test that all events include a type field for routing."""
        event = ConnectionAckEvent(session_id="abc", player_id=0)
        data = event.model_dump()
        assert data["type"] == "connection_ack"
