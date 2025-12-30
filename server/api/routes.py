"""REST API routes."""

import asyncio
from fastapi import APIRouter, HTTPException

from ..config import settings
from ..models.api import (
    SessionConfigRequest,
    SessionResponse,
    SessionStatusResponse,
    ModelsResponse,
    ModelInfo,
    HealthResponse,
    PlayerInfo,
)
from ..models.game import GameConfig
from ..game import GameSessionManager
from ..streaming import OllamaStreamingClient

router = APIRouter()

# Global session manager (will be initialized in main.py)
session_manager: GameSessionManager = None
ollama_client: OllamaStreamingClient = None


def init_dependencies(sm: GameSessionManager, oc: OllamaStreamingClient):
    """Initialize route dependencies."""
    global session_manager, ollama_client
    session_manager = sm
    ollama_client = oc


@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: SessionConfigRequest):
    """Create a new game session."""
    if session_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")

    if len(request.opponents) < 1 or len(request.opponents) > 5:
        raise HTTPException(status_code=400, detail="Must have 1-5 opponents")

    config = GameConfig(
        starting_stack=request.starting_stack,
        small_blind=request.small_blind,
        big_blind=request.big_blind,
        num_hands=request.num_hands,
        turn_timeout_seconds=request.turn_timeout_seconds,
    )

    session = await session_manager.create_session(request.opponents, config)

    # Build player info
    players = [
        PlayerInfo(id=0, name="You", player_type="human"),
    ]
    for i, opp in enumerate(request.opponents):
        players.append(
            PlayerInfo(id=i + 1, name=opp.name, player_type="llm", model=opp.model)
        )

    return SessionResponse(
        session_id=session.session_id,
        websocket_url=f"/ws/{session.session_id}",
        players=players,
    )


@router.get("/sessions/{session_id}", response_model=SessionStatusResponse)
async def get_session(session_id: str):
    """Get current session status."""
    if session_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")

    session = await session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionStatusResponse(
        session_id=session.session_id,
        status=session.status,
        hand_number=session.engine.hand_number,
        player_stacks=[p.stack for p in session.players],
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """End and cleanup a session."""
    if session_manager is None:
        raise HTTPException(status_code=500, detail="Server not initialized")

    session = await session_manager.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    await session_manager.remove_session(session_id)
    return {"status": "deleted"}


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """List available Ollama models."""
    if ollama_client is None:
        raise HTTPException(status_code=500, detail="Server not initialized")

    models = await ollama_client.list_models()
    return ModelsResponse(
        models=[
            ModelInfo(
                name=m.get("name", "unknown"),
                size=m.get("details", {}).get("parameter_size"),
            )
            for m in models
        ]
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    ollama_connected = False
    if ollama_client:
        ollama_connected = await ollama_client.check_connection()

    active_sessions = session_manager.active_session_count if session_manager else 0

    return HealthResponse(
        status="healthy",
        ollama_connected=ollama_connected,
        active_sessions=active_sessions,
    )
