"""Hardware detection and quantization configuration."""

import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import torch


class Quantization(Enum):
    """Quantization levels for model loading."""
    INT4 = "4bit"
    INT8 = "8bit"
    FP16 = "fp16"


@dataclass
class HardwareConfig:
    """Hardware configuration with auto-detection."""
    gpu_name: str
    vram_gb: float
    quantization: Quantization

    @classmethod
    def detect(cls, override_quant: Optional[Quantization] = None) -> "HardwareConfig":
        """
        Auto-detect GPU and select appropriate quantization.

        Args:
            override_quant: Override auto-detected quantization level

        Returns:
            HardwareConfig with detected GPU and quantization settings
        """
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                check=True,
            )
            gpu_name, vram_mb = result.stdout.strip().split(", ")
            vram_gb = float(vram_mb) / 1024
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            # Fallback for environments without nvidia-smi
            gpu_name = "Unknown GPU"
            vram_gb = 16.0  # Assume T4-like

        # Select quantization based on GPU (can be overridden)
        if override_quant:
            quant = override_quant
        elif "A100" in gpu_name:
            quant = Quantization.FP16
        elif "L4" in gpu_name:
            quant = Quantization.INT8
        else:  # T4, V100, etc.
            quant = Quantization.INT4

        return cls(gpu_name=gpu_name, vram_gb=vram_gb, quantization=quant)

    def get_bnb_config(self):
        """
        Get bitsandbytes config for this quantization level.

        Returns:
            BitsAndBytesConfig or None for fp16
        """
        # Import here to avoid dependency issues
        from transformers import BitsAndBytesConfig

        if self.quantization == Quantization.INT4:
            return BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        elif self.quantization == Quantization.INT8:
            return BitsAndBytesConfig(load_in_8bit=True)
        else:  # FP16
            return None

    def get_torch_dtype(self) -> torch.dtype:
        """Get torch dtype for model loading."""
        return torch.float16

    def __str__(self) -> str:
        return f"{self.gpu_name} ({self.vram_gb:.0f}GB) - {self.quantization.value}"
