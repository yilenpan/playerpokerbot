"""Pretty hand logging for poker games."""

import os
from datetime import datetime
from typing import List, Dict, Optional

try:
    from .cards import SUIT_SYMBOLS, RANK_ORDER
except ImportError:
    from cards import SUIT_SYMBOLS, RANK_ORDER


class HandLogger:
    """Logs sampled poker hands to a file in a pretty format."""

    def __init__(self, log_dir: str = "logs", sample_rate: int = 5):
        """
        Initialize the hand logger.

        Args:
            log_dir: Directory to store log files
            sample_rate: Log every Nth hand (default: 5)
        """
        self.log_dir = log_dir
        self.sample_rate = sample_rate
        self.session_file: Optional[str] = None
        self._current_hand: Optional[Dict] = None

        # Create logs directory if needed
        os.makedirs(log_dir, exist_ok=True)

        # Create session log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = os.path.join(log_dir, f"poker_session_{timestamp}.log")

    def should_log(self, hand_num: int) -> bool:
        """Check if this hand should be logged."""
        return hand_num % self.sample_rate == 0

    def start_hand(
        self,
        hand_num: int,
        player_names: List[str],
        stacks: List[int],
        hole_cards: List[tuple],
        button_pos: int,
        sb_pos: int,
        bb_pos: int,
        blinds: tuple,
    ):
        """Start recording a new hand."""
        if not self.should_log(hand_num):
            self._current_hand = None
            return

        self._current_hand = {
            "hand_num": hand_num,
            "timestamp": datetime.now().isoformat(),
            "player_names": player_names,
            "stacks": stacks.copy(),
            "hole_cards": hole_cards,
            "button_pos": button_pos,
            "sb_pos": sb_pos,
            "bb_pos": bb_pos,
            "blinds": blinds,
            "streets": [],
            "current_street": None,
            "board": [],
            "final_stacks": None,
            "winners": [],
        }

    def start_street(self, street_name: str, board: List[str]):
        """Start recording a new street."""
        if self._current_hand is None:
            return

        self._current_hand["current_street"] = {
            "name": street_name,
            "board": [str(c) for c in board],
            "actions": [],
        }
        self._current_hand["board"] = [str(c) for c in board]

    def log_action(self, player_idx: int, player_name: str, action_str: str):
        """Log a player action."""
        if self._current_hand is None or self._current_hand["current_street"] is None:
            return

        self._current_hand["current_street"]["actions"].append({
            "player_idx": player_idx,
            "player_name": player_name,
            "action": action_str,
        })

    def end_street(self):
        """End the current street."""
        if self._current_hand is None or self._current_hand["current_street"] is None:
            return

        self._current_hand["streets"].append(self._current_hand["current_street"])
        self._current_hand["current_street"] = None

    def end_hand(self, final_stacks: List[int], winners: List[int], chips_won: int):
        """End the hand and write to log file."""
        if self._current_hand is None:
            return

        # End any unclosed street
        if self._current_hand["current_street"] is not None:
            self.end_street()

        self._current_hand["final_stacks"] = final_stacks
        self._current_hand["winners"] = winners
        self._current_hand["chips_won"] = chips_won

        # Write formatted hand to file
        self._write_hand()
        self._current_hand = None

    def _format_card(self, card: str) -> str:
        """Format a single card with suit symbol (no ANSI colors for log file)."""
        card_str = str(card)

        # Handle PokerKit Card objects
        if "(" in card_str and ")" in card_str:
            start = card_str.rfind("(") + 1
            end = card_str.rfind(")")
            card_str = card_str[start:end]

        if len(card_str) >= 2:
            rank = card_str[:-1].upper()
            suit = card_str[-1].lower()
            symbol = SUIT_SYMBOLS.get(suit, suit)
            return f"{rank}{symbol}"
        return card_str

    def _format_cards(self, cards: List) -> str:
        """Format a list of cards."""
        if not cards:
            return "[ ]"
        return "[" + " ".join(self._format_card(c) for c in cards) + "]"

    def _pad_line(self, content: str, width: int = 58) -> str:
        """Pad content to fit in a box line."""
        padding = max(0, width - len(content))
        return f"║{content}" + " " * padding + "║"

    def _write_hand(self):
        """Write the current hand to the log file."""
        if self._current_hand is None:
            return

        h = self._current_hand
        lines = []

        # Header
        lines.append("")
        lines.append("╔" + "═" * 58 + "╗")
        lines.append(f"║  🎴 HAND #{h['hand_num']:>4}  │  {h['timestamp'][:19]}  ║")
        lines.append("╠" + "═" * 58 + "╣")

        # Player info
        lines.append("║  PLAYERS" + " " * 49 + "║")
        lines.append("╟" + "─" * 58 + "╢")

        for i, name in enumerate(h["player_names"]):
            pos_tag = ""
            if i == h["button_pos"]:
                pos_tag = " [BTN]"
            elif i == h["sb_pos"]:
                pos_tag = " [SB]"
            elif i == h["bb_pos"]:
                pos_tag = " [BB]"

            hole = self._format_cards(h["hole_cards"][i]) if h["hole_cards"][i] else "[?? ??]"
            stack_str = f"${h['stacks'][i]:,}"
            line = f"║  {name[:12]:<12} {hole:<12} {stack_str:>10}{pos_tag:<8}"
            lines.append(line + " " * (58 - len(line) + 1) + "║")

        lines.append("╠" + "═" * 58 + "╣")

        # Blinds
        sb, bb = h["blinds"]
        lines.append(f"║  Blinds: ${sb}/${bb}" + " " * (58 - 17 - len(str(sb)) - len(str(bb))) + "║")
        lines.append("╠" + "═" * 58 + "╣")

        # Streets
        for street in h["streets"]:
            street_name = street["name"].upper()
            board_str = self._format_cards(street["board"]) if street["board"] else ""

            lines.append(f"║  ▶ {street_name} {board_str}" + " " * max(0, 58 - 5 - len(street_name) - len(board_str)) + "║")
            lines.append("╟" + "─" * 58 + "╢")

            for action in street["actions"]:
                player = action["player_name"][:12]
                act = action["action"]
                line = f"║    {player:<12}: {act}"
                lines.append(line + " " * max(0, 58 - len(line) + 1) + "║")

            if not street["actions"]:
                lines.append("║    (no actions)" + " " * 42 + "║")

            lines.append("╟" + "─" * 58 + "╢")

        # Final board
        if h["board"]:
            board_str = self._format_cards(h["board"])
            lines.append(f"║  Final Board: {board_str}" + " " * max(0, 58 - 15 - len(board_str)) + "║")
            lines.append("╠" + "═" * 58 + "╣")

        # Results
        lines.append("║  🏆 RESULTS" + " " * 46 + "║")
        lines.append("╟" + "─" * 58 + "╢")

        if h["winners"]:
            winner_names = [h["player_names"][w] for w in h["winners"]]
            winner_line = f"  Winner: {', '.join(winner_names)} (+${h['chips_won']:,})"
            lines.append(self._pad_line(winner_line))

        lines.append("╟" + "─" * 58 + "╢")
        lines.append("║  Final Stacks:" + " " * 43 + "║")

        for i, name in enumerate(h["player_names"]):
            if h["final_stacks"]:
                diff = h["final_stacks"][i] - h["stacks"][i]
                diff_str = f"+{diff}" if diff > 0 else str(diff)
                stack_str = f"${h['final_stacks'][i]:,}"
                content = f"    {name[:12]:<12}: {stack_str:>10} ({diff_str})"
            else:
                content = f"    {name[:12]:<12}: unknown"
            lines.append(self._pad_line(content))

        lines.append("╚" + "═" * 58 + "╝")
        lines.append("")

        # Write to file
        with open(self.session_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))
            f.write("\n")

    def log_session_start(self, num_players: int, starting_stack: int, blinds: tuple, num_hands: int):
        """Log session start info."""
        lines = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines.append("┌" + "─" * 58 + "┐")
        lines.append("│" + " " * 20 + "🃏 POKER SESSION 🃏" + " " * 19 + "│")
        lines.append("├" + "─" * 58 + "┤")
        lines.append(f"│  Started: {timestamp}" + " " * 27 + "│")
        lines.append(f"│  Players: {num_players}" + " " * (47 - len(str(num_players))) + "│")
        lines.append(f"│  Starting Stack: ${starting_stack:,}" + " " * max(0, 40 - len(str(starting_stack))) + "│")
        lines.append(f"│  Blinds: ${blinds[0]}/${blinds[1]}" + " " * max(0, 45 - len(str(blinds[0])) - len(str(blinds[1]))) + "│")
        lines.append(f"│  Planned Hands: {num_hands}" + " " * max(0, 41 - len(str(num_hands))) + "│")
        lines.append(f"│  Sample Rate: every {self.sample_rate} hands" + " " * max(0, 36 - len(str(self.sample_rate))) + "│")
        lines.append("└" + "─" * 58 + "┘")
        lines.append("")

        with open(self.session_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            f.write("\n")

    def log_session_end(self, hands_played: int, final_stacks: List[int], player_names: List[str], starting_stack: int):
        """Log session end summary."""
        lines = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines.append("")
        lines.append("┌" + "─" * 58 + "┐")
        lines.append("│" + " " * 18 + "📊 SESSION SUMMARY 📊" + " " * 18 + "│")
        lines.append("├" + "─" * 58 + "┤")
        lines.append(f"│  Ended: {timestamp}" + " " * 29 + "│")
        lines.append(f"│  Hands Played: {hands_played}" + " " * max(0, 42 - len(str(hands_played))) + "│")
        lines.append("├" + "─" * 58 + "┤")
        lines.append("│  Final Results:" + " " * 42 + "│")

        for i, name in enumerate(player_names):
            diff = final_stacks[i] - starting_stack
            diff_str = f"+{diff}" if diff > 0 else str(diff)
            emoji = "🏆" if diff > 0 else "📉" if diff < 0 else "➖"
            stack_str = f"${final_stacks[i]:,}"
            line = f"│    {emoji} {name[:12]:<12}: {stack_str:>10} ({diff_str})"
            lines.append(line + " " * max(0, 58 - len(line) + 1) + "│")

        lines.append("└" + "─" * 58 + "┘")
        lines.append("")

        with open(self.session_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))
            f.write("\n")

        print(f"\n  📝 Hand log saved to: {self.session_file}")
