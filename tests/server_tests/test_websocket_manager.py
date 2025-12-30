"""Tests for WebSocketManager."""

# Add project root to path for imports BEFORE other imports
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.websocket_manager import WebSocketManager
from server.models.events import (
    ConnectionAckEvent,
    ErrorEvent,
    TimerTickEvent,
)


# =============================================================================
# WebSocketManager Tests
# =============================================================================


class TestWebSocketManager:
    """Tests for WebSocketManager class."""

    @pytest.fixture
    def manager(self):
        """Create a WebSocket manager."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_websocket):
        """Test connecting a WebSocket."""
        await manager.connect(mock_websocket)

        assert mock_websocket.accepted is True
        assert manager.connection_count == 1
        assert mock_websocket in manager.active_connections

    @pytest.mark.asyncio
    async def test_connect_multiple(self, manager, mock_websocket_factory):
        """Test connecting multiple WebSockets."""
        ws1 = mock_websocket_factory()
        ws2 = mock_websocket_factory()
        ws3 = mock_websocket_factory()

        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)

        assert manager.connection_count == 3

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Test disconnecting a WebSocket."""
        await manager.connect(mock_websocket)
        await manager.disconnect(mock_websocket)

        assert manager.connection_count == 0
        assert mock_websocket not in manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self, manager, mock_websocket):
        """Test disconnecting a WebSocket that isn't connected."""
        # Should not raise
        await manager.disconnect(mock_websocket)
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_idempotent(self, manager, mock_websocket):
        """Test that disconnect is idempotent."""
        await manager.connect(mock_websocket)
        await manager.disconnect(mock_websocket)
        await manager.disconnect(mock_websocket)  # Second call

        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_send_event(self, manager, mock_websocket):
        """Test sending an event to a specific connection."""
        await manager.connect(mock_websocket)

        event = ConnectionAckEvent(session_id="test123", player_id=0)
        await manager.send_event(mock_websocket, event)

        events = mock_websocket.get_sent_events()
        assert len(events) == 1
        assert events[0]["type"] == "connection_ack"
        assert events[0]["session_id"] == "test123"

    @pytest.mark.asyncio
    async def test_send_event_disconnects_on_error(self, manager, mock_websocket):
        """Test that send_event disconnects on error."""
        await manager.connect(mock_websocket)
        mock_websocket.set_should_fail(True)

        event = ErrorEvent(code="test", message="test")
        await manager.send_event(mock_websocket, event)

        # Should have been disconnected
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_broadcast(self, manager, mock_websocket_factory):
        """Test broadcasting to all connections."""
        ws1 = mock_websocket_factory()
        ws2 = mock_websocket_factory()
        ws3 = mock_websocket_factory()

        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)

        event = TimerTickEvent(player_id=0, remaining_seconds=10)
        await manager.broadcast(event)

        # All should have received the event
        for ws in [ws1, ws2, ws3]:
            events = ws.get_sent_events()
            assert len(events) == 1
            assert events[0]["type"] == "timer_tick"

    @pytest.mark.asyncio
    async def test_broadcast_removes_disconnected(self, manager, mock_websocket_factory):
        """Test that broadcast removes disconnected clients."""
        ws1 = mock_websocket_factory()
        ws2 = mock_websocket_factory()

        await manager.connect(ws1)
        await manager.connect(ws2)

        # Make ws2 fail
        ws2.set_should_fail(True)

        event = ErrorEvent(code="test", message="test")
        await manager.broadcast(event)

        # ws2 should have been disconnected
        assert manager.connection_count == 1
        assert ws1 in manager.active_connections
        assert ws2 not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_json(self, manager, mock_websocket_factory):
        """Test broadcasting raw JSON."""
        ws1 = mock_websocket_factory()
        ws2 = mock_websocket_factory()

        await manager.connect(ws1)
        await manager.connect(ws2)

        data = {"type": "custom", "value": 42}
        await manager.broadcast_json(data)

        for ws in [ws1, ws2]:
            events = ws.get_sent_events()
            assert len(events) == 1
            assert events[0] == data

    @pytest.mark.asyncio
    async def test_broadcast_json_removes_disconnected(self, manager, mock_websocket_factory):
        """Test that broadcast_json removes disconnected clients."""
        ws1 = mock_websocket_factory()
        ws2 = mock_websocket_factory()

        await manager.connect(ws1)
        await manager.connect(ws2)

        ws2.set_should_fail(True)

        await manager.broadcast_json({"type": "test"})

        assert manager.connection_count == 1

    @pytest.mark.asyncio
    async def test_close_all(self, manager, mock_websocket_factory):
        """Test closing all connections."""
        ws1 = mock_websocket_factory()
        ws2 = mock_websocket_factory()
        ws3 = mock_websocket_factory()

        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)

        await manager.close_all()

        assert manager.connection_count == 0
        assert ws1.closed is True
        assert ws2.closed is True
        assert ws3.closed is True

    @pytest.mark.asyncio
    async def test_close_all_handles_errors(self, manager, mock_websocket_factory):
        """Test that close_all handles errors gracefully."""

        class FailingMockWebSocket:
            def __init__(self):
                self.accepted = False
                self.closed = False
                self.sent_messages = []

            async def accept(self):
                self.accepted = True

            async def close(self):
                raise RuntimeError("Close failed")

            async def send_text(self, message: str):
                self.sent_messages.append(message)

        ws1 = mock_websocket_factory()
        ws2 = FailingMockWebSocket()

        await manager.connect(ws1)
        # Manually add the failing one
        manager.active_connections.append(ws2)

        # Should not raise
        await manager.close_all()

        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_connection_count_property(self, manager, mock_websocket_factory):
        """Test connection_count property."""
        assert manager.connection_count == 0

        ws1 = mock_websocket_factory()
        await manager.connect(ws1)
        assert manager.connection_count == 1

        ws2 = mock_websocket_factory()
        await manager.connect(ws2)
        assert manager.connection_count == 2

        await manager.disconnect(ws1)
        assert manager.connection_count == 1


