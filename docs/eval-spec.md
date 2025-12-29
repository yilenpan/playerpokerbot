# Poker Bot Evaluation Spec

**Target:** Evaluate `YiPz/Qwen3-4B-pokerbench-sft` vs base `unsloth/Qwen3-4B-Thinking-2507`
**Hardware:** Configurable (T4 / L4 / A100)
**Inference:** transformers + bitsandbytes (4-bit / 8-bit / fp16)

---

## 1. Architecture Overview

```
Google Colab (auto-detected GPU)
├── HardwareConfig (detects T4/L4/A100, selects quantization)
├── Loaded Models (quantization based on hardware)
│   ├── YiPz/Qwen3-4B-pokerbench-sft
│   └── unsloth/Qwen3-4B-Thinking-2507
│
└── Evaluation Engine
    ├── TransformersPlayer (direct model.generate())
    ├── EvalPokerGame (automated game loop)
    ├── MetricsCollector (hand/action logging)
    └── ResultsExporter (CSV, plots)
```

**Why bitsandbytes:**
- No pre-conversion needed (load HF safetensors directly)
- Flexible quantization (4-bit, 8-bit, or fp16)
- Works across all Colab GPU tiers

---

## 2. Hardware & Quantization Matrix

| GPU | VRAM | 4-bit (2×4B) | 8-bit (2×4B) | fp16 (2×4B) | Default |
|-----|------|--------------|--------------|-------------|---------|
| T4 | 15GB | ✅ ~6GB | ✅ ~11GB | ❌ OOM | 4-bit |
| L4 | 24GB | ✅ ~6GB | ✅ ~11GB | ✅ ~17GB | 8-bit |
| A100 40GB | 40GB | ✅ ~6GB | ✅ ~11GB | ✅ ~17GB | fp16 |
| A100 80GB | 80GB | ✅ ~6GB | ✅ ~11GB | ✅ ~17GB | fp16 |

**Performance (hands/hour, heads-up):**

| GPU | 4-bit | 8-bit | fp16 |
|-----|-------|-------|------|
| T4 | 60-80 | 40-60 | N/A |
| L4 | 100-150 | 80-120 | 60-100 |
| A100 | 200-300 | 180-250 | 150-200 |

**Trade-offs:**
- **4-bit:** Fastest, lowest VRAM, slight quality loss
- **8-bit:** Good balance of speed and quality
- **fp16:** Full precision, best quality, slowest

---

## 3. Setup (Colab Cell)

```python
# Cell 1: Install dependencies
!pip install -q transformers accelerate bitsandbytes torch

# Cell 2: Hardware detection and quantization config
import torch
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


class Quantization(Enum):
    INT4 = "4bit"
    INT8 = "8bit"
    FP16 = "fp16"


@dataclass
class HardwareConfig:
    gpu_name: str
    vram_gb: float
    quantization: Quantization

    @classmethod
    def detect(cls, override_quant: Optional[Quantization] = None) -> "HardwareConfig":
        """Auto-detect GPU and select appropriate quantization."""
        # Get GPU info
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True
        )
        gpu_name, vram_mb = result.stdout.strip().split(", ")
        vram_gb = float(vram_mb) / 1024

        # Select quantization based on GPU (can be overridden)
        if override_quant:
            quant = override_quant
        elif "A100" in gpu_name:
            quant = Quantization.FP16
        elif "L4" in gpu_name:
            quant = Quantization.INT8
        else:  # T4, etc.
            quant = Quantization.INT4

        return cls(gpu_name=gpu_name, vram_gb=vram_gb, quantization=quant)

    def get_bnb_config(self) -> Optional[BitsAndBytesConfig]:
        """Get bitsandbytes config for this quantization level."""
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
            return None  # No quantization

    def get_torch_dtype(self) -> torch.dtype:
        """Get torch dtype for model loading."""
        return torch.float16


# Detect hardware (or override with: HardwareConfig.detect(Quantization.INT8))
hw = HardwareConfig.detect()
print(f"GPU: {hw.gpu_name} ({hw.vram_gb:.0f}GB)")
print(f"Quantization: {hw.quantization.value}")

# Cell 3: Load models
MODELS = {
    "sft": "YiPz/Qwen3-4B-pokerbench-sft",
    "base": "unsloth/Qwen3-4B-Thinking-2507",
}

loaded_models = {}
tokenizers = {}
bnb_config = hw.get_bnb_config()

for name, model_id in MODELS.items():
    print(f"Loading {name}: {model_id} ({hw.quantization.value})...")

    tokenizers[name] = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

    load_kwargs = {
        "device_map": "auto",
        "trust_remote_code": True,
        "torch_dtype": hw.get_torch_dtype(),
    }
    if bnb_config:
        load_kwargs["quantization_config"] = bnb_config

    loaded_models[name] = AutoModelForCausalLM.from_pretrained(model_id, **load_kwargs)

    allocated = torch.cuda.memory_allocated() / 1024**3
    print(f"  Loaded. VRAM: {allocated:.1f}GB")

print(f"\nTotal VRAM used: {torch.cuda.memory_allocated() / 1024**3:.1f}GB / {hw.vram_gb:.0f}GB")
```

