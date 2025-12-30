"""Tests for OllamaStreamingClient."""

# Add project root to path for imports BEFORE other imports
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.streaming.ollama_client import OllamaStreamingClient, SYSTEM_PROMPT


# =============================================================================
# Mock HTTP Response Helpers
# =============================================================================


class MockAsyncIterator:
    """Mock async iterator for streaming responses."""

    def __init__(self, lines: list[str]):
        self.lines = lines
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.lines):
            raise StopAsyncIteration
        line = self.lines[self.index]
        self.index += 1
        return line


class MockStreamResponse:
    """Mock streaming HTTP response."""

    def __init__(self, lines: list[str], status_code: int = 200):
        self.lines = lines
        self.status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def aiter_lines(self):
        return MockAsyncIterator(self.lines)


class MockHTTPClient:
    """Mock httpx.AsyncClient."""

    def __init__(self, responses: dict = None):
        self.responses = responses or {}
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url: str, **kwargs):
        self.requests.append(("GET", url, kwargs))
        if url in self.responses:
            return self.responses[url]
        return MagicMock(status_code=200, json=lambda: {"models": []})

    async def post(self, url: str, **kwargs):
        self.requests.append(("POST", url, kwargs))
        if url in self.responses:
            return self.responses[url]
        return MagicMock(
            status_code=200,
            json=lambda: {"message": {"content": "test response"}},
        )

    def stream(self, method: str, url: str, **kwargs):
        self.requests.append((method, url, kwargs))
        if url in self.responses:
            return self.responses[url]
        # Default streaming response
        lines = [
            json.dumps({"message": {"content": "test"}, "done": False}),
            json.dumps({"message": {"content": ""}, "done": True}),
        ]
        return MockStreamResponse(lines)


# =============================================================================
# OllamaStreamingClient Tests
# =============================================================================


