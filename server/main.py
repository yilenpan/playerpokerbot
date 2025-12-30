"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .config import settings
from .api.routes import router as api_router, init_dependencies
from .api.websocket import websocket_endpoint
from .game import GameSessionManager
from .streaming import OllamaStreamingClient


# Global instances
session_manager: GameSessionManager = None
ollama_client: OllamaStreamingClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global session_manager, ollama_client

    # Startup
    session_manager = GameSessionManager()
    ollama_client = OllamaStreamingClient()
    init_dependencies(session_manager, ollama_client)

    # Check Ollama connection
    if await ollama_client.check_connection():
        print(f"Connected to Ollama at {settings.ollama_endpoint}")
    else:
        print(f"WARNING: Cannot connect to Ollama at {settings.ollama_endpoint}")

    yield

    # Shutdown
    await session_manager.cleanup_all()


# Create FastAPI app
app = FastAPI(
    title="Poker Bot API",
    description="Browser-based poker game with LLM opponents",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router, prefix="/api")


# WebSocket endpoint
@app.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for game sessions."""
    await websocket_endpoint(websocket, session_id, session_manager)


# Serve static files for frontend (if web/ directory exists)
web_dir = Path(__file__).parent.parent / "web" / "dist"
if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")


def main():
    """Run the server."""
    import uvicorn

    uvicorn.run(
        "server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
