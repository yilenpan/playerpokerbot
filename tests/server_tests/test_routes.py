"""Tests for API routes."""

# Add project root to path for imports BEFORE other imports
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api.routes import router, init_dependencies
from server.game.session import GameSession, GameSessionManager
from server.streaming.ollama_client import OllamaStreamingClient
from server.models.game import GameConfig
from server.models.api import OpponentConfig


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def app():
    """Create a FastAPI app with routes."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager."""
    manager = MagicMock(spec=GameSessionManager)
    manager.active_session_count = 0
    return manager


@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client."""
    client = MagicMock(spec=OllamaStreamingClient)
    return client


@pytest.fixture
def initialized_app(app, mock_session_manager, mock_ollama_client):
    """Create an app with initialized dependencies."""
    init_dependencies(mock_session_manager, mock_ollama_client)
    return app


@pytest.fixture
def initialized_client(initialized_app):
    """Create a test client with initialized dependencies."""
    return TestClient(initialized_app)


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check_not_initialized(self, client):
        """Test health check when not initialized."""
        # Reset global state
        init_dependencies(None, None)

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["ollama_connected"] is False
        assert data["active_sessions"] == 0

    def test_health_check_ollama_connected(
        self, initialized_client, mock_session_manager, mock_ollama_client
    ):
        """Test health check with Ollama connected."""
        mock_ollama_client.check_connection = AsyncMock(return_value=True)
        mock_session_manager.active_session_count = 2

        response = initialized_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["ollama_connected"] is True
        assert data["active_sessions"] == 2

    def test_health_check_ollama_disconnected(
        self, initialized_client, mock_session_manager, mock_ollama_client
    ):
        """Test health check with Ollama disconnected."""
        mock_ollama_client.check_connection = AsyncMock(return_value=False)

        response = initialized_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["ollama_connected"] is False


# =============================================================================
# Models Endpoint Tests
# =============================================================================


class TestModelsEndpoint:
    """Tests for models listing endpoint."""

    def test_list_models_not_initialized(self, client):
        """Test listing models when not initialized."""
        init_dependencies(None, None)

        response = client.get("/models")
        assert response.status_code == 500
        assert "not initialized" in response.json()["detail"]

    def test_list_models_success(
        self, initialized_client, mock_ollama_client
    ):
        """Test listing models successfully."""
        mock_ollama_client.list_models = AsyncMock(
            return_value=[
                {"name": "llama2", "details": {"parameter_size": "7B"}},
                {"name": "mistral", "details": {"parameter_size": "7B"}},
            ]
        )

        response = initialized_client.get("/models")
        assert response.status_code == 200

        data = response.json()
        assert len(data["models"]) == 2
        assert data["models"][0]["name"] == "llama2"
        assert data["models"][0]["size"] == "7B"

    def test_list_models_empty(
        self, initialized_client, mock_ollama_client
    ):
        """Test listing models when none available."""
        mock_ollama_client.list_models = AsyncMock(return_value=[])

        response = initialized_client.get("/models")
        assert response.status_code == 200

        data = response.json()
        assert data["models"] == []


# =============================================================================
# Session Creation Tests
# =============================================================================


class TestSessionCreation:
    """Tests for session creation endpoint."""

    def test_create_session_not_initialized(self, client):
        """Test creating session when not initialized."""
        init_dependencies(None, None)

        response = client.post(
            "/sessions",
            json={
                "opponents": [{"name": "Bot", "model": "llama2"}],
            },
        )
        assert response.status_code == 500
        assert "not initialized" in response.json()["detail"]

    def test_create_session_success(
        self, initialized_client, mock_session_manager
    ):
        """Test successful session creation."""
        mock_session = MagicMock()
        mock_session.session_id = "abc12345"
        mock_session_manager.create_session = AsyncMock(return_value=mock_session)

        response = initialized_client.post(
            "/sessions",
            json={
                "opponents": [{"name": "Bot-1", "model": "llama2"}],
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["session_id"] == "abc12345"
        assert data["websocket_url"] == "/ws/abc12345"
        assert len(data["players"]) == 2  # Human + 1 opponent
        assert data["players"][0]["player_type"] == "human"
        assert data["players"][1]["player_type"] == "llm"

    def test_create_session_multiple_opponents(
        self, initialized_client, mock_session_manager
    ):
        """Test creating session with multiple opponents."""
        mock_session = MagicMock()
        mock_session.session_id = "xyz98765"
        mock_session_manager.create_session = AsyncMock(return_value=mock_session)

        response = initialized_client.post(
            "/sessions",
            json={
                "opponents": [
                    {"name": "Bot-1", "model": "llama2"},
                    {"name": "Bot-2", "model": "mistral"},
                    {"name": "Bot-3", "model": "gemma"},
                ],
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["players"]) == 4  # Human + 3 opponents

    def test_create_session_custom_config(
        self, initialized_client, mock_session_manager
    ):
        """Test creating session with custom configuration."""
        mock_session = MagicMock()
        mock_session.session_id = "custom1"
        mock_session_manager.create_session = AsyncMock(return_value=mock_session)

        response = initialized_client.post(
            "/sessions",
            json={
                "opponents": [{"name": "Bot", "model": "llama2"}],
                "starting_stack": 5000,
                "small_blind": 25,
                "big_blind": 50,
                "num_hands": 5,
                "turn_timeout_seconds": 60,
            },
        )
        assert response.status_code == 200

        # Verify create_session was called with correct config
        call_args = mock_session_manager.create_session.call_args
        config = call_args[0][1]  # Second positional argument
        assert config.starting_stack == 5000
        assert config.small_blind == 25
        assert config.big_blind == 50
        assert config.num_hands == 5
        assert config.turn_timeout_seconds == 60

    def test_create_session_no_opponents(
        self, initialized_client, mock_session_manager
    ):
        """Test creating session with no opponents fails."""
        response = initialized_client.post(
            "/sessions",
            json={
                "opponents": [],
            },
        )
        assert response.status_code == 400
        assert "1-5 opponents" in response.json()["detail"]

    def test_create_session_too_many_opponents(
        self, initialized_client, mock_session_manager
    ):
        """Test creating session with too many opponents fails."""
        response = initialized_client.post(
            "/sessions",
            json={
                "opponents": [
                    {"name": f"Bot-{i}", "model": "llama2"}
                    for i in range(6)
                ],
            },
        )
        assert response.status_code == 400
        assert "1-5 opponents" in response.json()["detail"]


# =============================================================================
# Session Status Tests
# =============================================================================


class TestSessionStatus:
    """Tests for session status endpoint."""

    def test_get_session_not_initialized(self, client):
        """Test getting session when not initialized."""
        init_dependencies(None, None)

        response = client.get("/sessions/abc123")
        assert response.status_code == 500

    def test_get_session_success(
        self, initialized_client, mock_session_manager
    ):
        """Test getting session status successfully."""
        mock_session = MagicMock()
        mock_session.session_id = "abc123"
        mock_session.status = "in_progress"
        mock_session.engine.hand_number = 5
        mock_session.players = [
            MagicMock(stack=9000),
            MagicMock(stack=11000),
        ]
        mock_session_manager.get_session = AsyncMock(return_value=mock_session)

        response = initialized_client.get("/sessions/abc123")
        assert response.status_code == 200

        data = response.json()
        assert data["session_id"] == "abc123"
        assert data["status"] == "in_progress"
        assert data["hand_number"] == 5
        assert data["player_stacks"] == [9000, 11000]

    def test_get_session_not_found(
        self, initialized_client, mock_session_manager
    ):
        """Test getting non-existent session."""
        mock_session_manager.get_session = AsyncMock(return_value=None)

        response = initialized_client.get("/sessions/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


# =============================================================================
# Session Deletion Tests
# =============================================================================


class TestSessionDeletion:
    """Tests for session deletion endpoint."""

    def test_delete_session_not_initialized(self, client):
        """Test deleting session when not initialized."""
        init_dependencies(None, None)

        response = client.delete("/sessions/abc123")
        assert response.status_code == 500

    def test_delete_session_success(
        self, initialized_client, mock_session_manager
    ):
        """Test deleting session successfully."""
        mock_session = MagicMock()
        mock_session.session_id = "abc123"
        mock_session_manager.get_session = AsyncMock(return_value=mock_session)
        mock_session_manager.remove_session = AsyncMock()

        response = initialized_client.delete("/sessions/abc123")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "deleted"

        # Verify remove was called
        mock_session_manager.remove_session.assert_called_once_with("abc123")

    def test_delete_session_not_found(
        self, initialized_client, mock_session_manager
    ):
        """Test deleting non-existent session."""
        mock_session_manager.get_session = AsyncMock(return_value=None)

        response = initialized_client.delete("/sessions/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


# =============================================================================
# Request Validation Tests
# =============================================================================


class TestRequestValidation:
    """Tests for request validation."""

    def test_create_session_missing_opponents(
        self, initialized_client, mock_session_manager
    ):
        """Test creating session without opponents field."""
        response = initialized_client.post(
            "/sessions",
            json={},
        )
        assert response.status_code == 422  # Validation error

    def test_create_session_invalid_opponent(
        self, initialized_client, mock_session_manager
    ):
        """Test creating session with invalid opponent."""
        response = initialized_client.post(
            "/sessions",
            json={
                "opponents": [{"name": "Bot"}],  # Missing model
            },
        )
        assert response.status_code == 422

    def test_create_session_invalid_json(
        self, initialized_client, mock_session_manager
    ):
        """Test creating session with invalid JSON."""
        response = initialized_client.post(
            "/sessions",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422


# =============================================================================
# Integration Tests
# =============================================================================


class TestRouteIntegration:
    """Integration tests for API routes."""

    @pytest.fixture
    def real_manager(self):
        """Create a real session manager."""
        return GameSessionManager()

    @pytest.fixture
    def real_ollama(self):
        """Create a real Ollama client (won't connect)."""
        return OllamaStreamingClient(
            endpoint="http://localhost:11434",
            timeout=5.0,
        )

    def test_full_session_lifecycle(self, app, real_manager, real_ollama):
        """Test creating and deleting a session."""
        init_dependencies(real_manager, real_ollama)
        client = TestClient(app)

        # Create session
        response = client.post(
            "/sessions",
            json={
                "opponents": [{"name": "Bot", "model": "llama2"}],
            },
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Check status
        response = client.get(f"/sessions/{session_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "waiting"

        # Delete session
        response = client.delete(f"/sessions/{session_id}")
        assert response.status_code == 200

        # Verify deleted
        response = client.get(f"/sessions/{session_id}")
        assert response.status_code == 404