**Override examples:**
```python
# Force 4-bit on any GPU (for speed)
hw = HardwareConfig.detect(override_quant=Quantization.INT4)

# Force 8-bit on A100 (balance speed/quality)
hw = HardwareConfig.detect(override_quant=Quantization.INT8)

# Force fp16 on L4 (if you have headroom)
hw = HardwareConfig.detect(override_quant=Quantization.FP16)
```

---

## 4. TransformersPlayer Implementation

```python
# src/eval/transformers_player.py
"""Transformers-based player using direct model.generate()."""

import time
import torch
from dataclasses import dataclass
from typing import List, Tuple, Optional, Any

from actions import ParsedAction, ActionParser


@dataclass
class ActionRecord:
    hand_id: int
    street: str
    hole_cards: Tuple[str, str]
    board: List[str]
    pot: int
    to_call: int
    stack: int
    position: str
    action: ParsedAction
    thinking: str          # Content inside <think>...</think>
    response: str          # Content after </think>
    latency_ms: float
    tokens_generated: int


class TransformersPlayer:
    """Player using HuggingFace transformers with bitsandbytes."""

    SYSTEM_PROMPT = """You are an expert poker player. Analyze the game state and decide your action.

Output format: <action>ACTION</action>
- <action>f</action> = fold
- <action>cc</action> = check or call
- <action>cbr AMOUNT</action> = bet or raise to AMOUNT

Think step by step, then output exactly ONE action tag."""

    def __init__(
        self,
        name: str,
        model: Any,  # PreTrainedModel
        tokenizer: Any,  # PreTrainedTokenizer
        temperature: float = 0.6,
        max_new_tokens: int = 256,
        player_id: int = 0,
    ):
        self.name = name
        self.model = model
        self.tokenizer = tokenizer
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens
        self.player_id = player_id

        self.parser = ActionParser()
        self.action_history: List[ActionRecord] = []
        self._hand_id = 0
        self._street = "preflop"

        # Ensure pad token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def set_hand_context(self, hand_id: int, street: str) -> None:
        self._hand_id = hand_id
        self._street = street

    def get_action(
        self,
        hole_cards: Tuple[str, str],
        board: List[str],
        pot: int,
        to_call: int,
        stack: int,
        position: str,
        num_players: int,
    ) -> ParsedAction:
        """Get action via model.generate()."""
        start = time.perf_counter()

        prompt = self._build_prompt(
            hole_cards, board, pot, to_call, stack, position, num_players
        )

        try:
            thinking, response, tokens_gen = self._generate(prompt)
            can_check = to_call == 0
            # Parse action from response (after </think>)
            action = self.parser.parse(response, can_check, stack)
        except Exception as e:
            thinking = ""
            response = f"ERROR: {e}"
            tokens_gen = 0
            action = ParsedAction("fold")

        latency = (time.perf_counter() - start) * 1000

        self.action_history.append(ActionRecord(
            hand_id=self._hand_id,
            street=self._street,
            hole_cards=hole_cards,
            board=list(board),
            pot=pot,
            to_call=to_call,
            stack=stack,
            position=position,
            action=action,
            thinking=thinking[:1000],   # Truncate for storage
            response=response[:500],
            latency_ms=latency,
            tokens_generated=tokens_gen,
        ))

        return action

    def _build_prompt(
        self,
        hole_cards: Tuple[str, str],
        board: List[str],
        pot: int,
        to_call: int,
        stack: int,
        position: str,
        num_players: int,
    ) -> str:
        """Build game state prompt."""
        board_str = " ".join(board) if board else "None"

        user_msg = f"""Game: {num_players}-handed No-Limit Hold'em
Position: {position}
Stack: {stack}
Hole Cards: {hole_cards[0]} {hole_cards[1]}
Board: {board_str}
Pot: {pot}
To Call: {to_call}

What is your action?"""

        # Format as chat
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        return self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

    # Token ID for </think> in Qwen3 thinking models
    THINK_END_TOKEN_ID = 151668

    def _generate(self, prompt: str) -> Tuple[str, str, int]:
        """Generate response from model. Returns (thinking, response, token_count)."""
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        input_len = inputs.input_ids.shape[1]

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                top_p=0.95,
                top_k=20,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
            )

        new_tokens = outputs[0][input_len:]
        num_tokens = len(new_tokens)

        # Split thinking from response at </think> token
        try:
            think_end_idx = (new_tokens == self.THINK_END_TOKEN_ID).nonzero(as_tuple=True)[0][-1].item()
            thinking_tokens = new_tokens[:think_end_idx]
            response_tokens = new_tokens[think_end_idx + 1:]
        except (IndexError, RuntimeError):
            # No </think> token found - treat all as response
            thinking_tokens = torch.tensor([], dtype=new_tokens.dtype)
            response_tokens = new_tokens

        thinking = self.tokenizer.decode(thinking_tokens, skip_special_tokens=True).strip()
        response = self.tokenizer.decode(response_tokens, skip_special_tokens=True).strip()

        return thinking, response, num_tokens

    def get_stats(self) -> dict:
        """Calculate player statistics."""
        if not self.action_history:
            return {}

        total = len(self.action_history)
        preflop = [a for a in self.action_history if a.street == "preflop"]

        vpip_actions = [a for a in preflop if a.action.action_type in ("call", "raise", "all_in")]
        pfr_actions = [a for a in preflop if a.action.action_type in ("raise", "all_in")]

        bets_raises = sum(1 for a in self.action_history if a.action.action_type in ("raise", "all_in"))
        calls = sum(1 for a in self.action_history if a.action.action_type == "call")

        latencies = [a.latency_ms for a in self.action_history]
        tokens = [a.tokens_generated for a in self.action_history]

        return {
            "total_actions": total,
            "vpip": len(vpip_actions) / len(preflop) if preflop else 0,
            "pfr": len(pfr_actions) / len(preflop) if preflop else 0,
            "aggression_factor": bets_raises / calls if calls > 0 else float('inf'),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "avg_tokens": sum(tokens) / len(tokens),
            "fold_pct": sum(1 for a in self.action_history if a.action.action_type == "fold") / total,
        }

    def reset_history(self) -> None:
        self.action_history = []
```

