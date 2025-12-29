# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Player Poker Bot is an interactive No-Limit Texas Hold'em poker game where a human plays against Ollama LLM opponents. Built on PokerKit for game rules, with a colorful terminal UI.

- **Language:** Python 3.10+
- **Game Engine:** PokerKit
- **LLM Integration:** Ollama (local HTTP API)

## Build & Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Development install (editable)
pip install -e .

# Run the game
python scripts/play.py --opponents 2 --models "model-name"
# Or after pip install -e .:
play-poker --opponents 2

# Format code
black src/ scripts/

# Lint code
ruff check src/ scripts/

# Run tests
pytest tests/
```

## Architecture

```
scripts/play.py (CLI entry point)
    ↓
src/game.py - PokerGame class (main game loop, hand management)
    ├── src/players.py - OllamaPlayer (LLM API), HumanPlayer (terminal input)
    ├── src/actions.py - ActionParser (regex extraction from LLM responses)
    └── src/cards.py - Card formatting, ANSI colors, hand scoring
```

**Key Flow:** `play.py` → `PokerGame.play_session()` → `_play_hand()` loop → players return `ParsedAction` objects → actions executed via PokerKit state methods (`fold()`, `check_or_call()`, `complete_bet_or_raise_to()`)

## Key Technical Details

- **Player Index 0** is always the human player; opponents are indexed 1+
- **PokerKit Delegation:** All poker rules handled by PokerKit's `NoLimitTexasHoldem.create_state()`. Don't implement custom game logic.
- **Ollama Endpoint:** Default `http://localhost:11434/api/chat`. Requires Ollama running locally with pulled models.
- **Action Parsing:** LLMs output `<action>f|cc|cbr AMOUNT</action>` tags. Parser has regex fallbacks for common keywords.
- **Defensive Imports:** Modules use try/except for both package and direct imports
- **Error Recovery:** Action execution has silent fallback chain (requested action → check/call → fold)

## Code Style

- **Line Length:** 100 characters
- **Formatter:** black
- **Linter:** ruff (E, F, W, I rules)
- **Colors:** ANSI codes defined in `cards.py` for terminal output
