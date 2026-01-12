"""Player implementations for poker."""

import json
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

try:
    from .cards import pretty_card, format_cards, score_hole_cards, RESET, BOLD, RED, GREEN, CYAN
    from .actions import ParsedAction, ActionParser
except ImportError:
    from cards import pretty_card, format_cards, score_hole_cards, RESET, BOLD, RED, GREEN, CYAN
    from actions import ParsedAction, ActionParser


SYSTEM_PROMPT = """You are an expert poker player. Analyze and decide the optimal action.

Output format: <action>ACTION</action>
- <action>f</action> = fold
- <action>cc</action> = call/check
- <action>cbr X</action> = bet/raise to X (multiple of big blind)

VALID:
<action>f</action>
<action>cc</action>
<action>cbr 6</action>

INVALID:
<action>fold</action> -- NOT PHH FORMAT
<action>p6 cc</action> -- DO NOT SPECIFY PLAYER
<action>cbr 1 5</action> -- INVALID PHH

Think first, then output ONE action tag."""


class OllamaPlayer:
    """Ollama-based poker player."""

    def __init__(
        self,
        name: str,
        model: str,
        endpoint: str = "http://localhost:11434",
        temperature: float = 0.6,
        max_tokens: int = 2048,
        trace_file: Optional[Path] = None,
    ):
        self.name = name
        self.model = model
        self.endpoint = endpoint
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.parser = ActionParser()
        self.trace_file = trace_file

    def check_connection(self) -> bool:
        """Check Ollama connection."""
        try:
            r = requests.get(f"{self.endpoint}/api/tags", timeout=5)
            if r.status_code == 200:
                models = [m.get("name", "") for m in r.json().get("models", [])]
                return any(self.model in m or m in self.model for m in models)
        except Exception:
            pass
        return False

    def shutdown(self) -> bool:
        """Unload model from Ollama to free memory. Returns True if successful."""
        try:
            # Send a request with keep_alive=0 to unload the model
            payload = {
                "model": self.model,
                "keep_alive": 0,
            }
            r = requests.post(f"{self.endpoint}/api/generate", json=payload, timeout=10)
            if r.status_code == 200:
                print(f"{GREEN}[{self.name}] Model unloaded{RESET}")
                return True
            else:
                print(f"{RED}[{self.name}] Failed to unload model: {r.status_code}{RESET}")
                return False
        except Exception as e:
            print(f"{RED}[{self.name}] Error unloading model: {e}{RESET}")
            return False

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
        """Get action from Ollama."""
        prompt = self._build_prompt(hole_cards, board, pot, to_call, stack, position, num_players)

        try:
            response = self._call_api(prompt)
            can_check = to_call == 0
            return self.parser.parse(response, can_check, stack)
        except Exception as e:
            error_msg = str(e)
            print(f"{RED}[{self.name}] Model error: {error_msg}{RESET}")
            return ParsedAction("error", error_message=error_msg)

    def _build_prompt(self, hole_cards, board, pot, to_call, stack, position, num_players) -> str:
        """Build prompt."""
        c1, c2 = hole_cards
        lines = [
            f"Playing {num_players}-handed No-Limit Hold'em.",
            f"Position: {position}",
            f"Stack: {stack} chips",
            f"",
            f"Hole cards: {pretty_card(c1)} {pretty_card(c2)}",
        ]

        if not board:
            strength = score_hole_cards(c1, c2)
            lines.append(f"Preflop strength: {strength}/169")
        else:
            lines.append(f"Board: {' '.join(pretty_card(c) for c in board)}")

        lines.extend([f"", f"Pot: {pot} chips"])

        if to_call > 0:
            lines.append(f"To call: {to_call} chips")
            lines.append(f"Actions: Fold, Call {to_call}, Raise")
        else:
            lines.append(f"Actions: Check, Bet")

        return "\n".join(lines)

    def _call_api(self, prompt: str) -> str:
        """Call Ollama API."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens}
        }

        r = requests.post(f"{self.endpoint}/api/chat", json=payload, timeout=120)
        r.raise_for_status()
        result = r.json()

        msg = result.get("message", {})
        content = msg.get("content", "")
        thinking = msg.get("thinking", "")

        # Log reasoning trace if trace file configured
        if self.trace_file:
            self._log_trace(prompt, thinking, content)

        return content if content else thinking

    def _log_trace(self, prompt: str, thinking: str, content: str):
        """Log reasoning trace to file."""
        trace = {
            "timestamp": datetime.now().isoformat(),
            "player": self.name,
            "model": self.model,
            "prompt": prompt,
            "thinking": thinking,
            "response": content,
        }
        with open(self.trace_file, "a") as f:
            f.write(json.dumps(trace) + "\n")


class HumanPlayer:
    """Interactive human player."""

    def __init__(self, name: str = "You"):
        self.name = name

    def get_action(
        self,
        hole_cards: Tuple[str, str],
        board: List[str],
        pot: int,
        to_call: int,
        stack: int,
        min_raise: int,
        max_raise: int,
    ) -> ParsedAction:
        """Get action from human via terminal."""
        print()
        print(f"  {BOLD}Your cards:{RESET} {format_cards(hole_cards)}")
        print(f"  {BOLD}Pot:{RESET} {pot} chips")
        if to_call > 0:
            print(f"  {BOLD}To call:{RESET} {to_call} chips")
        print()

        # Show options
        print(f"  {CYAN}[C]{RESET} {'Check' if to_call == 0 else f'Call {to_call}'}")
        if to_call > 0:
            print(f"  {CYAN}[F]{RESET} Fold")
        print(f"  {CYAN}[R]{RESET} Raise (min: {min_raise}, max: {max_raise})")
        print(f"  {CYAN}[A]{RESET} All-in ({stack})")
        print(f"  {CYAN}[Q]{RESET} Quit")
        print()

        while True:
            try:
                inp = input(f"  {BOLD}Your action:{RESET} ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return ParsedAction("quit")

            if not inp:
                continue

            if inp in ("q", "quit"):
                return ParsedAction("quit")
            if inp in ("f", "fold"):
                if to_call == 0:
                    print(f"  {RED}Can't fold when you can check!{RESET}")
                    continue
                return ParsedAction("fold")
            if inp in ("c", "call", "check"):
                return ParsedAction("check" if to_call == 0 else "call")
            if inp in ("a", "all", "allin"):
                return ParsedAction("all_in", stack)
            if inp.startswith("r") or inp.startswith("b"):
                parts = inp.split()
                if len(parts) >= 2:
                    try:
                        amt = int(parts[1])
                        if amt < min_raise:
                            print(f"  {RED}Minimum raise is {min_raise}{RESET}")
                            continue
                        if amt > max_raise:
                            print(f"  {RED}Maximum is {max_raise}{RESET}")
                            continue
                        return ParsedAction("raise", amt)
                    except ValueError:
                        pass
                # Prompt for amount
                try:
                    amt_str = input(f"  Raise to ({min_raise}-{max_raise}): ").strip()
                    amt = int(amt_str)
                    if min_raise <= amt <= max_raise:
                        return ParsedAction("raise", amt)
                    print(f"  {RED}Invalid amount{RESET}")
                except (ValueError, EOFError):
                    print(f"  {RED}Invalid amount{RESET}")
                continue

            print(f"  {RED}Unknown command. Use C/F/R/A/Q{RESET}")