---

## 5. Evaluation Configuration

```python
# Cell 4: Configuration

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ModelConfig:
    name: str           # Display name
    model_id: str       # HuggingFace model ID
    temperature: float = 0.6
    max_new_tokens: int = 512

@dataclass
class EvalConfig:
    models: List[ModelConfig]
    num_hands: int = 500
    num_sessions: int = 5
    starting_stack: int = 10000
    small_blind: int = 50
    big_blind: int = 100
    seed: int = 42
    quantization: Optional[Quantization] = None  # None = auto-detect
    output_dir: str = "/content/eval_results"

# Your evaluation config
config = EvalConfig(
    models=[
        ModelConfig(
            name="Qwen3-4B-SFT",
            model_id="YiPz/Qwen3-4B-pokerbench-sft",
        ),
        ModelConfig(
            name="Qwen3-4B-Base",
            model_id="unsloth/Qwen3-4B-Thinking-2507",
        ),
    ],
    num_hands=500,
    num_sessions=5,
    # quantization=Quantization.INT4,  # Uncomment to override auto-detection
)

print(f"Hardware: {hw.gpu_name} ({hw.quantization.value})")
print(f"Evaluating: {config.models[0].name} vs {config.models[1].name}")
print(f"Total hands: {config.num_hands * config.num_sessions}")
```

