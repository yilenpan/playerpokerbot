"""Tests for action parsing."""

import pytest

from src.actions import ActionParser, ParsedAction


class TestActionParserRegexFallbacks:
    """Tests for regex fallbacks when no action tags are present."""

    def setup_method(self):
        self.parser = ActionParser()

    def test_fold_keyword(self):
        """Parser should recognize 'I fold' without tags."""
        assert self.parser.parse("I fold").action_type == "fold"

    def test_call_keyword(self):
        """Parser should recognize 'call' without tags."""
        assert self.parser.parse("call").action_type == "call"

    def test_raise_to_amount(self):
        """Parser should recognize 'raise to 300' without tags."""
        result = self.parser.parse("raise to 300")
        assert result.action_type == "raise"
        assert result.amount == 300

    def test_all_in_with_stack(self):
        """Parser should recognize 'all in' and set amount to stack."""
        result = self.parser.parse("all in", stack=1000)
        assert result.action_type == "all_in"
        assert result.amount == 1000
