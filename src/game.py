"""Poker game engine using PokerKit."""

import os
import random
import time
from typing import List, Dict

from pokerkit import NoLimitTexasHoldem, Automation

try:
    from .cards import (
        pretty_card, format_cards,
        RESET, BOLD, RED, GREEN, YELLOW, BLUE, CYAN
    )
    from .actions import ParsedAction
    from .players import OllamaPlayer, HumanPlayer
except ImportError:
    from cards import (
        pretty_card, format_cards,
        RESET, BOLD, RED, GREEN, YELLOW, BLUE, CYAN
    )
    from actions import ParsedAction
    from players import OllamaPlayer, HumanPlayer


class PokerGame:
    """Poker game engine using PokerKit."""

    def __init__(
        self,
        human: HumanPlayer,
        opponents: List[OllamaPlayer],
        starting_stack: int = 10000,
        small_blind: int = 50,
        big_blind: int = 100,
    ):
        self.human = human
        self.opponents = opponents
        self.num_players = 1 + len(opponents)
        self.starting_stack = starting_stack
        self.small_blind = small_blind
        self.big_blind = big_blind

        # All players: human at index 0
        self.players = [human] + opponents
        self.stacks = [starting_stack] * self.num_players
        self.button = 0
        self.hand_num = 0

    def play_session(self, num_hands: int = 10):
        """Play a session of hands."""
        print()
        print(f"{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}{CYAN}  POKER: You vs {len(self.opponents)} Ollama Model(s){RESET}")
        print(f"{BOLD}{'='*60}{RESET}")
        print(f"  Players: {self.num_players}")
        print(f"  Stack: {self.starting_stack}")
        print(f"  Blinds: {self.small_blind}/{self.big_blind}")
        print(f"  Hands: {num_hands}")
        print(f"{BOLD}{'='*60}{RESET}")

        for _ in range(num_hands):
            if not self._play_hand():
                break

            # Check if anyone is broke
            if any(s <= 0 for s in self.stacks):
                break

        self._show_final_results()
        self.shutdown()

    def _play_hand(self) -> bool:
        """Play a single hand. Returns False to quit."""
        self.hand_num += 1

        # Rotate button
        self.button = (self.button + 1) % self.num_players

        # Calculate positions
        sb_pos = (self.button + 1) % self.num_players
        bb_pos = (self.button + 2) % self.num_players

        print()
        print(f"{BOLD}{'─'*60}{RESET}")
        print(f"{BOLD}  Hand #{self.hand_num}  |  Button: {self._player_name(self.button)}{RESET}")
        print(f"{BOLD}  SB: {self._player_name(sb_pos)}  |  BB: {self._player_name(bb_pos)}{RESET}")
        print(f"{BOLD}{'─'*60}{RESET}")

        # Show stacks with positions
        for i in range(self.num_players):
            name = self._player_name(i)
            pos_tag = ""
            if i == self.button:
                pos_tag = f" {YELLOW}[BTN]{RESET}"
            elif i == sb_pos:
                pos_tag = f" {CYAN}[SB]{RESET}"
            elif i == bb_pos:
                pos_tag = f" {CYAN}[BB]{RESET}"
            print(f"  {name}: {self.stacks[i]} chips{pos_tag}")

        # Create hand with full automations
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
            print(f"{RED}Error creating hand: {e}{RESET}")
            return True

        # Get hole cards dealt by PokerKit
        hole_cards = []
        for i in range(self.num_players):
            cards = state.hole_cards[i]
            if cards and len(cards) >= 2:
                hole_cards.append((str(cards[0]), str(cards[1])))
            else:
                hole_cards.append(("??", "??"))

        # Get dealable cards from PokerKit (respects what's already dealt)
        dealable = list(state.get_dealable_cards())
        random.shuffle(dealable)
        deck = dealable  # Keep as Card objects for deal_board()

        # Show human's cards
        human_cards = hole_cards[0]
        print()
        print(f"  {GREEN}{BOLD}Your cards: {format_cards(human_cards)}{RESET}")

        board = []
        quit_requested = False
        stacks_before = self.stacks.copy()  # Track for winner detection

        # Betting rounds
        streets = ["Preflop", "Flop", "Turn", "River"]
        for street_idx, street in enumerate(streets):
            if state.status is False:  # Hand is over
                break

            # Deal community cards
            if street == "Flop":
                board = [deck.pop(), deck.pop(), deck.pop()]
                for card in board:
                    state.deal_board(card)
                print(f"\n  {BOLD}=== FLOP ==={RESET} {format_cards([str(c) for c in board])}")
            elif street == "Turn":
                board.append(deck.pop())
                state.deal_board(board[-1])
                print(f"\n  {BOLD}=== TURN ==={RESET} {format_cards([str(c) for c in board])}")
            elif street == "River":
                board.append(deck.pop())
                state.deal_board(board[-1])
                print(f"\n  {BOLD}=== RIVER ==={RESET} {format_cards([str(c) for c in board])}")
            elif street == "Preflop":
                print(f"\n  {BOLD}=== PREFLOP ==={RESET}")

            # Betting loop
            board_strs = [str(c) for c in board]  # Convert for player display
            error_occurred = False
            while state.actor_index is not None:
                actor = state.actor_index
                name = self._player_name(actor)

                # Get action
                if actor == 0:
                    # Human's turn
                    action = self._get_human_action(state, hole_cards[0], board_strs)
                    if action.action_type == "quit":
                        quit_requested = True
                        action = ParsedAction("fold")
                else:
                    # Ollama's turn
                    action = self._get_ollama_action(
                        self.opponents[actor - 1],
                        state,
                        hole_cards[actor],
                        board_strs
                    )
                    if action.action_type == "error":
                        print(f"  {RED}{name} failed to respond - skipping hand{RESET}")
                        error_occurred = True
                        break
                    print(f"  {YELLOW}{name} {action}{RESET}")

                # Execute action
                self._execute_action(state, action)

                if quit_requested:
                    break

            if quit_requested or error_occurred:
                break

        # Showdown / determine winner
        self._resolve_hand(state, hole_cards, [str(c) for c in board], stacks_before)

        return not quit_requested

    def _get_human_action(self, state, hole_cards, board) -> ParsedAction:
        """Get action from human player."""
        pot = state.total_pot_amount if hasattr(state, 'total_pot_amount') else 0
        current_bet = max(state.bets) if state.bets else 0
        player_bet = state.bets[0] if state.bets else 0
        to_call = current_bet - player_bet
        stack = state.stacks[0]
        min_raise = state.min_completion_betting_or_raising_to_amount if hasattr(state, 'min_completion_betting_or_raising_to_amount') else current_bet + self.big_blind
        max_raise = stack + player_bet

        return self.human.get_action(hole_cards, board, pot, to_call, stack, min_raise, max_raise)

    def _get_ollama_action(self, player: OllamaPlayer, state, hole_cards, board) -> ParsedAction:
        """Get action from Ollama player."""
        pot = state.total_pot_amount if hasattr(state, 'total_pot_amount') else 0
        current_bet = max(state.bets) if state.bets else 0
        actor = state.actor_index
        player_bet = state.bets[actor] if state.bets else 0
        to_call = current_bet - player_bet
        stack = state.stacks[actor]
        position = self._get_position_name(actor)

        return player.get_action(hole_cards, board, pot, to_call, stack, position, self.num_players)

    def _execute_action(self, state, action: ParsedAction):
        """Execute action on state."""
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

    def _resolve_hand(self, state, hole_cards, board, stacks_before):
        """Resolve hand and update stacks."""
        # Update stacks from state
        if hasattr(state, 'stacks'):
            for i in range(self.num_players):
                self.stacks[i] = state.stacks[i]

        # Determine winner(s) by stack change
        winners = []
        max_gain = 0
        for i in range(self.num_players):
            gain = self.stacks[i] - stacks_before[i]
            if gain > max_gain:
                max_gain = gain
                winners = [i]
            elif gain == max_gain and gain > 0:
                winners.append(i)

        # Clear terminal to hide reasoning traces
        os.system('clear' if os.name != 'nt' else 'cls')

        # Celebration animation
        if winners and max_gain > 0:
            winner_names = [self._player_name(w) for w in winners]
            winner_text = ', '.join(winner_names)
            self._celebration_animation(winner_text, max_gain)

        # Show hand result header
        print()
        print(f"{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}{CYAN}  HAND #{self.hand_num} COMPLETE{RESET}")
        print(f"{BOLD}{'='*60}{RESET}")

        # Highlight winner(s)
        if winners and max_gain > 0:
            winner_names = [self._player_name(w) for w in winners]
            print()
            print(f"  {BOLD}{YELLOW}★ WINNER: {', '.join(winner_names)} (+{max_gain} chips) ★{RESET}")
            print()

        # Show all stacks (public information)
        print(f"  {BOLD}Current Stacks:{RESET}")
        print(f"  {'-'*40}")
        for i in range(self.num_players):
            name = self._player_name(i)
            diff = self.stacks[i] - stacks_before[i]
            if diff > 0:
                diff_str = f"{GREEN}+{diff}{RESET}"
            elif diff < 0:
                diff_str = f"{RED}{diff}{RESET}"
            else:
                diff_str = "0"

            # Highlight winner row
            if i in winners and max_gain > 0:
                print(f"  {YELLOW}► {name}: {self.stacks[i]} chips ({diff_str}){RESET}")
            else:
                print(f"    {name}: {self.stacks[i]} chips ({diff_str})")
        print(f"  {'-'*40}")
        print()

        # Prompt to continue
        try:
            input(f"  {BOLD}Press Enter to start next hand...{RESET}")
        except (EOFError, KeyboardInterrupt):
            pass

    def _celebration_animation(self, winner_name: str, chips_won: int):
        """Display celebration animation for winner."""
        frames = [
            [
                "                                                            ",
                "                    ★  ★  ★  ★  ★                           ",
                "                 ★                 ★                        ",
                "               ★    W I N N E R !    ★                      ",
                "                 ★                 ★                        ",
                "                    ★  ★  ★  ★  ★                           ",
                "                                                            ",
            ],
            [
                "              ✦                          ✦                  ",
                "                   ★  ★  ★  ★  ★                            ",
                "        ✦       ★                 ★       ✦                 ",
                "              ★    W I N N E R !    ★                       ",
                "        ✦       ★                 ★       ✦                 ",
                "                   ★  ★  ★  ★  ★                            ",
                "              ✦                          ✦                  ",
            ],
            [
                "         ✧          ✦          ✦          ✧                 ",
                "    ✦               ★  ★  ★  ★  ★               ✦           ",
                "              ✧  ★                 ★  ✧                     ",
                "         ✦      ★    W I N N E R !    ★      ✦              ",
                "              ✧  ★                 ★  ✧                     ",
                "    ✦               ★  ★  ★  ★  ★               ✦           ",
                "         ✧          ✦          ✦          ✧                 ",
            ],
        ]

        # Animate 2 cycles
        for _ in range(2):
            for frame in frames:
                os.system('clear' if os.name != 'nt' else 'cls')
                print()
                for line in frame:
                    print(f"{YELLOW}{BOLD}{line}{RESET}")
                print()
                print(f"{BOLD}{GREEN}        {winner_name} wins +{chips_won} chips!{RESET}")
                print()
                time.sleep(0.25)

        # Final frame
        os.system('clear' if os.name != 'nt' else 'cls')

    def _show_final_results(self):
        """Show final session results."""
        print()
        print(f"{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}  SESSION COMPLETE - {self.hand_num} hands played{RESET}")
        print(f"{BOLD}{'='*60}{RESET}")

        for i in range(self.num_players):
            name = self._player_name(i)
            diff = self.stacks[i] - self.starting_stack
            color = GREEN if diff > 0 else RED if diff < 0 else ""
            sign = "+" if diff > 0 else ""
            print(f"  {name}: {self.stacks[i]} chips ({color}{sign}{diff}{RESET})")

        print(f"{BOLD}{'='*60}{RESET}")

    def _player_name(self, idx: int) -> str:
        """Get player name."""
        if idx == 0:
            return f"{GREEN}You{RESET}"
        return f"{BLUE}{self.opponents[idx-1].name}{RESET}"

    def _get_position_name(self, idx: int) -> str:
        """Get position name."""
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

    def shutdown(self):
        """Shutdown all Ollama opponents to free memory."""
        print()
        print(f"{BOLD}Shutting down models...{RESET}")
        for opponent in self.opponents:
            opponent.shutdown()