---

## 6. Key Metrics for SFT Evaluation

**Primary (Did fine-tuning help?):**
| Metric | What it shows |
|--------|---------------|
| BB/100 (SFT - Base) | Profit improvement from fine-tuning |
| Win Rate Delta | Raw win % improvement |

**Secondary (How did play style change?):**
| Metric | What it shows |
|--------|---------------|
| VPIP change | Looser/tighter starting hand selection |
| PFR change | More/less preflop aggression |
| AF change | Postflop aggression change |

**Diagnostic:**
| Metric | What it shows |
|--------|---------------|
| Fold % | Is model over/under-folding? |
| Avg tokens | Response verbosity |
| Latency | Inference speed |

---

## 7. Notebook Cell Structure

```
poker_eval.ipynb
├── Cell 1: Install dependencies
├── Cell 2: Hardware detection & quantization config
│   └── Auto-detects T4/L4/A100, selects 4bit/8bit/fp16
├── Cell 3: Load models
│   └── Uses detected/configured quantization
├── Cell 4: Evaluation config
│   └── Models, hands, sessions, game settings
├── Cell 5: Run Evaluation
│   ├── Progress bar
│   ├── Live stats display
│   └── Checkpoint every 100 hands
├── Cell 6: Results
│   ├── Summary table
│   ├── SFT vs Base comparison chart
│   ├── Per-street analysis
│   └── Export to Drive
└── Cell 7: Debug (optional)
    └── Inspect individual hands/thinking traces
```

---

## 8. Expected Output

```
=======================================================================
EVALUATION RESULTS: YiPz/Qwen3-4B-pokerbench-sft vs Qwen/Qwen3-4B
=======================================================================

Configuration:
  Hands per session: 500
  Sessions: 5
  Total hands: 2500

Model              Hands    Wins   Win%     BB/100    VPIP     PFR
-----------------------------------------------------------------------
Qwen3-4B-SFT        2500    1340   53.6%    +8.42    28.3%   21.5%
Qwen3-4B-Base       2500    1160   46.4%    -8.42    24.1%   18.2%
-----------------------------------------------------------------------

SFT IMPROVEMENT:
  Win Rate: +7.2%
  BB/100: +16.84 (from -8.42 to +8.42)
  VPIP: +4.2% (plays more hands)
  PFR: +3.3% (more aggressive preflop)

=======================================================================
```

---

## 9. File Changes Required

| File | Change |
|------|--------|
| `src/eval/__init__.py` | New - package init |
| `src/eval/hardware.py` | New - HardwareConfig, Quantization |
| `src/eval/transformers_player.py` | New - TransformersPlayer class |
| `src/eval/game.py` | New - EvalPokerGame (automated) |
| `src/eval/metrics.py` | New - MetricsCollector |
| `src/eval/config.py` | New - EvalConfig, ModelConfig |
| `notebooks/poker_eval.ipynb` | New - Colab notebook |

**Estimated new code:** ~500 lines

---

## 10. Resolved Design Decisions

1. **Thinking tokens:** ✅ Both models output `<think>...</think>`. Parser splits at token ID 151668
2. **Base model:** ✅ `unsloth/Qwen3-4B-Thinking-2507`
3. **Chat template:** ✅ Qwen3 default via `apply_chat_template()`
4. **Generation params:** ✅ temp=0.6, top_p=0.95, top_k=20
5. **Hardware:** ✅ Auto-detect GPU (T4/L4/A100), configurable override
6. **Quantization:** ✅ Auto-select (T4→4bit, L4→8bit, A100→fp16), configurable override
