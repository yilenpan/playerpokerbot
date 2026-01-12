"""Prompt builder matching pokergpt format for LLM evaluation."""

from typing import List, Tuple, Optional

# Card display constants
SUIT_MAP = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}

# Preflop scoring constants
RANK_ORDER = "23456789TJQKA"
RANK_VALUE = {r: i for i, r in enumerate(RANK_ORDER, start=2)}


def pretty_card(card: str) -> str:
    """
    Format a card string with pretty suit symbols.

    Args:
        card: Card string like 'As' or 'Kd'

    Returns:
        Pretty formatted card like 'A♠' or 'K♦'
    """
    if len(card) < 2:
        return card
    rank = card[:-1]
    suit = SUIT_MAP.get(card[-1].lower(), card[-1])
    return f"{rank}{suit}"


def score_hole_cards(c1: str, c2: str) -> int:
    """
    Score preflop hole cards on a scale where higher is better.

    Args:
        c1: First card string like 'As'
        c2: Second card string like 'Kd'

    Returns:
        Integer score where 128 is pair Aces (best possible)
    """
    r1 = c1[0].upper() if c1 else "2"
    r2 = c2[0].upper() if c2 else "2"

    v1 = RANK_VALUE.get(r1, 2)
    v2 = RANK_VALUE.get(r2, 2)
    high, low = max(v1, v2), min(v1, v2)

    is_pair = v1 == v2
    is_suited = len(c1) > 1 and len(c2) > 1 and c1[-1].lower() == c2[-1].lower()

    # Pairs get bonus scoring
    if is_pair:
        return 100 + high * 2

    # Base score from card values
    score = high * 4 + low

    # Suited bonus
    if is_suited:
        score += 12

    # Gap penalty/bonus
    gap = high - low
    if gap == 1:  # Connected
        score += 6
    elif gap == 2:  # One-gapper
        score += 3

    # Premium high cards
    if high >= 11 and low >= 10:  # Both broadway
        score += 6

    # Ace bonus
    if high == 14:
        score += 4

    return score


def get_position_name(player_idx: int, num_players: int, button_idx: int) -> str:
    """
    Get position name for a player.

    Args:
        player_idx: Player's seat position (0-indexed)
        num_players: Total number of players
        button_idx: Button position (0-indexed)

    Returns:
        Position name (UTG, UTG+1, MP, MP+1, HJ, CO, BTN, SB, BB)
    """
    if num_players < 2:
        return "Unknown"

    # Calculate position relative to button (0 = BTN, 1 = SB, 2 = BB, etc.)
    offset = (player_idx - button_idx) % num_players

    # Heads-up (2 players)
    if num_players == 2:
        return "BTN/SB" if offset == 0 else "BB"

    # 3+ players
    if offset == 0:
        return "BTN"
    elif offset == 1:
        return "SB"
    elif offset == 2:
        return "BB"

    # For 3 players, only BTN, SB, BB exist
    if num_players == 3:
        return f"P{player_idx + 1}"

    # Position mappings for 4-9+ players
    if num_players == 4:
        if offset == 3:
            return "CO"
    elif num_players == 5:
        if offset == 3:
            return "MP"
        elif offset == 4:
            return "CO"
    elif num_players == 6:
        if offset == 3:
            return "UTG"
        elif offset == 4:
            return "MP"
        elif offset == 5:
            return "CO"
    elif num_players == 7:
        if offset == 3:
            return "UTG"
        elif offset == 4:
            return "UTG+1"
        elif offset == 5:
            return "MP"
        elif offset == 6:
            return "CO"
    elif num_players == 8:
        if offset == 3:
            return "UTG"
        elif offset == 4:
            return "UTG+1"
        elif offset == 5:
            return "MP"
        elif offset == 6:
            return "MP+1"
        elif offset == 7:
            return "CO"
    elif num_players == 9:
        if offset == 3:
            return "UTG"
        elif offset == 4:
            return "UTG+1"
        elif offset == 5:
            return "UTG+2"
        elif offset == 6:
            return "MP"
        elif offset == 7:
            return "MP+1"
        elif offset == 8:
            return "CO"
    else:
        # 10+ players
        if offset >= 3:
            co_offset = num_players - 1
            if offset == co_offset:
                return "CO"
            elif offset == co_offset - 1:
                return "MP+1"
            elif offset == co_offset - 2:
                return "MP"
            else:
                utg_offset = offset - 3
                if utg_offset == 0:
                    return "UTG"
                else:
                    return f"UTG+{utg_offset}"

    return f"P{player_idx + 1}"


