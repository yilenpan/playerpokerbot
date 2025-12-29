#!/usr/bin/env python3
"""
Interactive poker game: Human vs Multiple Ollama LLMs.

Play No-Limit Texas Hold'em against one or more Ollama models.

Usage:
    # Play against 1 Ollama model (heads-up)
    python scripts/play.py

    # Play against 2 Ollama models (3-handed)
    python scripts/play.py --opponents 2

    # Specify different models for each opponent
    python scripts/play.py --models "qwen3:latest" "llama3:latest"

    # Custom stack size
    python scripts/play.py --stack 5000 --blinds 25/50

    # Dump LLM reasoning traces to a file
    python scripts/play.py --trace-file traces.jsonl
"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cards import RED, GREEN, RESET
from players import OllamaPlayer, HumanPlayer
from game import PokerGame


def parse_args():
    parser = argparse.ArgumentParser(description="Play poker against Ollama models")
    parser.add_argument("--opponents", "-n", type=int, default=1,
                       help="Number of Ollama opponents (default: 1)")
    parser.add_argument("--models", "-m", nargs="+",
                       default=["hf.co/unsloth/Qwen3-4B-Thinking-2507-GGUF:latest"],
                       help="Ollama model(s) to play against")
    parser.add_argument("--endpoint", default="http://localhost:11434",
                       help="Ollama endpoint")
    parser.add_argument("--stack", type=int, default=10000,
                       help="Starting stack (default: 10000)")
    parser.add_argument("--blinds", default="50/100",
                       help="Blinds as SB/BB (default: 50/100)")
    parser.add_argument("--hands", type=int, default=10,
                       help="Number of hands to play (default: 10)")
    parser.add_argument("--trace-file", "-t", type=Path,
                       help="File to dump LLM reasoning traces (JSONL format)")
    return parser.parse_args()


def main():
    args = parse_args()

    # Parse blinds
    try:
        sb, bb = map(int, args.blinds.split("/"))
    except ValueError:
        sb, bb = 50, 100

    # Create opponents
    opponents = []
    for i in range(args.opponents):
        model = args.models[i % len(args.models)]
        name = f"Ollama-{i+1}" if args.opponents > 1 else "Ollama"
        player = OllamaPlayer(name, model, args.endpoint, trace_file=args.trace_file)

        if not player.check_connection():
            print(f"{RED}Error: Cannot connect to Ollama or model '{model}' not found{RESET}")
            print(f"Make sure Ollama is running: ollama serve")
            print(f"And model is available: ollama pull {model}")
            return 1

        opponents.append(player)
        print(f"{GREEN}✓ {name} ready ({model}){RESET}")

    # Create game
    human = HumanPlayer()
    game = PokerGame(human, opponents, args.stack, sb, bb)

    # Play
    game.play_session(args.hands)

    return 0


if __name__ == "__main__":
    sys.exit(main())
