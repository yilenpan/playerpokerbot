"""Tests for GameSession and action parsing."""

# Add project root to path for imports BEFORE other imports
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.models.game import (
    ActionType,
    ParsedAction,
    GameConfig,
)
from server.models.api import OpponentConfig
from server.game.session import GameSession, GameSessionManager, parse_action


# =============================================================================
# Action Parsing Tests
# =============================================================================


class TestParseAction:
    """Tests for the parse_action function."""

    @pytest.mark.parametrize(
        "response,can_check,expected_type",
        [
            # Explicit action tags
            ("<action>f</action>", False, ActionType.FOLD),
            ("<action>fold</action>", False, ActionType.FOLD),
            ("<action>cc</action>", False, ActionType.CALL),
            ("<action>cc</action>", True, ActionType.CHECK),
            ("<action>call</action>", False, ActionType.CALL),
            ("<action>check</action>", True, ActionType.CHECK),
            # All-in
            ("<action>all-in</action>", False, ActionType.ALL_IN),
            ("<action>allin</action>", False, ActionType.ALL_IN),
            ("<action>shove</action>", False, ActionType.ALL_IN),
        ],
    )
    def test_parse_action_tag(self, response: str, can_check: bool, expected_type: ActionType):
        """Test parsing actions from action tags."""
        action = parse_action(response, can_check, stack=10000)
        assert action.action_type == expected_type

    @pytest.mark.parametrize(
        "response,expected_amount",
        [
            ("<action>cbr 200</action>", 200),
            ("<action>cbr 1000</action>", 1000),
            ("<action>bet 500</action>", 500),
            ("<action>raise 300</action>", 300),
        ],
    )
    def test_parse_action_raise_with_amount(self, response: str, expected_amount: int):
        """Test parsing raise actions with amounts."""
        action = parse_action(response, can_check=False, stack=10000)
        assert action.action_type == ActionType.RAISE
        assert action.amount == expected_amount

    def test_parse_action_with_reasoning(self):
        """Test parsing action with reasoning text."""
        response = """
        Looking at my hand, I have AK suited. The pot odds are good.
        I think I should raise here.
        <action>cbr 400</action>
        """
        action = parse_action(response, can_check=False, stack=10000)
        assert action.action_type == ActionType.RAISE
        assert action.amount == 400

    def test_parse_action_case_insensitive(self):
        """Test action tag parsing is case insensitive."""
        response = "<ACTION>FOLD</ACTION>"
        action = parse_action(response, can_check=False, stack=10000)
        assert action.action_type == ActionType.FOLD

    def test_parse_action_with_whitespace(self):
        """Test action tag parsing with extra whitespace."""
        response = "<action>   fold   </action>"
        action = parse_action(response, can_check=False, stack=10000)
        assert action.action_type == ActionType.FOLD

    def test_parse_action_no_tag_fold_keyword(self):
        """Test fallback to keyword parsing for fold."""
        response = "I should fold here"
        action = parse_action(response, can_check=False, stack=10000)
        assert action.action_type == ActionType.FOLD

    def test_parse_action_no_tag_call_keyword(self):
        """Test fallback to keyword parsing for call."""
        response = "I'll call this bet"
        action = parse_action(response, can_check=False, stack=10000)
        assert action.action_type == ActionType.CALL

    def test_parse_action_no_tag_check_keyword(self):
        """Test fallback to keyword parsing for check."""
        response = "Let me check here"
        action = parse_action(response, can_check=True, stack=10000)
        assert action.action_type == ActionType.CHECK

    def test_parse_action_no_match_defaults_check(self):
        """Test default to check when can check."""
        response = "I'm not sure what to do"
        action = parse_action(response, can_check=True, stack=10000)
        assert action.action_type == ActionType.CHECK

    def test_parse_action_no_match_defaults_fold(self):
        """Test default to fold when cannot check."""
        response = "I'm not sure what to do"
        action = parse_action(response, can_check=False, stack=10000)
        assert action.action_type == ActionType.FOLD

    def test_parse_action_all_in_sets_amount_to_stack(self):
        """Test all-in sets amount to stack size."""
        response = "<action>all-in</action>"
        action = parse_action(response, can_check=False, stack=5000)
        assert action.action_type == ActionType.ALL_IN
        assert action.amount == 5000


# =============================================================================
# GameSession Tests
# =============================================================================


