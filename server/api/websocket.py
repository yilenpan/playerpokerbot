"""WebSocket endpoint handler."""

import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect

from ..game import GameSessionManager
from ..models.events import ErrorEvent


async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    session_manager: GameSessionManager,
):
    """Handle WebSocket connection for a game session."""
    print(f"[WS] New connection for session {session_id}")

    # Get session
    session = await session_manager.get_session(session_id)
    if session is None:
        print(f"[WS] Session {session_id} not found")
        await websocket.close(code=4004, reason="Session not found")
        return

    # Connect client
    await session.on_client_connect(websocket)
    print(f"[WS] Client connected, session status: {session.status}")

    # Don't auto-start - wait for start_hand message from client

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "player_action":
                    # Human player action
                    action_type = message.get("action_type")
                    amount = message.get("amount")
                    await session.receive_human_action(action_type, amount)

                elif msg_type == "start_hand":
                    # Request to start next hand (if waiting)
                    if session.status == "waiting":
                        asyncio.create_task(session.start_session())

                elif msg_type == "end_session":
                    # Request to end session
                    await session.end_session()
                    break

                elif msg_type == "ping":
                    # Keep-alive - send pong
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except json.JSONDecodeError:
                await session.ws_manager.send_event(
                    websocket,
                    ErrorEvent(code="invalid_json", message="Invalid JSON message"),
                )

    except WebSocketDisconnect:
        pass
    finally:
        await session.on_client_disconnect(websocket)
