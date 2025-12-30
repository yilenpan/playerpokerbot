"""Tests for PokerEngine."""

# Add project root to path for imports BEFORE other imports
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import MagicMock, patch

import pytest

from server.models.game import (
    Card,
    Street,
    ActionType,
    ParsedAction,
    PlayerState,
    GameConfig,
)
from server.game.engine import PokerEngine


# =============================================================================
# PokerEngine Tests
# =============================================================================


class TestPokerEngineInitialization:
    """Tests for PokerEngine initialization."""

    @pytest.fixture
    def config(self):
        """Create a game config."""
        return GameConfig(
            starting_stack=10000,
            small_blind=50,
            big_blind=100,
            num_hands=10,
            turn_timeout_seconds=30,
        )

    def test_engine_initialization(self, config):
        """Test engine initializes correctly."""
        engine = PokerEngine(config, num_players=3)

        assert engine.config == config
        assert engine.num_players == 3
        assert len(engine.stacks) == 3
        assert all(s == 10000 for s in engine.stacks)
        assert engine.button == 0
        assert engine.hand_number == 0

    def test_engine_initialization_different_player_counts(self, config):
        """Test engine with different player counts."""
        for num in [2, 3, 4, 5, 6]:
            engine = PokerEngine(config, num_players=num)
            assert len(engine.stacks) == num


class TestPokerEngineHandManagement:
    """Tests for hand management."""

    @pytest.fixture
    def engine(self, sample_game_config):
        """Create an engine instance."""
        return PokerEngine(sample_game_config, num_players=3)

    def test_start_hand_increments_hand_number(self, engine):
        """Test that start_hand increments hand number."""
        assert engine.hand_number == 0
        engine.start_hand()
        assert engine.hand_number == 1
        engine.start_hand()
        assert engine.hand_number == 2

    def test_start_hand_rotates_button(self, engine):
        """Test that button rotates."""
        assert engine.button == 0
        engine.start_hand()
        assert engine.button == 1
        engine.start_hand()
        assert engine.button == 2
        engine.start_hand()
        assert engine.button == 0  # Wraps around

    def test_start_hand_returns_true(self, engine):
        """Test start_hand returns True when successful."""
        result = engine.start_hand()
        assert result is True

    def test_start_hand_deals_hole_cards(self, engine):
        """Test that hole cards are dealt."""
        engine.start_hand()

        for i in range(3):
            cards = engine.get_hole_cards(i)
            assert len(cards) == 2
            # Cards should be real card strings (not ??)
            assert cards[0] != "??"
            assert cards[1] != "??"

    def test_start_hand_insufficient_players(self, sample_game_config):
        """Test start_hand returns False with insufficient players."""
        engine = PokerEngine(sample_game_config, num_players=3)
        # Set all but one player to 0 chips
        engine.stacks = [10000, 0, 0]

        result = engine.start_hand()
        assert result is False

    def test_hand_not_complete_initially(self, engine):
        """Test hand is not complete after start."""
        engine.start_hand()
        assert engine.is_hand_complete() is False

    def test_get_street_preflop_initially(self, engine):
        """Test street is preflop initially."""
        engine.start_hand()
        assert engine.get_street() == Street.PREFLOP


class TestPokerEngineDealStreet:
    """Tests for dealing community cards."""

    @pytest.fixture
    def engine(self, sample_game_config):
        """Create an engine with a hand started."""
        engine = PokerEngine(sample_game_config, num_players=2)
        engine.start_hand()
        return engine

    def _complete_betting_round(self, engine):
        """Complete current betting round by calling/checking."""
        while engine.get_actor() is not None and not engine.is_hand_complete():
            action = ParsedAction(action_type=ActionType.CALL)
            engine.execute_action(action)

    def test_deal_flop(self, engine):
        """Test dealing the flop after preflop betting."""
        self._complete_betting_round(engine)  # Complete preflop
        street = engine.deal_street()
        assert street == Street.FLOP
        assert len(engine.get_board()) == 3

    def test_deal_turn(self, engine):
        """Test dealing the turn."""
        self._complete_betting_round(engine)  # Complete preflop
        engine.deal_street()  # Flop
        self._complete_betting_round(engine)  # Complete flop betting
        street = engine.deal_street()
        assert street == Street.TURN
        assert len(engine.get_board()) == 4

    def test_deal_river(self, engine):
        """Test dealing the river."""
        self._complete_betting_round(engine)  # Preflop
        engine.deal_street()  # Flop
        self._complete_betting_round(engine)  # Flop betting
        engine.deal_street()  # Turn
        self._complete_betting_round(engine)  # Turn betting
        street = engine.deal_street()
        assert street == Street.RIVER
        assert len(engine.get_board()) == 5

    def test_deal_street_returns_none_when_action_needed(self, engine):
        """Test deal_street returns None when betting action is needed."""
        # Preflop with action pending should return None
        result = engine.deal_street()
        assert result is None