class TestGameSession:
    """Tests for GameSession class."""

    @pytest.fixture
    def opponents(self):
        """Create opponent configs."""
        return [OpponentConfig(name="Bot-1", model="llama2")]

    @pytest.fixture
    def config(self):
        """Create game config."""
        return GameConfig(
            starting_stack=10000,
            small_blind=50,
            big_blind=100,
            num_hands=10,
            turn_timeout_seconds=30,
        )

    @pytest.fixture
    def session(self, opponents, config):
        """Create a game session."""
        return GameSession("test123", opponents, config)

    def test_session_initialization(self, session, opponents):
        """Test session initializes correctly."""
        assert session.session_id == "test123"
        assert session.status == "waiting"
        assert len(session.players) == 2  # Human + 1 opponent

    def test_session_players_setup(self, session):
        """Test player setup."""
        # Human player at index 0
        assert session.players[0].id == 0
        assert session.players[0].name == "You"
        assert session.players[0].player_type == "human"

        # LLM opponent at index 1
        assert session.players[1].id == 1
        assert session.players[1].name == "Bot-1"
        assert session.players[1].player_type == "llm"
        assert session.players[1].model == "llama2"

    def test_session_multiple_opponents(self, config):
        """Test session with multiple opponents."""
        opponents = [
            OpponentConfig(name="Bot-1", model="llama2"),
            OpponentConfig(name="Bot-2", model="mistral"),
            OpponentConfig(name="Bot-3", model="gemma"),
        ]
        session = GameSession("test", opponents, config)

        assert len(session.players) == 4  # Human + 3 opponents

    @pytest.mark.asyncio
    async def test_on_client_connect(self, session, mock_websocket):
        """Test client connection handling."""
        await session.on_client_connect(mock_websocket)

        # WebSocket should be accepted
        assert mock_websocket.accepted is True

        # Should have sent connection ack
        events = mock_websocket.get_sent_events()
        assert len(events) == 1
        assert events[0]["type"] == "connection_ack"
        assert events[0]["session_id"] == "test123"
        assert events[0]["player_id"] == 0

    @pytest.mark.asyncio
    async def test_on_client_disconnect(self, session, mock_websocket):
        """Test client disconnection handling."""
        await session.on_client_connect(mock_websocket)
        await session.on_client_disconnect(mock_websocket)

        # Connection count should be 0
        assert session.ws_manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_receive_human_action(self, session):
        """Test receiving human action."""
        # Simulate waiting for action
        session._action_event.clear()

        await session.receive_human_action("fold")

        assert session._pending_action is not None
        assert session._pending_action.action_type == ActionType.FOLD
        assert session._action_event.is_set()

    @pytest.mark.asyncio
    async def test_receive_human_action_with_amount(self, session):
        """Test receiving human action with amount."""
        await session.receive_human_action("raise", amount=400)

        assert session._pending_action is not None
        assert session._pending_action.action_type == ActionType.RAISE
        assert session._pending_action.amount == 400

    @pytest.mark.asyncio
    async def test_receive_human_action_invalid_type(self, session):
        """Test receiving invalid action type."""
        await session.receive_human_action("invalid_action")

        assert session._pending_action is None

    @pytest.mark.asyncio
    async def test_broadcast(self, session, mock_websocket):
        """Test broadcasting events."""
        await session.on_client_connect(mock_websocket)

        from server.models.events import ErrorEvent

        event = ErrorEvent(code="test", message="Test error")
        await session.broadcast(event)

        events = mock_websocket.get_sent_events()
        # Should have connection_ack + error event
        assert len(events) == 2
        assert events[1]["type"] == "error"
        assert events[1]["code"] == "test"

    @pytest.mark.asyncio
    async def test_end_session(self, session, mock_websocket):
        """Test ending session."""
        await session.on_client_connect(mock_websocket)
        await session.end_session()

        assert session.status == "complete"

        events = mock_websocket.get_sent_events()
        # Should have sent session_complete event
        session_complete = [e for e in events if e["type"] == "session_complete"]
        assert len(session_complete) == 1

    @pytest.mark.asyncio
    async def test_cleanup(self, session, mock_websocket):
        """Test session cleanup."""
        await session.on_client_connect(mock_websocket)
        await session.cleanup()

        # All connections should be closed
        assert session.ws_manager.connection_count == 0


