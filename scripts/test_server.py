#!/usr/bin/env python3
"""Simple test client for the poker server."""

import asyncio
import json
import httpx
import websockets


async def test_health():
    """Test health endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/api/health")
        print(f"Health check: {response.json()}")
        return response.status_code == 200


async def test_models():
    """Test models endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/api/models")
        print(f"Available models: {response.json()}")


async def test_create_session():
    """Test session creation."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/sessions",
            json={
                "opponents": [
                    {"name": "AI-1", "model": "qwen3:4b"},
                ],
                "starting_stack": 1000,
                "small_blind": 10,
                "big_blind": 20,
                "num_hands": 1,
                "turn_timeout_seconds": 30,
            },
        )
        print(f"Session created: {response.json()}")
        return response.json()


async def test_websocket(session_id: str):
    """Test WebSocket connection and game flow."""
    uri = f"ws://localhost:8000/ws/{session_id}"

    print(f"\nConnecting to {uri}...")

    async with websockets.connect(uri) as ws:
        # Listen for events
        event_count = 0
        max_events = 50  # Limit for testing

        while event_count < max_events:
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=60.0)
                data = json.loads(message)
                event_type = data.get("type", "unknown")

                print(f"\n[{event_type}]")

                if event_type == "connection_ack":
                    print(f"  Connected as player {data.get('player_id')}")

                elif event_type == "game_state":
                    state = data.get("state", {})
                    print(f"  Hand #{state.get('hand_number')}")
                    print(f"  Street: {state.get('street')}")
                    print(f"  Pot: {state.get('pot')}")

                elif event_type == "your_turn":
                    print(f"  Available actions: {data.get('available_actions')}")
                    # Auto-call for testing
                    await ws.send(json.dumps({
                        "type": "player_action",
                        "action_type": "call",
                    }))
                    print("  -> Sent: call")

                elif event_type == "thinking_start":
                    print(f"  {data.get('player_name')} is thinking...")

                elif event_type == "thinking_token":
                    # Print token inline
                    print(data.get("token", ""), end="", flush=True)

                elif event_type == "thinking_complete":
                    print(f"  Action: {data.get('action')}")
                    print(f"  Duration: {data.get('duration_ms')}ms")

                elif event_type == "timer_tick":
                    remaining = data.get("remaining_seconds")
                    if remaining % 5 == 0:  # Print every 5 seconds
                        print(f"  Timer: {remaining}s remaining")

                elif event_type == "timer_expired":
                    print(f"  Timer expired! Auto-{data.get('action_taken')}")

                elif event_type == "hand_complete":
                    print(f"  Hand complete!")
                    print(f"  Winners: {data.get('winners')}")

                elif event_type == "session_complete":
                    print(f"\nSession complete!")
                    print(f"  Hands played: {data.get('hands_played')}")
                    print(f"  Final stacks: {data.get('final_stacks')}")
                    break

                elif event_type == "game_state_update":
                    print(f"  Street: {data.get('street')}, Pot: {data.get('pot')}")

                elif event_type == "error":
                    print(f"  ERROR: {data.get('message')}")

                event_count += 1

            except asyncio.TimeoutError:
                print("Timeout waiting for message")
                break


async def main():
    """Run tests."""
    print("=" * 60)
    print("Poker Server Test Client")
    print("=" * 60)

    # Test health
    print("\n1. Testing health endpoint...")
    if not await test_health():
        print("Server not running. Start with: python -m server.main")
        return

    # Test models
    print("\n2. Testing models endpoint...")
    await test_models()

    # Create session
    print("\n3. Creating session...")
    session = await test_create_session()
    session_id = session.get("session_id")

    if not session_id:
        print("Failed to create session")
        return

    # Test WebSocket
    print("\n4. Testing WebSocket game flow...")
    await test_websocket(session_id)

    print("\n" + "=" * 60)
    print("Tests complete!")


if __name__ == "__main__":
    asyncio.run(main())
