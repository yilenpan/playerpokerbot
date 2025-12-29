"""Metrics collection for poker evaluation."""

import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class HandResult:
    """Result of a single hand."""
    hand_id: int
    player_names: List[str]
    starting_stacks: List[int]
    ending_stacks: List[int]
    chip_deltas: List[int]
    hole_cards: Dict[str, Tuple[str, str]]  # player_name -> (card1, card2)
    board: List[str]
    winner_names: List[str]
    pot_size: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class SessionSummary:
    """Summary statistics for evaluation session."""
    total_hands: int
    duration_seconds: float
    hands_per_hour: float
    player_summaries: Dict[str, dict]  # player_name -> stats


class MetricsCollector:
    """Collects and aggregates poker evaluation metrics."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"session_{int(time.time())}"
        self.hand_results: List[HandResult] = []
        self.session_start: float = time.time()
        self.session_summary: Optional[SessionSummary] = None

    def log_hand(self, result: HandResult) -> None:
        """Log a completed hand."""
        self.hand_results.append(result)

    def finalize_session(self, player_stats: Dict[str, dict]) -> SessionSummary:
        """Calculate final session statistics."""
        duration = time.time() - self.session_start
        total_hands = len(self.hand_results)

        # Calculate per-player summaries
        player_summaries = {}
        player_names = set()
        for hr in self.hand_results:
            player_names.update(hr.player_names)

        for name in player_names:
            hands_played = 0
            hands_won = 0
            total_chip_delta = 0

            for hr in self.hand_results:
                if name in hr.player_names:
                    idx = hr.player_names.index(name)
                    hands_played += 1
                    total_chip_delta += hr.chip_deltas[idx]
                    if name in hr.winner_names:
                        hands_won += 1

            # Merge with player action stats
            action_stats = player_stats.get(name, {})

            player_summaries[name] = {
                "hands_played": hands_played,
                "hands_won": hands_won,
                "win_rate": hands_won / hands_played if hands_played > 0 else 0,
                "total_chip_delta": total_chip_delta,
                "bb_per_100": (total_chip_delta / hands_played * 100) if hands_played > 0 else 0,
                **action_stats,
            }

        self.session_summary = SessionSummary(
            total_hands=total_hands,
            duration_seconds=duration,
            hands_per_hour=(total_hands / duration * 3600) if duration > 0 else 0,
            player_summaries=player_summaries,
        )

        return self.session_summary

    def to_dict(self) -> dict:
        """Export metrics as dictionary."""
        return {
            "session_id": self.session_id,
            "hand_results": [
                {
                    "hand_id": hr.hand_id,
                    "player_names": hr.player_names,
                    "chip_deltas": hr.chip_deltas,
                    "hole_cards": hr.hole_cards,
                    "board": hr.board,
                    "winner_names": hr.winner_names,
                    "pot_size": hr.pot_size,
                    "timestamp": hr.timestamp,
                }
                for hr in self.hand_results
            ],
            "summary": {
                "total_hands": self.session_summary.total_hands,
                "duration_seconds": self.session_summary.duration_seconds,
                "hands_per_hour": self.session_summary.hands_per_hour,
                "player_summaries": self.session_summary.player_summaries,
            } if self.session_summary else None,
        }

    def to_json(self, indent: int = 2) -> str:
        """Export metrics as JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def print_summary(self, big_blind: int = 100) -> None:
        """Print human-readable summary."""
        if not self.session_summary:
            print("No session summary available. Call finalize_session() first.")
            return

        print("\n" + "=" * 70)
        print("EVALUATION RESULTS")
        print("=" * 70)

        print(f"\nSession: {self.session_id}")
        print(f"Duration: {self.session_summary.duration_seconds:.1f}s")
        print(f"Hands: {self.session_summary.total_hands}")
        print(f"Rate: {self.session_summary.hands_per_hour:.0f} hands/hour")

        print(f"\n{'Model':<25} {'Hands':>8} {'Wins':>8} {'Win%':>8} {'BB/100':>10}")
        print("-" * 70)

        for name, stats in sorted(
            self.session_summary.player_summaries.items(),
            key=lambda x: -x[1].get("bb_per_100", 0)
        ):
            bb_per_100 = stats.get("total_chip_delta", 0) / max(stats.get("hands_played", 1), 1) * 100 / big_blind
            print(
                f"{name:<25} "
                f"{stats.get('hands_played', 0):>8} "
                f"{stats.get('hands_won', 0):>8} "
                f"{stats.get('win_rate', 0)*100:>7.1f}% "
                f"{bb_per_100:>+10.2f}"
            )

        print("=" * 70)
