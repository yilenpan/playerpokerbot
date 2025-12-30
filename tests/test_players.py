"""Tests for player implementations."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.players import OllamaPlayer, HumanPlayer
from src.actions import ParsedAction


class TestOllamaPlayerShutdown:
    """Tests for OllamaPlayer shutdown functionality."""

    def test_shutdown_sends_keep_alive_zero(self):
        """shutdown should send a request with keep_alive=0 to unload model."""
        player = OllamaPlayer("TestBot", "test-model")

        with patch('src.players.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = player.shutdown()

        assert result is True
        mock_post.assert_called_once()

        # Verify the request payload
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        payload = call_args[1]['json']
        assert payload['model'] == "test-model"
        assert payload['keep_alive'] == 0

    def test_shutdown_returns_true_on_success(self):
        """shutdown should return True when model unloads successfully."""
        player = OllamaPlayer("TestBot", "test-model")

        with patch('src.players.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = player.shutdown()

        assert result is True

    def test_shutdown_returns_false_on_http_error(self):
        """shutdown should return False when API returns error status."""
        player = OllamaPlayer("TestBot", "test-model")

        with patch('src.players.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response

            result = player.shutdown()

        assert result is False

    def test_shutdown_returns_false_on_connection_error(self):
        """shutdown should return False when connection fails."""
        player = OllamaPlayer("TestBot", "test-model")

        with patch('src.players.requests.post') as mock_post:
            mock_post.side_effect = requests.ConnectionError("Connection refused")

            result = player.shutdown()

        assert result is False

    def test_shutdown_returns_false_on_timeout(self):
        """shutdown should return False when request times out."""
        player = OllamaPlayer("TestBot", "test-model")

        with patch('src.players.requests.post') as mock_post:
            mock_post.side_effect = requests.Timeout("Request timed out")

            result = player.shutdown()

        assert result is False

    def test_shutdown_uses_correct_endpoint(self):
        """shutdown should use the configured endpoint."""
        player = OllamaPlayer("TestBot", "test-model", endpoint="http://custom:1234")

        with patch('src.players.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            player.shutdown()

        call_args = mock_post.call_args
        assert call_args[0][0] == "http://custom:1234/api/generate"


class TestOllamaPlayerGetAction:
    """Tests for OllamaPlayer.get_action error handling."""

    def test_get_action_returns_error_on_api_failure(self):
        """get_action should return error action when API call fails."""
        player = OllamaPlayer("TestBot", "test-model")

        with patch.object(player, '_call_api') as mock_api:
            mock_api.side_effect = requests.ConnectionError("Connection refused")

            action = player.get_action(
                ("Ah", "Kh"), [], 100, 0, 1000, "BTN", 2
            )

        assert action.action_type == "error"
        assert action.error_message is not None

    def test_get_action_returns_error_on_timeout(self):
        """get_action should return error action when request times out."""
        player = OllamaPlayer("TestBot", "test-model")

        with patch.object(player, '_call_api') as mock_api:
            mock_api.side_effect = requests.Timeout("Request timed out")

            action = player.get_action(
                ("Ah", "Kh"), [], 100, 0, 1000, "BTN", 2
            )

        assert action.action_type == "error"
        assert "timed out" in action.error_message.lower()


class TestOllamaPlayerCheckConnection:
    """Tests for OllamaPlayer.check_connection."""

    def test_check_connection_returns_true_when_model_available(self):
        """check_connection should return True when model is listed."""
        player = OllamaPlayer("TestBot", "test-model")

        with patch('src.players.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [{"name": "test-model"}, {"name": "other-model"}]
            }
            mock_get.return_value = mock_response

            result = player.check_connection()

        assert result is True

    def test_check_connection_returns_false_when_model_not_found(self):
        """check_connection should return False when model is not listed."""
        player = OllamaPlayer("TestBot", "test-model")

        with patch('src.players.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [{"name": "other-model"}]
            }
            mock_get.return_value = mock_response

            result = player.check_connection()

        assert result is False

    def test_check_connection_returns_false_on_connection_error(self):
        """check_connection should return False when connection fails."""
        player = OllamaPlayer("TestBot", "test-model")

        with patch('src.players.requests.get') as mock_get:
            mock_get.side_effect = requests.ConnectionError("Connection refused")

            result = player.check_connection()

        assert result is False