class TestOllamaStreamingClient:
    """Tests for OllamaStreamingClient."""

    @pytest.fixture
    def client(self):
        """Create a client instance."""
        return OllamaStreamingClient(
            endpoint="http://localhost:11434",
            timeout=30.0,
        )

    @pytest.mark.asyncio
    async def test_check_connection_success(self, client):
        """Test successful connection check."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_http = MockHTTPClient(
            responses={"http://localhost:11434/api/tags": mock_response}
        )

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await client.check_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_check_connection_failure(self, client):
        """Test failed connection check."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await client.check_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_list_models_success(self, client):
        """Test listing models successfully."""
        models_data = [
            {"name": "llama2", "details": {"parameter_size": "7B"}},
            {"name": "mistral", "details": {"parameter_size": "7B"}},
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"models": models_data}

        mock_http = MockHTTPClient(
            responses={"http://localhost:11434/api/tags": mock_response}
        )

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await client.list_models()
            assert len(result) == 2
            assert result[0]["name"] == "llama2"

    @pytest.mark.asyncio
    async def test_list_models_empty(self, client):
        """Test listing models when none available."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"models": []}

        mock_http = MockHTTPClient(
            responses={"http://localhost:11434/api/tags": mock_response}
        )

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await client.list_models()
            assert result == []

    @pytest.mark.asyncio
    async def test_list_models_error(self, client):
        """Test listing models on error."""

        async def mock_get(*args, **kwargs):
            raise Exception("Connection refused")

        mock_http = AsyncMock()
        mock_http.get = mock_get
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await client.list_models()
            assert result == []

    @pytest.mark.asyncio
    async def test_generate_streaming_basic(self, client):
        """Test basic streaming generation."""
        tokens = ["Hello", " ", "World", "!"]
        lines = []
        for token in tokens:
            lines.append(json.dumps({"message": {"content": token}, "done": False}))
        lines.append(json.dumps({"message": {"content": ""}, "done": True}))

        mock_stream = MockStreamResponse(lines)
        mock_http = MockHTTPClient(
            responses={"http://localhost:11434/api/chat": mock_stream}
        )

        received_tokens = []

        async def on_token(token: str):
            received_tokens.append(token)

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await client.generate_streaming(
                model="llama2",
                prompt="Say hello",
                on_token=on_token,
            )

        assert result == "Hello World!"
        assert received_tokens == tokens

    @pytest.mark.asyncio
    async def test_generate_streaming_with_thinking(self, client):
        """Test streaming generation with thinking content (qwen3 style)."""
        lines = [
            json.dumps({"message": {"thinking": "Let me think..."}, "done": False}),
            json.dumps({"message": {"content": "The answer"}, "done": False}),
            json.dumps({"message": {"content": ""}, "done": True}),
        ]

        mock_stream = MockStreamResponse(lines)
        mock_http = MockHTTPClient(
            responses={"http://localhost:11434/api/chat": mock_stream}
        )

        received_tokens = []

        async def on_token(token: str):
            received_tokens.append(token)

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await client.generate_streaming(
                model="qwen3",
                prompt="Think about this",
                on_token=on_token,
            )

        assert "Let me think..." in result
        assert "The answer" in result
        assert received_tokens == ["Let me think...", "The answer"]

    @pytest.mark.asyncio
    async def test_generate_streaming_empty_lines(self, client):
        """Test streaming with empty lines in response."""
        lines = [
            json.dumps({"message": {"content": "A"}, "done": False}),
            "",  # Empty line
            json.dumps({"message": {"content": "B"}, "done": False}),
            "",  # Empty line
            json.dumps({"message": {"content": ""}, "done": True}),
        ]

        mock_stream = MockStreamResponse(lines)
        mock_http = MockHTTPClient(
            responses={"http://localhost:11434/api/chat": mock_stream}
        )

        received_tokens = []

        async def on_token(token: str):
            received_tokens.append(token)

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await client.generate_streaming(
                model="llama2",
                prompt="test",
                on_token=on_token,
            )

        assert result == "AB"
        assert received_tokens == ["A", "B"]

    @pytest.mark.asyncio
    async def test_generate_streaming_malformed_json(self, client):
        """Test streaming with malformed JSON lines."""
        lines = [
            json.dumps({"message": {"content": "A"}, "done": False}),
            "not valid json",  # Malformed
            json.dumps({"message": {"content": "B"}, "done": False}),
            json.dumps({"message": {"content": ""}, "done": True}),
        ]

        mock_stream = MockStreamResponse(lines)
        mock_http = MockHTTPClient(
            responses={"http://localhost:11434/api/chat": mock_stream}
        )

        received_tokens = []

        async def on_token(token: str):
            received_tokens.append(token)

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await client.generate_streaming(
                model="llama2",
                prompt="test",
                on_token=on_token,
            )

        # Should skip malformed lines
        assert result == "AB"
        assert received_tokens == ["A", "B"]

    @pytest.mark.asyncio
    async def test_generate_streaming_custom_system_prompt(self, client):
        """Test streaming with custom system prompt."""
        lines = [
            json.dumps({"message": {"content": "OK"}, "done": False}),
            json.dumps({"message": {"content": ""}, "done": True}),
        ]

        mock_stream = MockStreamResponse(lines)
        mock_http = MockHTTPClient(
            responses={"http://localhost:11434/api/chat": mock_stream}
        )

        async def on_token(token: str):
            pass

        with patch("httpx.AsyncClient", return_value=mock_http):
            await client.generate_streaming(
                model="llama2",
                prompt="test",
                on_token=on_token,
                system_prompt="You are a helpful assistant.",
            )

        # Verify the request included custom system prompt
        assert len(mock_http.requests) == 1
        _, url, kwargs = mock_http.requests[0]
        payload = kwargs.get("json", {})
        messages = payload.get("messages", [])
        assert messages[0]["content"] == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_generate_streaming_uses_default_system_prompt(self, client):
        """Test streaming uses default system prompt when not specified."""
        lines = [
            json.dumps({"message": {"content": "OK"}, "done": False}),
            json.dumps({"message": {"content": ""}, "done": True}),
        ]

        mock_stream = MockStreamResponse(lines)
        mock_http = MockHTTPClient(
            responses={"http://localhost:11434/api/chat": mock_stream}
        )

        async def on_token(token: str):
            pass

        with patch("httpx.AsyncClient", return_value=mock_http):
            await client.generate_streaming(
                model="llama2",
                prompt="test",
                on_token=on_token,
            )

        # Verify the request included default system prompt
        assert len(mock_http.requests) == 1
        _, url, kwargs = mock_http.requests[0]
        payload = kwargs.get("json", {})
        messages = payload.get("messages", [])
        assert messages[0]["content"] == SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_generate_streaming_temperature_and_max_tokens(self, client):
        """Test streaming with custom temperature and max tokens."""
        lines = [
            json.dumps({"message": {"content": "OK"}, "done": False}),
            json.dumps({"message": {"content": ""}, "done": True}),
        ]

        mock_stream = MockStreamResponse(lines)
        mock_http = MockHTTPClient(
            responses={"http://localhost:11434/api/chat": mock_stream}
        )

        async def on_token(token: str):
            pass

        with patch("httpx.AsyncClient", return_value=mock_http):
            await client.generate_streaming(
                model="llama2",
                prompt="test",
                on_token=on_token,
                temperature=0.8,
                max_tokens=1024,
            )

        # Verify the request included temperature and max_tokens
        _, url, kwargs = mock_http.requests[0]
        payload = kwargs.get("json", {})
        options = payload.get("options", {})
        assert options["temperature"] == 0.8
        assert options["num_predict"] == 1024

    @pytest.mark.asyncio
    async def test_generate_non_streaming(self, client):
        """Test non-streaming generation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "message": {"content": "This is the response"}
        }

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await client.generate(
                model="llama2",
                prompt="test",
            )

        assert result == "This is the response"

    @pytest.mark.asyncio
    async def test_generate_non_streaming_thinking_fallback(self, client):
        """Test non-streaming falls back to thinking content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "message": {"content": "", "thinking": "My thinking process"}
        }

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_http):
            result = await client.generate(
                model="qwen3",
                prompt="test",
            )

        assert result == "My thinking process"

    @pytest.mark.asyncio
    async def test_generate_non_streaming_custom_system_prompt(self, client):
        """Test non-streaming with custom system prompt."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"message": {"content": "OK"}}

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_http):
            await client.generate(
                model="llama2",
                prompt="test",
                system_prompt="Custom system prompt",
            )

        # Verify custom system prompt was used
        call_args = mock_http.post.call_args
        payload = call_args.kwargs.get("json", {})
        messages = payload.get("messages", [])
        assert messages[0]["content"] == "Custom system prompt"


