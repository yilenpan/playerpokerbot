"""Card utilities for poker."""

SUIT_SYMBOLS = {"c": "♣", "d": "♦", "h": "♥", "s": "♠"}
RANK_ORDER = "23456789TJQKA"

# ANSI colors
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
DIM = "\033[2m"


def pretty_card(card) -> str:
    """Convert card to pretty format with suit symbol."""
    card_str = str(card)

    # Handle PokerKit Card objects (e.g., "DEUCE OF HEARTS (2H)")
    if "(" in card_str and ")" in card_str:
        start = card_str.rfind("(") + 1
        end = card_str.rfind(")")
        card_str = card_str[start:end]

    if len(card_str) >= 2:
        rank = card_str[:-1].upper()
        suit = card_str[-1].lower()
        symbol = SUIT_SYMBOLS.get(suit, suit)
        if suit in ("d", "h"):
            return f"{RED}{rank}{symbol}{RESET}"
        return f"{rank}{symbol}"
    return card_str


def format_cards(cards) -> str:
    """Format list of cards."""
    if not cards:
        return f"{DIM}[ ]{RESET}"
    return "[" + " ".join(pretty_card(c) for c in cards) + "]"


def score_hole_cards(c1: str, c2: str) -> int:
    """Simple preflop hand strength (higher = better, max ~169)."""
    r1 = c1[0].upper() if c1 else "2"
    r2 = c2[0].upper() if c2 else "2"
    s1 = c1[-1].lower() if len(c1) > 1 else "x"
    s2 = c2[-1].lower() if len(c2) > 1 else "y"

    v1 = RANK_ORDER.index(r1) if r1 in RANK_ORDER else 0
    v2 = RANK_ORDER.index(r2) if r2 in RANK_ORDER else 0

    # Pairs are strong
    if r1 == r2:
        return 130 + v1 * 3

    suited = 15 if s1 == s2 else 0
    high, low = max(v1, v2), min(v1, v2)
    gap = high - low
    connected = 10 if gap == 1 else 5 if gap == 2 else 0

    return high * 8 + low * 2 + suited + connected
