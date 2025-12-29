"""Evaluation configuration."""

from dataclasses import dataclass, field
from typing import List, Optional

from .hardware import Quantization


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    name: str                       # Display name
    model_id: str                   # HuggingFace model ID
    temperature: float = 0.6
    max_new_tokens: int = 512


@dataclass
class EvalConfig:
    """Configuration for evaluation run."""
    models: List[ModelConfig]
    num_hands: int = 500
    num_sessions: int = 5
    starting_stack: int = 10000
    small_blind: int = 50
    big_blind: int = 100
    seed: int = 42
    quantization: Optional[Quantization] = None  # None = auto-detect
    output_dir: str = "/content/eval_results"
    verbose: bool = False

    def total_hands(self) -> int:
        """Total hands to be played."""
        return self.num_hands * self.num_sessions


# Preset configurations
def quick_test_config() -> EvalConfig:
    """Quick test with minimal hands."""
    return EvalConfig(
        models=[
            ModelConfig("SFT", "YiPz/Qwen3-4B-pokerbench-sft"),
            ModelConfig("Base", "unsloth/Qwen3-4B-Thinking-2507"),
        ],
        num_hands=20,
        num_sessions=1,
        verbose=True,
    )


def standard_eval_config() -> EvalConfig:
    """Standard evaluation config."""
    return EvalConfig(
        models=[
            ModelConfig("SFT", "YiPz/Qwen3-4B-pokerbench-sft"),
            ModelConfig("Base", "unsloth/Qwen3-4B-Thinking-2507"),
        ],
        num_hands=500,
        num_sessions=5,
    )
