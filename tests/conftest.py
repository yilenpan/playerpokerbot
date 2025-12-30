"""Root conftest for path setup and shared fixtures.

This file is loaded first by pytest and ensures the project root
is on sys.path before any test modules are imported.
"""

import sys
from pathlib import Path

# Add project root to path IMMEDIATELY
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import json
import os
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

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
from server.models.api import OpponentConfig
from server.models.events import (
    ConnectionAckEvent,
    GameStateEvent,
    ThinkingTokenEvent,
    TimerTickEvent,
)


# =============================================================================
# Pytest Configuration
# =============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Card and Game State Fixtures
# =============================================================================


@pytest.fixture
def sample_cards() -> list[Card]:
    """Sample list of cards."""
    return [
        Card(rank="A", suit="s"),
        Card(rank="K", suit="h"),
        Card(rank="Q", suit="d"),
        Card(rank="J", suit="c"),
        Card(rank="T", suit="s"),
    ]


@pytest.fixture
def hole_cards() -> tuple[Card, Card]:
    """Sample hole cards."""
    return Card(rank="A", suit="s"), Card(rank="K", suit="s")


@pytest.fixture
def community_cards() -> list[Card]:
    """Sample community cards (flop)."""
    return [
        Card(rank="Q", suit="h"),
        Card(rank="J", suit="d"),
        Card(rank="T", suit="c"),
    ]


@pytest.fixture
def sample_player_state() -> PlayerState:
    """Sample player state."""
    return PlayerState(
        id=0,
        name="TestPlayer",
        player_type="human",
        stack=10000,
        current_bet=100,
        is_active=True,
        is_busted=False,
    )


@pytest.fixture
def sample_llm_player_state() -> PlayerState:
    """Sample LLM player state."""
    return PlayerState(
        id=1,
        name="GPT-Bot",
        player_type="llm",
        model="llama2",
        stack=9900,
        current_bet=200,
        is_active=True,
        is_busted=False,
    )


@pytest.fixture
def sample_available_actions() -> AvailableActions:
    """Sample available actions."""
    return AvailableActions(
        can_fold=True,
        can_check=False,
        can_call=True,
        call_amount=100,
        can_raise=True,
        min_raise=200,
        max_raise=10000,
    )


@pytest.fixture
def sample_game_state(
    sample_player_state, sample_llm_player_state, community_cards, sample_available_actions
) -> GameState:
    """Sample complete game state."""
    return GameState(
        session_id="abc123",
        hand_number=1,
        street=Street.FLOP,
        pot=300,
        community_cards=community_cards,
        button_position=0,
        current_actor=0,
        players=[sample_player_state, sample_llm_player_state],
        available_actions=sample_available_actions,
    )


@pytest.fixture
def sample_game_config() -> GameConfig:
    """Sample game configuration."""
    return GameConfig(
        starting_stack=10000,
        small_blind=50,
        big_blind=100,
        num_hands=10,
        turn_timeout_seconds=30,
    )


@pytest.fixture
def sample_opponent_configs() -> list[OpponentConfig]:
    """Sample opponent configurations."""
    return [
        OpponentConfig(name="Bot-1", model="llama2", temperature=0.6),
        OpponentConfig(name="Bot-2", model="mistral", temperature=0.7),
    ]


# =============================================================================
# Mock WebSocket Fixture
# =============================================================================


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.accepted = False
        self.closed = False
        self.sent_messages: list[str] = []
        self.receive_queue: list[str] = []
        self._should_fail = False

    async def accept(self) -> None:
        """Accept the connection."""
        self.accepted = True

    async def close(self) -> None:
        """Close the connection."""
        self.closed = True

    async def send_text(self, message: str) -> None:
        """Send a text message."""
        if self._should_fail:
            raise ConnectionError("Connection closed")
        self.sent_messages.append(message)

    async def receive_text(self) -> str:
        """Receive a text message."""
        if self.receive_queue:
            return self.receive_queue.pop(0)
        raise asyncio.TimeoutError("No message")

    def queue_message(self, message: str) -> None:
        """Queue a message to be received."""
        self.receive_queue.append(message)

    def set_should_fail(self, should_fail: bool) -> None:
        """Set whether send should fail."""
        self._should_fail = should_fail

    def get_sent_events(self) -> list[dict]:
        """Parse sent messages as JSON events."""
        return [json.loads(msg) for msg in self.sent_messages]


@pytest.fixture
def mock_websocket() -> MockWebSocket:
    """Create a mock WebSocket."""
    return MockWebSocket()


@pytest.fixture
def mock_websocket_factory():
    """Factory to create multiple mock WebSockets."""

    def factory() -> MockWebSocket:
        return MockWebSocket()

    return factory


# =============================================================================
# Mock Ollama Client Fixture
# =============================================================================


class MockOllamaResponse:
    """Mock Ollama streaming response."""

    def __init__(self, tokens: list[str], include_action: bool = True):
        self.tokens = tokens
        self.include_action = include_action

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def raise_for_status(self):
        pass

    async def aiter_lines(self):
        """Yield mock response lines."""
        for token in self.tokens:
            data = {"message": {"content": token}, "done": False}
            yield json.dumps(data)

        # Final message
        final_data = {"message": {"content": ""}, "done": True}
        yield json.dumps(final_data)


@pytest.fixture
def mock_ollama_success_response():
    """Mock successful Ollama response with action tag."""
    tokens = [
        "Looking at my ",
        "hand, I have ",
        "AK suited. ",
        "The pot is 300. ",
        "I should raise. ",
        "<action>",
        "cbr 400",
        "</action>",
    ]
    return MockOllamaResponse(tokens)


@pytest.fixture
def mock_ollama_fold_response():
    """Mock Ollama response with fold action."""
    tokens = ["This hand is weak. ", "I should fold. ", "<action>f</action>"]
    return MockOllamaResponse(tokens)


@pytest.fixture
def mock_ollama_check_response():
    """Mock Ollama response with check/call action."""
    tokens = ["Let me check here. ", "<action>cc</action>"]
    return MockOllamaResponse(tokens)


# =============================================================================
# Async Helpers
# =============================================================================


@pytest.fixture
def async_callback_tracker():
    """Track async callback invocations."""

    class CallbackTracker:
        def __init__(self):
            self.calls: list[Any] = []

        async def callback(self, *args, **kwargs) -> None:
            self.calls.append((args, kwargs))

        def get_call_args(self) -> list[tuple]:
            return [call[0] for call in self.calls]

    return CallbackTracker()


# =============================================================================
# Parsed Action Fixtures
# =============================================================================


@pytest.fixture
def fold_action() -> ParsedAction:
    """Fold action."""
    return ParsedAction(action_type=ActionType.FOLD)


@pytest.fixture
def check_action() -> ParsedAction:
    """Check action."""
    return ParsedAction(action_type=ActionType.CHECK)


@pytest.fixture
def call_action() -> ParsedAction:
    """Call action."""
    return ParsedAction(action_type=ActionType.CALL)


@pytest.fixture
def raise_action() -> ParsedAction:
    """Raise action."""
    return ParsedAction(action_type=ActionType.RAISE, amount=400)


@pytest.fixture
def all_in_action() -> ParsedAction:
    """All-in action."""
    return ParsedAction(action_type=ActionType.ALL_IN, amount=10000)
