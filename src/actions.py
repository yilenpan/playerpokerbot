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


@dataclass
class ParseResult:
    """Result of parsing with metadata for observability."""
    action: ParsedAction
    method: str  # "tag" | "regex_fold" | "regex_call" | "regex_raise" | "regex_allin" | "default"
    raw_match: str  # What was matched
    error: Optional[str] = None  # Why parsing failed (if fallback used)


class ActionParser:
    """Parse PHH-format actions from LLM responses."""

    RE_ACTION_TAG = re.compile(r'<action>\s*(.+?)\s*</action>', re.IGNORECASE | re.DOTALL)
    RE_FOLD = re.compile(r'\b(f|fold)\b', re.IGNORECASE)
    RE_CC = re.compile(r'\b(cc|call|check)\b', re.IGNORECASE)
    RE_CBR = re.compile(r'\b(?:cbr|bet|raise)\s*(?:to\s+)?(\d+)', re.IGNORECASE)
    RE_ALL_IN = re.compile(r'\b(?:all.?in|allin|shove)\b', re.IGNORECASE)

    def parse(self, response: str, can_check: bool = False, stack: int = 0) -> ParsedAction:
        """Parse action from LLM response."""
        result = self.parse_with_metadata(response, can_check, stack)
        return result.action

    def parse_with_metadata(self, response: str, can_check: bool = False, stack: int = 0) -> ParseResult:
        """Parse action from LLM response with full metadata for observability."""
        # Try action tag first
        tag_match = self.RE_ACTION_TAG.search(response)
        used_tag = tag_match is not None
        text = tag_match.group(1).strip() if tag_match else response

        # All-in
        if self.RE_ALL_IN.search(text):
            method = "tag" if used_tag else "regex_allin"
            return ParseResult(
                action=ParsedAction("all_in", stack),
                method=method,
                raw_match=text,
            )

        # Check/Call
        if self.RE_CC.search(text):
            action_type = "check" if can_check else "call"
            method = "tag" if used_tag else "regex_call"
            return ParseResult(
                action=ParsedAction(action_type),
                method=method,
                raw_match=text,
            )

        # Fold
        if self.RE_FOLD.search(text):
            method = "tag" if used_tag else "regex_fold"
            return ParseResult(
                action=ParsedAction("fold"),
                method=method,
                raw_match=text,
            )

        # Bet/Raise
        cbr_match = self.RE_CBR.search(text)
        if cbr_match:
            method = "tag" if used_tag else "regex_raise"
            return ParseResult(
                action=ParsedAction("raise", int(cbr_match.group(1))),
                method=method,
                raw_match=text,
            )

        # Default fallback
        default_action = "check" if can_check else "fold"
        return ParseResult(
            action=ParsedAction(default_action),
            method="default",
            raw_match=text[:100] if text else "",
            error=f"No valid action pattern found in response",
        )
