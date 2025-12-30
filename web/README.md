# Poker Bot Web UI

React + TypeScript frontend for the Player Poker Bot.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Open http://localhost:5173

## Prerequisites

The backend server must be running:

```bash
# From the project root
cd ..
python -m server.main
```

And Ollama must have the poker model:

```bash
ollama pull hf.co/YiPz/Qwen3-4B-pokerbench-sft:latest
```

## Build for Production

```bash
npm run build
```

Output is in `dist/`.

## Tech Stack

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Framer Motion (animations)
- Zustand (state management)
- WebSocket (real-time updates)

## Features

- Visual poker table with dynamic player positioning
- Real-time LLM reasoning stream display
- Position badges (BTN, SB, BB)
- Thinking animation with color cycling
- Winner celebration with confetti
- Responsive card rendering with suit images