class TestWebSocketManagerConcurrency:
    """Concurrency tests for WebSocketManager."""

    @pytest.fixture
    def manager(self):
        """Create a WebSocket manager."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_concurrent_connects(self, manager, mock_websocket_factory):
        """Test concurrent connection attempts."""
        websockets = [mock_websocket_factory() for _ in range(10)]

        await asyncio.gather(*[manager.connect(ws) for ws in websockets])

        assert manager.connection_count == 10

    @pytest.mark.asyncio
    async def test_concurrent_disconnects(self, manager, mock_websocket_factory):
        """Test concurrent disconnection attempts."""
        websockets = [mock_websocket_factory() for _ in range(10)]

        for ws in websockets:
            await manager.connect(ws)

        await asyncio.gather(*[manager.disconnect(ws) for ws in websockets])

        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_concurrent_broadcast(self, manager, mock_websocket_factory):
        """Test concurrent broadcasts."""
        websockets = [mock_websocket_factory() for _ in range(5)]

        for ws in websockets:
            await manager.connect(ws)

        events = [
            TimerTickEvent(player_id=0, remaining_seconds=i)
            for i in range(10)
        ]

        await asyncio.gather(*[manager.broadcast(e) for e in events])

        # Each WebSocket should have received all events
        for ws in websockets:
            assert len(ws.get_sent_events()) == 10

    @pytest.mark.asyncio
    async def test_connect_disconnect_during_broadcast(self, manager, mock_websocket_factory):
        """Test connecting and disconnecting during broadcast."""
        ws1 = mock_websocket_factory()
        await manager.connect(ws1)

        async def broadcast_task():
            for i in range(10):
                event = TimerTickEvent(player_id=0, remaining_seconds=i)
                await manager.broadcast(event)
                await asyncio.sleep(0.01)

        async def connect_task():
            for _ in range(5):
                ws = mock_websocket_factory()
                await manager.connect(ws)
                await asyncio.sleep(0.02)

        await asyncio.gather(broadcast_task(), connect_task())

        # Should have 6 connections (1 original + 5 new)
        assert manager.connection_count == 6


class TestWebSocketManagerEventSerialization:
    """Tests for event serialization in WebSocketManager."""

    @pytest.fixture
    def manager(self):
        """Create a WebSocket manager."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_pydantic_model_serialization(self, manager, mock_websocket):
        """Test that Pydantic models are properly serialized."""
        await manager.connect(mock_websocket)

        event = ConnectionAckEvent(session_id="abc123", player_id=0)
        await manager.send_event(mock_websocket, event)

        # Verify the message was valid JSON
        assert len(mock_websocket.sent_messages) == 1
        parsed = json.loads(mock_websocket.sent_messages[0])
        assert parsed["type"] == "connection_ack"
        assert parsed["session_id"] == "abc123"

    @pytest.mark.asyncio
    async def test_broadcast_uses_json_serialization(self, manager, mock_websocket_factory):
        """Test that broadcast properly serializes events."""
        ws1 = mock_websocket_factory()
        ws2 = mock_websocket_factory()

        await manager.connect(ws1)
        await manager.connect(ws2)

        event = ErrorEvent(code="test_code", message="test message")
        await manager.broadcast(event)

        # Both should have the same JSON
        assert ws1.sent_messages[0] == ws2.sent_messages[0]

        # Verify it's valid JSON
        parsed = json.loads(ws1.sent_messages[0])
        assert parsed["type"] == "error"
        assert parsed["code"] == "test_code"
        assert parsed["message"] == "test message"
