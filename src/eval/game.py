"""Evaluation poker game - fully automated, no human input."""

import random
from typing import Callable, List, Optional

from pokerkit import Automation, NoLimitTexasHoldem

try:
    from ..actions import ParsedAction
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from actions import ParsedAction

from .metrics import HandResult, MetricsCollector
from .transformers_player import TransformersPlayer


class EvalPokerGame:
    """Poker game for automated LLM evaluation."""

    def __init__(
        self,
        players: List[TransformersPlayer],
        starting_stack: int = 10000,
        small_blind: int = 50,
        big_blind: int = 100,
        metrics_collector: Optional[MetricsCollector] = None,
        verbose: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        self.players = players
        self.num_players = len(players)
        self.starting_stack = starting_stack
        self.small_blind = small_blind
        self.big_blind = big_blind

        self.stacks = [starting_stack] * self.num_players
        self.button = 0
        self.hand_num = 0

        self.metrics = metrics_collector or MetricsCollector()
        self.verbose = verbose
        self.progress_callback = progress_callback

    def play_session(self, num_hands: int = 100) -> MetricsCollector:
        """Play automated session."""
        if self.verbose:
            print(f"Starting evaluation: {num_hands} hands, {self.num_players} players")
            for i, p in enumerate(self.players):
                print(f"  Player {i}: {p.name}")

        for hand_idx in range(num_hands):
            self._play_hand()

            # Progress callback
            if self.progress_callback:
                self.progress_callback(hand_idx + 1, num_hands)

            # Check for bust players
            active_players = sum(1 for s in self.stacks if s > 0)
            if active_players < 2:
                if self.verbose:
                    print(f"Session ended: only {active_players} player(s) remaining")
                break

        self._finalize_session()
        return self.metrics

    def _play_hand(self) -> None:
        """Play single hand - fully automated."""
        self.hand_num += 1
        self.button = (self.button + 1) % self.num_players

        # Set hand context for all players
        for player in self.players:
            player.set_hand_context(self.hand_num, "preflop")

        # Skip hands where players can't post blinds
        sb_pos = (self.button + 1) % self.num_players
        bb_pos = (self.button + 2) % self.num_players
        if self.stacks[sb_pos] <= 0 or self.stacks[bb_pos] <= 0:
            return

        # Record starting stacks for this hand
        starting_stacks = self.stacks.copy()

        # Create PokerKit state
        try:
            state = NoLimitTexasHoldem.create_state(
                automations=(
                    Automation.ANTE_POSTING,
                    Automation.BET_COLLECTION,
                    Automation.BLIND_OR_STRADDLE_POSTING,
                    Automation.CARD_BURNING,
                    Automation.HOLE_DEALING,
                    Automation.HOLE_CARDS_SHOWING_OR_MUCKING,
                    Automation.HAND_KILLING,
                    Automation.CHIPS_PUSHING,
                    Automation.CHIPS_PULLING,
                ),
                ante_trimming_status=True,
                raw_antes={-1: 0},
                raw_blinds_or_straddles=(self.small_blind, self.big_blind),
                min_bet=self.big_blind,
                raw_starting_stacks=self.stacks.copy(),
                player_count=self.num_players,
            )
        except Exception as e:
            if self.verbose:
                print(f"Error creating hand state: {e}")
            return

        # Get hole cards
        hole_cards = []
        for i in range(self.num_players):
            cards = state.hole_cards[i]
            if cards and len(cards) >= 2:
                hole_cards.append((str(cards[0]), str(cards[1])))
            else:
                hole_cards.append(("??", "??"))

        # Get deck for community cards
        dealable = list(state.get_dealable_cards())
        random.shuffle(dealable)
        deck = dealable

        board = []
        streets = ["preflop", "flop", "turn", "river"]

        for street in streets:
            if state.status is False:
                break

            # Update street context for all players
            for player in self.players:
                player.set_hand_context(self.hand_num, street)

            # Deal community cards
            if street == "flop":
                board = [deck.pop(), deck.pop(), deck.pop()]
                for card in board:
                    try:
                        state.deal_board(card)
                    except Exception:
                        pass
            elif street in ("turn", "river"):
                board.append(deck.pop())
                try:
                    state.deal_board(board[-1])
                except Exception:
                    pass

            # Betting loop
            board_strs = [str(c) for c in board]
            while state.actor_index is not None:
                actor = state.actor_index
                player = self.players[actor]

                # Get game state for player
                pot = state.total_pot_amount if hasattr(state, 'total_pot_amount') else 0
                current_bet = max(state.bets) if state.bets else 0
                player_bet = state.bets[actor] if state.bets else 0
                to_call = current_bet - player_bet
                stack = state.stacks[actor]
                position = self._get_position_name(actor)

                # Get action from player
                action = player.get_action(
                    hole_cards[actor], board_strs, pot, to_call, stack,
                    position, self.num_players
                )

                if self.verbose:
                    print(f"  Hand {self.hand_num} | {street} | {player.name}: {action}")

                # Execute action
                self._execute_action(state, action)

        # Update stacks
        if hasattr(state, 'stacks'):
            for i in range(self.num_players):
                self.stacks[i] = state.stacks[i]

        # Calculate chip deltas
        chip_deltas = [self.stacks[i] - starting_stacks[i] for i in range(self.num_players)]

        # Determine winner(s)
        winners = [self.players[i].name for i, delta in enumerate(chip_deltas) if delta > 0]

        # Log hand result
        hand_result = HandResult(
            hand_id=self.hand_num,
            player_names=[p.name for p in self.players],
            starting_stacks=starting_stacks,
            ending_stacks=self.stacks.copy(),
            chip_deltas=chip_deltas,
            hole_cards={p.name: hole_cards[i] for i, p in enumerate(self.players)},
            board=[str(c) for c in board],
            winner_names=winners,
            pot_size=sum(abs(d) for d in chip_deltas if d < 0),
        )
        self.metrics.log_hand(hand_result)

    def _execute_action(self, state, action: ParsedAction) -> None:
        """Execute action on state with fallback chain."""
        try:
            if action.action_type == "fold":
                state.fold()
            elif action.action_type in ("check", "call"):
                state.check_or_call()
            elif action.action_type in ("raise", "bet"):
                state.complete_bet_or_raise_to(action.amount)
            elif action.action_type == "all_in":
                actor = state.actor_index
                stack = state.stacks[actor] + state.bets[actor]
                state.complete_bet_or_raise_to(stack)
        except Exception:
            try:
                state.check_or_call()
            except Exception:
                try:
                    state.fold()
                except Exception:
                    pass

    def _finalize_session(self) -> None:
        """Finalize session metrics."""
        self.metrics.finalize_session(
            player_stats={p.name: p.get_stats() for p in self.players}
        )

    def _get_position_name(self, idx: int) -> str:
        """Get position name relative to button."""
        positions_2 = ["SB", "BB"]
        positions_3 = ["BTN", "SB", "BB"]
        positions_4 = ["BTN", "CO", "SB", "BB"]
        positions_6 = ["BTN", "CO", "HJ", "LJ", "SB", "BB"]

        if self.num_players == 2:
            positions = positions_2
        elif self.num_players == 3:
            positions = positions_3
        elif self.num_players <= 4:
            positions = positions_4
        else:
            positions = positions_6[:self.num_players]

        rel_pos = (idx - self.button) % self.num_players
        return positions[rel_pos] if rel_pos < len(positions) else f"P{idx}"
