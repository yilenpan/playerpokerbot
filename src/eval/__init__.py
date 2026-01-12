"""Poker bot evaluation module."""

from .hardware import HardwareConfig, Quantization
from .config import EvalConfig, ModelConfig
from .transformers_player import TransformersPlayer, ActionRecord
from .metrics import MetricsCollector, HandResult
from .game import EvalPokerGame
from .openai_player import OpenAIPlayer
from .observability import ActionTrace, ModelObservability, ObservabilityCollector
from .prompt_builder import PromptBuilder, pretty_card, score_hole_cards, get_position_name

__all__ = [
    "HardwareConfig",
    "Quantization",
    "EvalConfig",
    "ModelConfig",
    "TransformersPlayer",
    "ActionRecord",
    "MetricsCollector",
    "HandResult",
    "EvalPokerGame",
    "OpenAIPlayer",
    "ActionTrace",
    "ModelObservability",
    "ObservabilityCollector",
    "PromptBuilder",
    "pretty_card",
    "score_hole_cards",
    "get_position_name",
]
