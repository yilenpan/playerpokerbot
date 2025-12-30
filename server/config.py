"""Server configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Ollama
    ollama_endpoint: str = "http://localhost:11434"
    ollama_timeout: float = 120.0

    # Game defaults
    default_starting_stack: int = 10000
    default_small_blind: int = 50
    default_big_blind: int = 100
    default_num_hands: int = 10

    # Turn timer
    turn_timeout_seconds: int = 30
    timer_warning_threshold: int = 10
    timer_critical_threshold: int = 5

    class Config:
        env_prefix = "POKER_"


settings = Settings()