class TestPokerEngineActionExecution:
    """Tests for action execution."""

    @pytest.fixture
    def engine(self, sample_game_config):
        """Create an engine with a hand started."""
        engine = PokerEngine(sample_game_config, num_players=2)
        engine.start_hand()
        return engine

    def test_execute_fold(self, engine):
        """Test executing fold action."""
        action = ParsedAction(action_type=ActionType.FOLD)
        result = engine.execute_action(action)
        assert result is True

    def test_execute_check_or_call(self, engine):
        """Test executing check/call action."""
        action = ParsedAction(action_type=ActionType.CALL)
        result = engine.execute_action(action)
        assert result is True

    def test_execute_raise(self, engine):
        """Test executing raise action."""
        # First call
        action = ParsedAction(action_type=ActionType.CALL)
        engine.execute_action(action)

        # Then raise
        action = ParsedAction(action_type=ActionType.RAISE, amount=300)
        result = engine.execute_action(action)
        assert result is True

    def test_execute_all_in(self, engine):
        """Test executing all-in action."""
        action = ParsedAction(action_type=ActionType.ALL_IN, amount=10000)
        result = engine.execute_action(action)
        assert result is True

    def test_execute_action_fallback(self, engine):
        """Test action execution falls back on error."""
        # Try an invalid raise (too small) - should fall back
        action = ParsedAction(action_type=ActionType.RAISE, amount=1)
        result = engine.execute_action(action)
        # Should still return True due to fallback
        assert result is True


class TestPokerEngineStateQueries:
    """Tests for state query methods."""

    @pytest.fixture
    def engine(self, sample_game_config):
        """Create an engine with a hand started."""
        engine = PokerEngine(sample_game_config, num_players=2)
        engine.start_hand()
        return engine

    def test_get_actor(self, engine):
        """Test getting current actor."""
        actor = engine.get_actor()
        # First actor in heads-up should be determined by PokerKit
        assert actor in [0, 1]

    def test_get_pot(self, engine):
        """Test getting pot size."""
        pot = engine.get_pot()
        # Initial pot should include blinds
        assert pot > 0

    def test_get_player_bet(self, engine):
        """Test getting player's current bet."""
        bet = engine.get_player_bet(0)
        # Should be a blind amount initially
        assert bet >= 0

    def test_get_player_stack(self, engine):
        """Test getting player's stack."""
        stack = engine.get_player_stack(0)
        # Stack should be less than starting due to blinds
        assert stack <= 10000
        assert stack > 0

    def test_get_available_actions(self, engine):
        """Test getting available actions."""
        actions = engine.get_available_actions()
        assert actions is not None
        # Basic structure checks
        assert hasattr(actions, "can_fold")
        assert hasattr(actions, "can_check")
        assert hasattr(actions, "can_call")
        assert hasattr(actions, "can_raise")

    def test_get_available_actions_no_actor(self, sample_game_config):
        """Test get_available_actions returns None when no actor."""
        engine = PokerEngine(sample_game_config, num_players=2)
        # Don't start a hand
        actions = engine.get_available_actions()
        assert actions is None

    def test_get_hole_cards_invalid_index(self, engine):
        """Test get_hole_cards with invalid index."""
        cards = engine.get_hole_cards(99)
        assert cards == ("??", "??")

    def test_get_board_copy(self, engine):
        """Test get_board returns a copy."""
        # Complete preflop betting first
        while engine.get_actor() is not None and not engine.is_hand_complete():
            action = ParsedAction(action_type=ActionType.CALL)
            engine.execute_action(action)
        engine.deal_street()  # Deal flop
        board1 = engine.get_board()
        board2 = engine.get_board()
        assert board1 == board2
        assert board1 is not board2  # Different objects

    def test_needs_cards_initially_false(self, engine):
        """Test needs_cards is initially False (action needed)."""
        # At preflop, action is needed, not cards
        assert engine.needs_cards() is False


