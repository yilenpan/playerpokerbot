# Player Poker Bot

Interactive No-Limit Texas Hold'em poker game against Ollama LLM models.

## Features

- Play heads-up or multi-way (up to 6 players)
- Support for multiple Ollama models as opponents
- Real PokerKit game engine for accurate poker rules
- **Web UI** with real-time LLM thinking visualization
- Terminal UI with colorful cards and position indicators
- PHH-format action parsing (compatible with poker training data)

## Installation

```bash
# Clone the repo
git clone https://github.com/yilenpan/playerpokerbot.git
cd playerpokerbot

# Install Python dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .

# Install web UI dependencies
cd web
npm install
cd ..
```

## Prerequisites

1. **Ollama** must be installed and running:
   ```bash
   # Install Ollama (if not installed)
   curl -fsSL https://ollama.com/install.sh | sh

   # Start Ollama server
   ollama serve
   ```

2. **Pull the recommended poker model**:
   ```bash
   # Recommended: Fine-tuned poker model from Hugging Face
   ollama pull hf.co/YiPz/Qwen3-4B-pokerbench-sft:latest
   ```

   This model was fine-tuned specifically for poker play and produces better decisions than general-purpose models.

   Alternative models (less optimized for poker):
   ```bash
   ollama pull qwen2.5:7b
   ollama pull llama3:8b
   ```

## Web UI (Recommended)

The web UI provides a visual poker table with real-time streaming of LLM thinking.

### Quick Start

```bash
# Terminal 1: Start the backend server
cd playerpokerbot
python -m server.main

# Terminal 2: Start the web frontend
cd playerpokerbot/web
npm run dev
```

Then open http://localhost:5173 in your browser.

### Features

- Visual poker table with player positions
- Real-time LLM reasoning display (watch the AI think!)
- Position badges (BTN, SB, BB)
- Animated winner celebration
- Stack tracking for all players

### Configuration

When starting a game in the web UI:
1. Select the model: `hf.co/YiPz/Qwen3-4B-pokerbench-sft:latest`
2. Choose number of opponents (1-5)
3. Set starting stack and blinds
4. Click "Start Game"

## Terminal UI

For a quick terminal-based game:

### Basic Play (Heads-Up)

```bash
python scripts/play.py --models "hf.co/YiPz/Qwen3-4B-pokerbench-sft:latest"
```

### Multi-Way Game

```bash
# 3-handed (you + 2 bots)
python scripts/play.py --opponents 2 --models "hf.co/YiPz/Qwen3-4B-pokerbench-sft:latest"

# 6-max (you + 5 bots)
python scripts/play.py --opponents 5 --models "hf.co/YiPz/Qwen3-4B-pokerbench-sft:latest"
```

### Multiple Different Models

```bash
python scripts/play.py -n 3 --models "hf.co/YiPz/Qwen3-4B-pokerbench-sft:latest" "qwen2.5:7b"
```

### Custom Settings

```bash
python scripts/play.py \
    --opponents 2 \
    --models "hf.co/YiPz/Qwen3-4B-pokerbench-sft:latest" \
    --stack 5000 \
    --blinds 25/50 \
    --hands 20
```

## Controls

### Web UI
| Action | How |
|--------|-----|
| Check/Call | Click "Check" or "Call" button |
| Fold | Click "Fold" button |
| Raise | Use slider or enter amount, click "Raise" |
| All-in | Click "All In" button |

### Terminal UI
| Key | Action |
|-----|--------|
| `C` | Check / Call |
| `F` | Fold |
| `R 500` | Raise to 500 |
| `A` | All-in |
| `Q` | Quit |

## Project Structure

```
playerpokerbot/
├── src/                    # Terminal game
│   ├── cards.py            # Card utilities and formatting
│   ├── actions.py          # Action parsing (PHH format)
│   ├── players.py          # Ollama and Human player implementations
│   └── game.py             # PokerKit game engine
├── server/                 # Web backend
│   ├── main.py             # FastAPI server
│   ├── game/               # Game session management
│   ├── models/             # Pydantic models
│   └── streaming/          # LLM streaming client
├── web/                    # React frontend
│   ├── src/
│   │   ├── components/     # UI components
│   │   ├── store/          # Zustand state management
│   │   └── hooks/          # WebSocket hooks
│   └── public/
│       └── suits/          # Card suit images
├── scripts/
│   └── play.py             # Terminal entry point
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

## About the Model

The recommended model [YiPz/Qwen3-4B-pokerbench-sft](https://huggingface.co/YiPz/Qwen3-4B-pokerbench-sft) is a Qwen3-4B model fine-tuned on poker hand histories. It understands:

- Pot odds and implied odds
- Position-based play
- Hand strength evaluation
- Bet sizing strategies

The model outputs actions in a structured format: `<action>f</action>` (fold), `<action>cc</action>` (check/call), or `<action>cbr 500</action>` (raise to 500).

## License

MIT
