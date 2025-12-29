# Player Poker Bot

Interactive No-Limit Texas Hold'em poker game against Ollama LLM models.

## Features

- Play heads-up or multi-way (up to 6 players)
- Support for multiple Ollama models as opponents
- Real PokerKit game engine for accurate poker rules
- Terminal UI with colorful cards and position indicators
- PHH-format action parsing (compatible with poker training data)

## Installation

```bash
# Clone the repo
git clone https://github.com/yilenpan/player_poker_bot.git
cd player_poker_bot

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

## Prerequisites

1. **Ollama** must be installed and running:
   ```bash
   # Install Ollama (if not installed)
   curl -fsSL https://ollama.com/install.sh | sh

   # Start Ollama server
   ollama serve
   ```

2. **Pull a model** to play against:
   ```bash
   # Recommended: Qwen3 thinking model
   ollama pull hf.co/unsloth/Qwen3-4B-Thinking-2507-GGUF:latest

   # Or any other model
   ollama pull llama3:8b
   ollama pull qwen2.5:7b
   ```

## Usage

### Basic Play (Heads-Up)

```bash
python scripts/play.py
```

### Multi-Way Game

```bash
# 3-handed (you + 2 bots)
python scripts/play.py --opponents 2

# 6-max (you + 5 bots)
python scripts/play.py --opponents 5
```

### Multiple Different Models

```bash
python scripts/play.py -n 3 --models "qwen2.5:7b" "llama3:8b" "mistral:7b"
```

### Custom Settings

```bash
python scripts/play.py \
    --opponents 2 \
    --stack 5000 \
    --blinds 25/50 \
    --hands 20
```

## Controls

| Key | Action |
|-----|--------|
| `C` | Check / Call |
| `F` | Fold |
| `R 500` | Raise to 500 |
| `A` | All-in |
| `Q` | Quit |

## Project Structure

```
player_poker_bot/
├── src/
│   ├── __init__.py
│   ├── cards.py      # Card utilities and formatting
│   ├── actions.py    # Action parsing (PHH format)
│   ├── players.py    # Ollama and Human player implementations
│   └── game.py       # PokerKit game engine
├── scripts/
│   └── play.py       # Main entry point
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

## License

MIT
