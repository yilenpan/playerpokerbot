"""API request/response models."""

from typing import Optional
from pydantic import BaseModel


class OpponentConfig(BaseModel):
    """Configuration for an LLM opponent."""

    name: str
    model: str
    temperature: float = 0.6


class SessionConfigRequest(BaseModel):
    """Request to create a new game session."""

    opponents: list[OpponentConfig]
    starting_stack: int = 10000
    small_blind: int = 50
    big_blind: int = 100
    num_hands: int = 10
    turn_timeout_seconds: int = 30


class PlayerInfo(BaseModel):
    """Player information in session response."""

    id: int
    name: str
    player_type: str  # "human" or "llm"
    model: Optional[str] = None


class SessionResponse(BaseModel):
    """Response after creating a session."""

    session_id: str
    websocket_url: str
    players: list[PlayerInfo]


class SessionStatusResponse(BaseModel):
    """Current session status."""

    session_id: str
    status: str  # "waiting", "in_progress", "complete"
    hand_number: int
    player_stacks: list[int]


class ModelInfo(BaseModel):
    """Ollama model information."""

    name: str
    size: Optional[str] = None


class ModelsResponse(BaseModel):
    """Available Ollama models."""

    models: list[ModelInfo]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    ollama_connected: bool
    active_sessions: int
