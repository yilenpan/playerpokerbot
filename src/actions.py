"""Action parsing for poker."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedAction:
    """Parsed poker action."""
    action_type: str  # fold, check, call, raise, all_in, quit, error
    amount: Optional[int] = None
    error_message: Optional[str] = None  # For error actions

    def __str__(self):
        if self.action_type == "error":
            return f"Error: {self.error_message or 'Unknown error'}"
        if self.action_type in ("fold", "check", "call"):
            return self.action_type.capitalize()
        elif self.amount:
            return f"{self.action_type.capitalize()} {self.amount}"
        return self.action_type


class ActionParser:
    """Parse PHH-format actions from LLM responses."""

    RE_ACTION_TAG = re.compile(r'<action>\s*(.+?)\s*</action>', re.IGNORECASE | re.DOTALL)
    RE_FOLD = re.compile(r'\b(f|fold)\b', re.IGNORECASE)
    RE_CC = re.compile(r'\b(cc|call|check)\b', re.IGNORECASE)
    RE_CBR = re.compile(r'\b(?:cbr|bet|raise)\s*(\d+)', re.IGNORECASE)
    RE_ALL_IN = re.compile(r'\b(?:all.?in|allin|shove)\b', re.IGNORECASE)

    def parse(self, response: str, can_check: bool = False, stack: int = 0) -> ParsedAction:
        """Parse action from LLM response."""
        # Try action tag first
        match = self.RE_ACTION_TAG.search(response)
        text = match.group(1).strip() if match else response

        if self.RE_ALL_IN.search(text):
            return ParsedAction("all_in", stack)
        if self.RE_CC.search(text):
            return ParsedAction("check" if can_check else "call")
        if self.RE_FOLD.search(text):
            return ParsedAction("fold")

        match = self.RE_CBR.search(text)
        if match:
            return ParsedAction("raise", int(match.group(1)))

        # Default
        return ParsedAction("check" if can_check else "fold")
