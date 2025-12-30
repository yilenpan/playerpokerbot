"""WebSocket connection manager."""

import asyncio
import json
from typing import Any
from fastapi import WebSocket
from pydantic import BaseModel


class WebSocketManager:
    """Manages WebSocket connections for a game session."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def send_event(self, websocket: WebSocket, event: BaseModel) -> None:
        """Send an event to a specific connection."""
        try:
            await websocket.send_text(event.model_dump_json())
        except Exception:
            await self.disconnect(websocket)

    async def broadcast(self, event: BaseModel) -> None:
        """Broadcast an event to all connected clients."""
        message = event.model_dump_json()
        disconnected = []

        async with self._lock:
            connections = list(self.active_connections)

        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn)

    async def broadcast_json(self, data: dict[str, Any]) -> None:
        """Broadcast raw JSON to all connected clients."""
        message = json.dumps(data)
        disconnected = []

        async with self._lock:
            connections = list(self.active_connections)

        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            await self.disconnect(conn)

    @property
    def connection_count(self) -> int:
        """Number of active connections."""
        return len(self.active_connections)

    async def close_all(self) -> None:
        """Close all connections."""
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.close()
                except Exception:
                    pass
            self.active_connections.clear()
