"""Transformers-based player using direct model.generate()."""

import time
from dataclasses import dataclass
from typing import Any, List, Tuple

import torch

# Import from parent package
try:
    from ..actions import ParsedAction, ActionParser
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from actions import ParsedAction, ActionParser


@dataclass
class ActionRecord:
    """Record of a single action decision."""
    hand_id: int
    street: str
    hole_cards: Tuple[str, str]
    board: List[str]
    pot: int
    to_call: int
    stack: int
    position: str
    action: ParsedAction
    thinking: str           # Content inside <think>...</think>
    response: str           # Content after </think>
    latency_ms: float
    tokens_generated: int


class TransformersPlayer:
    """Player using HuggingFace transformers with bitsandbytes."""

    SYSTEM_PROMPT = """You are an expert poker player. Analyze the game state and decide your action.

Output format: <action>ACTION</action>
- <action>f</action> = fold
- <action>cc</action> = check or call
- <action>cbr X</action> = bet or raise to X (multiple of big blind)

VALID:
<action>f</action>
<action>cc</action>
<action>cbr 6</action>

INVALID:
<action>fold</action> -- NOT PHH FORMAT
<action>p6 cc</action> -- DO NOT SPECIFY PLAYER
<action>cbr 1 5</action> -- INVALID PHH

Think step by step, then output exactly ONE action tag."""

    # Token ID for </think> in Qwen3 thinking models
    THINK_END_TOKEN_ID = 151668

    def __init__(
        self,
        name: str,
        model: Any,  # PreTrainedModel
        tokenizer: Any,  # PreTrainedTokenizer
        temperature: float = 0.6,
        max_new_tokens: int = 512,
    ):
        self.name = name
        self.model = model
        self.tokenizer = tokenizer
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens

        self.parser = ActionParser()
        self.action_history: List[ActionRecord] = []
        self._hand_id = 0
        self._street = "preflop"

        # Ensure pad token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def set_hand_context(self, hand_id: int, street: str) -> None:
        """Set context for action logging."""
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
        """Get action via model.generate() using simple prompt format."""
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

    def get_action_with_prompt(
        self,
        prompt_text: str,
        hole_cards: Tuple[str, str],
        board: List[str],
        pot: int,
        to_call: int,
        stack: int,
        position: str,
    ) -> ParsedAction:
        """Get action using a pre-built prompt (pokergpt format)."""
        start = time.perf_counter()

        # Format as chat with system prompt
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ]
        full_prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        try:
            thinking, response, tokens_gen = self._generate(full_prompt)
            can_check = to_call == 0
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
            thinking=thinking[:1000],
            response=response[:500],
            latency_ms=latency,
            tokens_generated=tokens_gen,
        ))

        return action

    def get_last_record(self):
        """Get the last action record."""
        return self.action_history[-1] if self.action_history else None

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
        """Clear action history for new session."""
        self.action_history = []