class TestOllamaStreamingClientConfiguration:
    """Tests for OllamaStreamingClient configuration."""

    def test_default_configuration(self):
        """Test default client configuration."""
        # Note: We can't easily test settings defaults without mocking
        # This tests that the client can be instantiated with explicit values
        client = OllamaStreamingClient(
            endpoint="http://custom:8080",
            timeout=60.0,
        )
        assert client.endpoint == "http://custom:8080"
        assert client.timeout == 60.0

    def test_custom_endpoint(self):
        """Test custom endpoint configuration."""
        client = OllamaStreamingClient(
            endpoint="http://192.168.1.100:11434",
            timeout=30.0,
        )
        assert client.endpoint == "http://192.168.1.100:11434"


class TestSystemPrompt:
    """Tests for the default system prompt."""

    def test_system_prompt_contains_action_format(self):
        """Test that system prompt explains the action format."""
        assert "<action>" in SYSTEM_PROMPT
        assert "</action>" in SYSTEM_PROMPT

    def test_system_prompt_contains_action_types(self):
        """Test that system prompt explains action types."""
        assert "fold" in SYSTEM_PROMPT.lower()
        assert "call" in SYSTEM_PROMPT.lower() or "check" in SYSTEM_PROMPT.lower()
        assert "cbr" in SYSTEM_PROMPT.lower() or "bet" in SYSTEM_PROMPT.lower()