class TestGameSessionLLMAction:
    """Tests for LLM action getting."""

    @pytest.fixture
    def opponents(self):
        """Create opponent configs."""
        return [OpponentConfig(name="Bot-1", model="llama2")]

    @pytest.fixture
    def config(self):
        """Create game config."""
        return GameConfig(
            starting_stack=10000,
            small_blind=50,
            big_blind=100,
            num_hands=10,
            turn_timeout_seconds=30,
        )

    @pytest.fixture
    def session(self, opponents, config):
        """Create a game session."""
        return GameSession("test123", opponents, config)

    def test_build_llm_prompt(self, session):
        """Test building LLM prompt."""
        session.engine.start_hand()
        prompt = session._build_llm_prompt(1)

        assert "Hold'em" in prompt
        assert "Position" in prompt
        assert "Stack" in prompt
        assert "Hole cards" in prompt


# =============================================================================
# GameSessionManager Tests
# =============================================================================


class TestGameSessionManager:
    """Tests for GameSessionManager class."""

    @pytest.fixture
    def manager(self):
        """Create a session manager."""
        return GameSessionManager()

    @pytest.fixture
    def opponents(self):
        """Create opponent configs."""
        return [OpponentConfig(name="Bot-1", model="llama2")]

    @pytest.fixture
    def config(self):
        """Create game config."""
        return GameConfig()

    @pytest.mark.asyncio
    async def test_create_session(self, manager, opponents, config):
        """Test creating a session."""
        session = await manager.create_session(opponents, config)

        assert session is not None
        assert session.session_id is not None
        assert len(session.session_id) == 8  # UUID[:8]
        assert manager.active_session_count == 1

    @pytest.mark.asyncio
    async def test_get_session(self, manager, opponents, config):
        """Test getting a session by ID."""
        session = await manager.create_session(opponents, config)
        session_id = session.session_id

        retrieved = await manager.get_session(session_id)
        assert retrieved is session

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, manager):
        """Test getting non-existent session."""
        result = await manager.get_session("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_remove_session(self, manager, opponents, config):
        """Test removing a session."""
        session = await manager.create_session(opponents, config)
        session_id = session.session_id

        await manager.remove_session(session_id)

        assert manager.active_session_count == 0
        assert await manager.get_session(session_id) is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_session(self, manager):
        """Test removing non-existent session doesn't raise."""
        # Should not raise
        await manager.remove_session("nonexistent")

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, manager, opponents, config):
        """Test creating multiple sessions."""
        session1 = await manager.create_session(opponents, config)
        session2 = await manager.create_session(opponents, config)
        session3 = await manager.create_session(opponents, config)

        assert manager.active_session_count == 3
        assert session1.session_id != session2.session_id
        assert session2.session_id != session3.session_id

    @pytest.mark.asyncio
    async def test_cleanup_all(self, manager, opponents, config):
        """Test cleaning up all sessions."""
        await manager.create_session(opponents, config)
        await manager.create_session(opponents, config)
        await manager.create_session(opponents, config)

        assert manager.active_session_count == 3

        await manager.cleanup_all()

        assert manager.active_session_count == 0

    @pytest.mark.asyncio
    async def test_concurrent_session_creation(self, manager, opponents, config):
        """Test concurrent session creation."""

        async def create():
            return await manager.create_session(opponents, config)

        sessions = await asyncio.gather(*[create() for _ in range(10)])

        assert len(sessions) == 10
        assert manager.active_session_count == 10

        # All session IDs should be unique
        session_ids = [s.session_id for s in sessions]
        assert len(set(session_ids)) == 10


class TestGameSessionIntegration:
    """Integration tests for GameSession flow."""

    @pytest.fixture
    def opponents(self):
        """Create opponent configs."""
        return [OpponentConfig(name="Bot-1", model="llama2")]

    @pytest.fixture
    def config(self):
        """Create game config with short timeout."""
        return GameConfig(
            starting_stack=10000,
            small_blind=50,
            big_blind=100,
            num_hands=1,  # Just one hand
            turn_timeout_seconds=1,  # Short timeout for testing
        )

    @pytest.fixture
    def session(self, opponents, config):
        """Create a game session."""
        return GameSession("test123", opponents, config)

    @pytest.mark.asyncio
    async def test_session_state_after_start(self, session, mock_websocket):
        """Test session state after starting."""
        await session.on_client_connect(mock_websocket)

        # Start without blocking (would need to mock LLM)
        session.status = "in_progress"
        session.engine.start_hand()

        assert session.status == "in_progress"
        assert session.engine.hand_number == 1
