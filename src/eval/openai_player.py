"""OpenAI API-based player for poker evaluation."""

import os
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

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
    thinking: str
    response: str
    latency_ms: float
    tokens_input: int
    tokens_output: int


class OpenAIPlayer:
    """Player using OpenAI API (GPT-4, etc.)."""

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

    def __init__(
        self,
        name: str,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        temperature: float = 0.6,
        max_tokens: int = 512,
    ):
        if OpenAI is None:
            raise ImportError("openai package not installed. Run: pip install openai")

        self.name = name
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize client with API key from param or env
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

        self.parser = ActionParser()
        self.action_history: List[ActionRecord] = []
        self._hand_id = 0
        self._street = "preflop"

        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0

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
        """Get action via OpenAI API."""
        start = time.perf_counter()

        user_msg = self._build_prompt(
            hole_cards, board, pot, to_call, stack, position, num_players
        )

        try:
            response_text, tokens_in, tokens_out = self._call_api(user_msg)
            can_check = to_call == 0
            action = self.parser.parse(response_text, can_check, stack)
            thinking = ""  # OpenAI doesn't have explicit thinking blocks
        except Exception as e:
            response_text = f"ERROR: {e}"
            tokens_in = 0
            tokens_out = 0
            action = ParsedAction("fold")
            thinking = ""

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
            thinking=thinking,
            response=response_text[:500],
            latency_ms=latency,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
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

        return f"""Game: {num_players}-handed No-Limit Hold'em
Position: {position}
Stack: {stack}
Hole Cards: {hole_cards[0]} {hole_cards[1]}
Board: {board_str}
Pot: {pot}
To Call: {to_call}

What is your action?"""

    def _call_api(self, user_msg: str) -> Tuple[str, int, int]:
        """Call OpenAI API. Returns (response_text, input_tokens, output_tokens)."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        content = response.choices[0].message.content or ""
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0

        # Track cumulative usage
        self.total_input_tokens += tokens_in
        self.total_output_tokens += tokens_out

        return content, tokens_in, tokens_out

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
        tokens_out = [a.tokens_output for a in self.action_history]

        return {
            "total_actions": total,
            "vpip": len(vpip_actions) / len(preflop) if preflop else 0,
            "pfr": len(pfr_actions) / len(preflop) if preflop else 0,
            "aggression_factor": bets_raises / calls if calls > 0 else float('inf'),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "avg_tokens": sum(tokens_out) / len(tokens_out) if tokens_out else 0,
            "fold_pct": sum(1 for a in self.action_history if a.action.action_type == "fold") / total,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
        }

    def get_estimated_cost(self) -> float:
        """Estimate API cost in USD based on GPT-4 pricing."""
        # GPT-4 pricing as of 2024: $30/1M input, $60/1M output
        # GPT-4-turbo: $10/1M input, $30/1M output
        if "turbo" in self.model.lower() or "4o" in self.model.lower():
            input_cost = self.total_input_tokens * 10 / 1_000_000
            output_cost = self.total_output_tokens * 30 / 1_000_000
        else:
            input_cost = self.total_input_tokens * 30 / 1_000_000
            output_cost = self.total_output_tokens * 60 / 1_000_000
        return input_cost + output_cost

    def reset_history(self) -> None:
        """Clear action history for new session."""
        self.action_history = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