class PromptBuilder:
    """Builds prompts in pokergpt format for LLM poker players."""

    def __init__(self, big_blind: int = 100):
        """
        Initialize prompt builder.

        Args:
            big_blind: Big blind amount in chips (for BB normalization)
        """
        self.big_blind = big_blind
        self.action_history: List[str] = []

    def record_deal(self, player_label: str, is_hero: bool = False, blind_note: str = ""):
        """Record a hole card deal."""
        suffix = f" ({blind_note})" if blind_note else ""
        if is_hero:
            self.action_history.append(f"{player_label} were dealt your hole cards{suffix}.")
        else:
            self.action_history.append(f"{player_label} was dealt hole cards{suffix}.")

    def record_board(self, board_cards: List[str]):
        """Record a board deal."""
        n = len(board_cards)
        if n == 3:
            street = "Flop"
        elif n == 4:
            street = "Turn"
        elif n == 5:
            street = "River"
        else:
            street = "Board"
        pretty = " ".join(pretty_card(c) for c in board_cards)
        self.action_history.append(f"{street} dealt: {pretty}")

    def record_action(self, player_label: str, action: str, amount_bb: Optional[float] = None):
        """
        Record a player action.

        Args:
            player_label: Player label like "UTG" or "You (BTN)"
            action: Action type like "folded", "checked", "called", "bet/raised to"
            amount_bb: Amount in BB (if applicable)
        """
        if amount_bb is not None:
            self.action_history.append(f"{player_label} {action} {amount_bb:.1f} BB.")
        else:
            self.action_history.append(f"{player_label} {action}.")

    def reset_hand(self):
        """Reset action history for a new hand."""
        self.action_history = []

    def get_player_label(self, player_idx: int, hero_idx: int, positions: List[str]) -> str:
        """Get label for a player."""
        pos = positions[player_idx] if player_idx < len(positions) else f"P{player_idx + 1}"
        if player_idx == hero_idx:
            return f"You ({pos})"
        return pos

    def build_prompt(
        self,
        hero_idx: int,
        hero_cards: Tuple[str, str],
        board: List[str],
        stacks: List[int],
        bets: List[int],
        pot: int,
        to_call: int,
        min_raise: int,
        button_idx: int,
        num_players: int,
        street: str = "preflop",
    ) -> str:
        """
        Build a prompt in pokergpt format.

        Args:
            hero_idx: Hero player index (0-indexed)
            hero_cards: Tuple of hero's hole cards
            board: List of board cards
            stacks: List of stack sizes for all players
            bets: List of current street bets for all players
            pot: Total pot size
            to_call: Amount hero needs to call
            min_raise: Minimum raise amount
            button_idx: Button position index
            num_players: Number of players
            street: Current street name

        Returns:
            Formatted prompt string
        """
        bb = self.big_blind
        positions = [get_position_name(i, num_players, button_idx) for i in range(num_players)]
        hero_pos = positions[hero_idx]

        lines = [
            "You are an expert poker player and you are playing NT poker.",
            f"There are {num_players} players at the table.",
            f"You are in the {hero_pos} position.",
            "",
            "Stacks:",
        ]

        # Stacks for all players
        for i, stack in enumerate(stacks):
            label = self.get_player_label(i, hero_idx, positions)
            lines.append(f"- {label}: {stack / bb:.1f} BB")

        # Action history
        if self.action_history:
            lines.extend(["", "Actions so far:"])
            for action in self.action_history:
                lines.append(f"- {action}")

        # Hero's hole cards
        c1, c2 = hero_cards
        lines.extend([
            "",
            f"Your hole cards are: {pretty_card(c1)} {pretty_card(c2)}",
        ])

        # Hand strength or board
        if street == "preflop":
            strength = score_hole_cards(c1, c2)
            lines.append(f"Preflop hand strength score out of 128 (128 is pair Aces): {strength}")
        elif board:
            pretty_board = " ".join(pretty_card(c) for c in board)
            lines.append(f"The current board is: {pretty_board}")

        # Current bets
        if any(b > 0 for b in bets):
            lines.extend(["", "The current bets are:"])
            for i, bet in enumerate(bets):
                if bet > 0:
                    label = self.get_player_label(i, hero_idx, positions)
                    lines.append(f"- {label}: {bet / bb:.1f} BB")

        # Pot and turn
        lines.extend([
            "",
            f"The current pot size is: {pot / bb:.1f} BB",
            "It is now your turn to act.",
            f"Minimum bet: 1 BB.",
            "",
            "Available actions:",
        ])

        # Available actions
        if to_call > 0:
            lines.append("- Fold")
            lines.append(f"- Call {to_call / bb:.0f} BB")
            lines.append(f"- Raise (minimum: {min_raise / bb:.0f} BB)")
        else:
            lines.append("- Check")
            lines.append(f"- Bet (minimum: 1 BB)")

        return "\n".join(lines)