class TestPokerEnginePositions:
    """Tests for position name calculation."""

    def test_position_names_2_players(self, sample_game_config):
        """Test position names for 2 players."""
        engine = PokerEngine(sample_game_config, num_players=2)
        engine.button = 0

        assert engine.get_position_name(0) == "SB"
        assert engine.get_position_name(1) == "BB"

    def test_position_names_3_players(self, sample_game_config):
        """Test position names for 3 players."""
        engine = PokerEngine(sample_game_config, num_players=3)
        engine.button = 0

        assert engine.get_position_name(0) == "BTN"
        assert engine.get_position_name(1) == "SB"
        assert engine.get_position_name(2) == "BB"

    def test_position_names_4_players(self, sample_game_config):
        """Test position names for 4 players."""
        engine = PokerEngine(sample_game_config, num_players=4)
        engine.button = 0

        assert engine.get_position_name(0) == "BTN"
        assert engine.get_position_name(1) == "CO"
        assert engine.get_position_name(2) == "SB"
        assert engine.get_position_name(3) == "BB"


class TestPokerEngineFinalizeHand:
    """Tests for hand finalization."""

    @pytest.fixture
    def engine(self, sample_game_config):
        """Create an engine."""
        return PokerEngine(sample_game_config, num_players=2)

    def test_finalize_hand_returns_result(self, engine):
        """Test finalize_hand returns result dict."""
        engine.start_hand()
        result = engine.finalize_hand()

        assert "winners" in result
        assert "amounts" in result
        assert "revealed_cards" in result

    def test_finalize_hand_no_state(self, engine):
        """Test finalize_hand with no active state."""
        result = engine.finalize_hand()
        assert result == {"winners": [], "amounts": [], "revealed_cards": {}}


class TestPokerEngineBuildGameState:
    """Tests for building game state."""

    @pytest.fixture
    def engine(self, sample_game_config):
        """Create an engine with a hand started."""
        engine = PokerEngine(sample_game_config, num_players=2)
        engine.start_hand()
        return engine

    @pytest.fixture
    def players(self):
        """Create player states."""
        return [
            PlayerState(id=0, name="Human", player_type="human", stack=10000),
            PlayerState(id=1, name="Bot", player_type="llm", model="llama2", stack=10000),
        ]

    def test_build_game_state(self, engine, players):
        """Test building game state."""
        state = engine.build_game_state("session123", players)

        assert state.session_id == "session123"
        assert state.hand_number == 1
        assert state.street == Street.PREFLOP
        assert len(state.players) == 2

    def test_build_game_state_updates_stacks(self, engine, players):
        """Test that build_game_state updates player stacks."""
        state = engine.build_game_state("session123", players)

        # Stacks should be updated from engine
        for player in state.players:
            assert player.stack == engine.get_player_stack(player.id)

    def test_build_game_state_includes_hole_cards_for_human(self, engine, players):
        """Test that hole cards are included for human player."""
        state = engine.build_game_state("session123", players)

        human_player = state.players[0]
        assert human_player.hole_cards is not None
        assert len(human_player.hole_cards) == 2

    def test_build_game_state_with_community_cards(self, engine, players):
        """Test game state includes community cards."""
        # Complete preflop betting first
        while engine.get_actor() is not None and not engine.is_hand_complete():
            action = ParsedAction(action_type=ActionType.CALL)
            engine.execute_action(action)
        engine.deal_street()  # Deal flop
        state = engine.build_game_state("session123", players)

        assert len(state.community_cards) == 3


class TestPokerEngineIntegration:
    """Integration tests for full hand flow."""

    @pytest.fixture
    def engine(self, sample_game_config):
        """Create an engine."""
        return PokerEngine(sample_game_config, num_players=2)

    def test_complete_hand_with_fold(self, engine):
        """Test a complete hand ending with fold."""
        engine.start_hand()

        # Fold immediately
        action = ParsedAction(action_type=ActionType.FOLD)
        engine.execute_action(action)

        # Hand should be complete
        assert engine.is_hand_complete() is True

    def test_complete_hand_to_showdown(self, engine):
        """Test a hand going to showdown."""
        engine.start_hand()

        # Play through all streets with check/call
        while not engine.is_hand_complete():
            if engine.needs_cards():
                engine.deal_street()
            elif engine.get_actor() is not None:
                action = ParsedAction(action_type=ActionType.CALL)
                engine.execute_action(action)

        assert engine.is_hand_complete() is True

    def test_multiple_hands(self, engine):
        """Test playing multiple hands."""
        for i in range(3):
            result = engine.start_hand()
            assert result is True
            assert engine.hand_number == i + 1

            # Fold to end hand
            action = ParsedAction(action_type=ActionType.FOLD)
            engine.execute_action(action)
            engine.finalize_hand()
