# Browser-Based Poker Bot with Real-Time LLM Thinking Streams

**Version:** 1.0.0  
**Status:** Draft  
**Last Updated:** 2025-12-29  
**Author:** Technical Specification  

---

## Table of Contents

1. [Overview](#1-overview)
2. [Goals and Non-Goals](#2-goals-and-non-goals)
3. [Success Metrics](#3-success-metrics)
4. [User Stories](#4-user-stories)
5. [System Architecture](#5-system-architecture)
6. [Frontend Specification](#6-frontend-specification)
7. [Backend Specification](#7-backend-specification)
8. [Real-Time Communication Protocol](#8-real-time-communication-protocol)
9. [API Specification](#9-api-specification)
10. [Data Models](#10-data-models)
11. [State Management](#11-state-management)
12. [Streaming Token Implementation](#12-streaming-token-implementation)
13. [UI/UX Design Specification](#13-uiux-design-specification)
14. [Security Considerations](#14-security-considerations)
15. [Error Handling](#15-error-handling)
16. [Testing Strategy](#16-testing-strategy)
17. [Migration & Rollout Plan](#17-migration--rollout-plan)
18. [Technology Stack Recommendations](#18-technology-stack-recommendations)
19. [Open Questions](#19-open-questions)
20. [Appendices](#20-appendices)

---

## 1. Overview

### 1.1 Executive Summary

This specification describes the conversion of the existing terminal-based "Player Poker Bot" into a browser-playable web application. The key differentiating feature is real-time streaming of LLM "thinking" tokens, allowing players to watch AI opponents reason through their decisions in real-time.

### 1.2 Current System Analysis

The existing system is a Python-based No-Limit Texas Hold'em poker game with the following characteristics:

| Component | Current Implementation |
|-----------|----------------------|
| **Game Engine** | PokerKit library handles all poker rules |
| **Player Types** | `HumanPlayer` (terminal input), `OllamaPlayer` (LLM via HTTP) |
| **LLM Communication** | Synchronous HTTP POST to Ollama API (`stream: false`) |
| **UI** | Terminal with ANSI color codes |
| **Action Format** | `<action>f\|cc\|cbr AMOUNT</action>` tags |
| **State Management** | Single-threaded, blocking execution |

### 1.3 Target System Vision

A modern web application where:
- The poker table is rendered in the browser with a polished visual design
- Multiple LLM opponents sit around the table with visible "thinking bubbles"
- As each LLM generates tokens, they stream character-by-character into the thinking bubble
- The human player interacts via clickable buttons and input fields
- The game state synchronizes in real-time between server and client

---

## 2. Goals and Non-Goals

### 2.1 Goals

| ID | Goal | Priority |
|----|------|----------|
| G1 | Browser-playable poker game with equivalent functionality to terminal version | P0 |
| G2 | Real-time streaming of LLM thinking tokens visible to the player | P0 |
| G3 | Visually polished poker table UI suitable for demonstration | P0 |
| G4 | Support for 2-6 players (1 human + 1-5 LLM opponents) | P1 |
| G5 | Preserve existing PokerKit integration for game rules | P1 |
| G6 | Maintain compatibility with Ollama local API | P1 |
| G7 | Responsive design for desktop and tablet viewports | P2 |
| G8 | Optional trace logging for LLM reasoning analysis | P2 |

### 2.2 Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Multiplayer with multiple human players | Complexity; single-human focus for MVP |
| NG2 | Mobile-first responsive design | Desktop is primary use case for watching LLM thinking |
| NG3 | Persistent user accounts or game history | Stateless session-based play for MVP |
| NG4 | Cloud deployment or Ollama proxy | Local development focus; user runs own Ollama |
| NG5 | Hand history replay or analysis tools | Out of scope for initial release |
| NG6 | Sound effects or animations beyond basic transitions | Polish deferred to future iteration |

---

## 3. Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Token Streaming Latency | <100ms from Ollama generation to browser display | Performance testing with timestamps |
| Game State Sync Accuracy | 100% consistency between server and client | Automated integration tests |
| Browser Compatibility | Chrome, Firefox, Safari (latest 2 versions) | Manual testing matrix |
| Complete Hand Playability | Full hand from deal to showdown without errors | End-to-end test suite |
| UI Responsiveness | Actions complete within 200ms (excluding LLM time) | Performance profiling |

---

## 4. User Stories

### 4.1 Core User Stories

**US1: Start a New Game**
> As a player, I want to configure and start a new poker game in my browser so that I can play against LLM opponents.

Acceptance Criteria:
- Player can select number of opponents (1-5)
- Player can select/configure Ollama models for each opponent
- Player can set starting stack and blind levels
- Game starts with proper seating arrangement

**US2: View the Poker Table**
> As a player, I want to see a visual poker table with my cards, opponent positions, and community cards so that I can understand the game state at a glance.

Acceptance Criteria:
- My hole cards are visible (face up)
- Opponent hole cards are hidden (face down) until showdown
- Community cards appear in the center
- Current pot amount is visible
- Each player's chip stack is displayed
- Dealer button, blinds, and positions are indicated

**US3: Watch LLM Thinking in Real-Time**
> As a player, I want to see each LLM opponent's thinking process stream in real-time so that I can understand their decision-making and find it engaging.

Acceptance Criteria:
- Each opponent has a "thinking bubble" near their seat
- When it is an LLM's turn, their bubble activates and shows "Thinking..."
- Tokens stream in character-by-character as they are generated
- The final action is highlighted when decision is made
- Thinking bubble can be scrolled if content overflows

**US4: Take My Turn**
> As a player, I want to take actions (fold, check, call, raise) when it is my turn using intuitive controls.

Acceptance Criteria:
- Action buttons appear only when it is my turn
- Available actions are clearly enabled/disabled based on game state
- Raise slider or input allows precise bet sizing
- Keyboard shortcuts available (F=fold, C=check/call, R=raise)
- Actions are confirmed with visual feedback

**US5: Complete a Hand**
> As a player, I want to play a complete hand through showdown and see results.

Acceptance Criteria:
- All betting rounds progress correctly
- Showdown reveals winning hand(s)
- Pot is awarded to winner(s)
- Hand summary is displayed
- Next hand can be started or session ended

---

## 5. System Architecture

### 5.1 High-Level Architecture Diagram

```
+------------------------------------------------------------------+
|                           BROWSER                                 |
|  +------------------------------------------------------------+  |
|  |                    React Frontend                           |  |
|  |  +------------------+  +------------------+  +------------+ |  |
|  |  |   Poker Table    |  |  Thinking Boxes  |  |  Controls  | |  |
|  |  |   Component      |  |  (per opponent)  |  |  Panel     | |  |
|  |  +------------------+  +------------------+  +------------+ |  |
|  |                              |                              |  |
|  |  +--------------------------------------------------+      |  |
|  |  |            State Management (Zustand)             |      |  |
|  |  +--------------------------------------------------+      |  |
|  |                              |                              |  |
|  |  +--------------------------------------------------+      |  |
|  |  |         WebSocket Client (real-time events)       |      |  |
|  |  +--------------------------------------------------+      |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                                  |
                                  | WebSocket (wss://)
                                  |
+------------------------------------------------------------------+
|                         PYTHON BACKEND                            |
|  +------------------------------------------------------------+  |
|  |                   FastAPI Application                       |  |
|  |  +------------------+  +------------------+  +------------+ |  |
|  |  |  WebSocket       |  |   Game Engine    |  |   Ollama   | |  |
|  |  |  Manager         |  |   (PokerKit)     |  |   Client   | |  |
|  |  +------------------+  +------------------+  +------------+ |  |
|  |           |                     |                  |        |  |
|  |  +--------------------------------------------------+      |  |
|  |  |              Game Session Manager                 |      |  |
|  |  +--------------------------------------------------+      |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                                  |
                                  | HTTP (streaming)
                                  |
+------------------------------------------------------------------+
|                       OLLAMA (LOCAL)                              |
|  +------------------------------------------------------------+  |
|  |  http://localhost:11434/api/chat (stream: true)             |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

### 5.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **React Frontend** | Render poker UI, manage local UI state, handle user input |
| **WebSocket Client** | Maintain persistent connection, receive game events, send player actions |
| **Zustand Store** | Client-side state management for game state, UI state, and thinking streams |
| **FastAPI Backend** | HTTP/WebSocket server, game session management, orchestration |
| **WebSocket Manager** | Handle multiple client connections, broadcast game events |
| **Game Engine** | PokerKit wrapper, poker rules, hand evaluation |
| **Ollama Client** | Streaming HTTP client for LLM inference |
| **Game Session Manager** | Track active games, player turns, game lifecycle |

### 5.3 Data Flow Diagram

```
+----------+     +-----------+     +-------------+     +--------+
|  Browser |<--->| WebSocket |<--->| Game Engine |<--->| Ollama |
+----------+     +-----------+     +-------------+     +--------+
     ^                 ^                  ^                 |
     |                 |                  |                 |
     | 1. User clicks  | 2. WS: player_   | 3. Process     | 4. HTTP POST
     |    "Call"       |    action        |    action      |    (stream)
     |                 |                  |                 |
     | 8. UI updates   | 7. WS: game_     | 6. Get LLM     | 5. Stream
     |    with new     |    state_update  |    decision    |    tokens
     |    state        |    + thinking_   |                 |
     |                 |    tokens        |                 |
     +                 +                  +                 +
```

---

## 6. Frontend Specification

### 6.1 Technology Stack

| Technology | Purpose | Rationale |
|------------|---------|-----------|
| **React 18+** | UI framework | Component model, hooks, ecosystem |
| **TypeScript** | Type safety | Catch errors early, better DX |
| **Zustand** | State management | Lightweight, simple API, good for real-time |
| **Tailwind CSS** | Styling | Rapid UI development, consistent design |
| **Framer Motion** | Animations | Smooth card/chip animations |
| **Vite** | Build tool | Fast development, modern bundling |

### 6.2 Component Hierarchy

```
App
+-- GameSetup                    # Initial configuration screen
|   +-- OpponentSelector         # Number of opponents
|   +-- ModelConfigurator        # Model selection per opponent
|   +-- GameSettings             # Stack, blinds, etc.
|
+-- PokerTable                   # Main game view
|   +-- TableFelt                # Green felt background
|   +-- CommunityCards           # Center card display
|   +-- PotDisplay               # Current pot amount
|   |
|   +-- PlayerSeat (x6 max)      # Individual player positions
|   |   +-- Avatar               # Player icon/identifier
|   |   +-- ChipStack            # Stack amount display
|   |   +-- HoleCards            # 2 cards (visible/hidden)
|   |   +-- PositionBadge        # BTN, SB, BB, etc.
|   |   +-- ActionIndicator      # Last action taken
|   |   +-- ThinkingBubble       # LLM thinking stream (opponents only)
|   |       +-- StreamingText    # Character-by-character display
|   |       +-- ActionHighlight  # Parsed action emphasis
|   |
|   +-- ActionPanel              # Human player controls
|   |   +-- FoldButton
|   |   +-- CheckCallButton
|   |   +-- RaiseControls
|   |   |   +-- RaiseSlider
|   |   |   +-- RaiseInput
|   |   |   +-- QuickBetButtons  # 1/2 pot, pot, all-in
|   |   +-- AllInButton
|   |
|   +-- HandInfo                 # Current hand metadata
|       +-- HandNumber
|       +-- Street               # Preflop, Flop, Turn, River
|       +-- Timer                # Turn timer (optional)
|
+-- GameOverlay                  # Modal overlays
    +-- HandResult               # Winner announcement
    +-- SessionSummary           # End of session stats
    +-- ErrorModal               # Connection/game errors
```

### 6.3 Key Component Specifications

#### 6.3.1 ThinkingBubble Component

```typescript
interface ThinkingBubbleProps {
  playerId: number;
  isThinking: boolean;
  tokens: string;           // Accumulated thinking text
  parsedAction: ParsedAction | null;  // Extracted action when complete
  maxHeight: number;        // Max height before scroll (px)
}

interface ThinkingBubbleState {
  isExpanded: boolean;      // User expanded the bubble
  scrollPosition: number;   // Current scroll position
  autoScroll: boolean;      // Auto-scroll to bottom
}
```

Visual Behavior:
- **Inactive**: Collapsed, subtle border, grayed out
- **Thinking**: Pulsing border, "Thinking..." placeholder, then streaming text
- **Complete**: Action tag highlighted in green, rest of text visible
- **Overflow**: Scrollable with fade gradient at top/bottom edges

#### 6.3.2 PlayerSeat Component

```typescript
interface PlayerSeatProps {
  player: Player;
  position: TablePosition;     // 0-5 around the table
  isCurrentActor: boolean;
  isDealer: boolean;
  isSB: boolean;
  isBB: boolean;
  holeCards: [Card, Card] | null;
  showCards: boolean;          // Face up or face down
  currentBet: number;
  lastAction: string | null;
}
```

Position Layout (6-max):
```
         [Seat 3]
    [Seat 2]    [Seat 4]
         
    [Community Cards]
    
    [Seat 1]    [Seat 5]
         [Seat 0 - Human]
```

### 6.4 Frontend State Schema

```typescript
interface GameState {
  // Session info
  sessionId: string;
  handNumber: number;
  
  // Players
  players: Player[];
  humanPlayerIndex: number;  // Always 0
  
  // Positions
  buttonPosition: number;
  currentActorIndex: number | null;
  
  // Cards
  communityCards: Card[];
  humanHoleCards: [Card, Card] | null;
  
  // Betting
  pot: number;
  currentBet: number;
  playerBets: number[];
  playerStacks: number[];
  
  // Street
  street: 'preflop' | 'flop' | 'turn' | 'river' | 'showdown';
  
  // Actions
  availableActions: AvailableActions;
  lastActions: (string | null)[];
  
  // LLM Thinking
  thinkingStreams: Map<number, ThinkingStream>;
}

interface ThinkingStream {
  playerId: number;
  isActive: boolean;
  tokens: string;
  parsedAction: ParsedAction | null;
  startTime: number;
}

interface AvailableActions {
  canFold: boolean;
  canCheck: boolean;
  canCall: boolean;
  callAmount: number;
  canRaise: boolean;
  minRaise: number;
  maxRaise: number;
}

interface Player {
  id: number;
  name: string;
  type: 'human' | 'llm';
  model?: string;        // For LLM players
  isActive: boolean;     // Still in hand
  isBusted: boolean;     // Out of chips
}
```

---

## 7. Backend Specification

### 7.1 Technology Stack

| Technology | Purpose | Rationale |
|------------|---------|-----------|
| **Python 3.10+** | Runtime | Match existing codebase |
| **FastAPI** | Web framework | Async, WebSocket support, automatic OpenAPI |
| **uvicorn** | ASGI server | Production-ready, async |
| **PokerKit** | Game engine | Already integrated, proven |
| **httpx** | HTTP client | Async, streaming support for Ollama |
| **Pydantic** | Data validation | Type safety, serialization |

### 7.2 Module Structure

```
src/
+-- __init__.py
+-- main.py                 # FastAPI app entry point
+-- config.py               # Configuration management
|
+-- api/
|   +-- __init__.py
|   +-- routes.py           # HTTP endpoints
|   +-- websocket.py        # WebSocket handlers
|
+-- game/
|   +-- __init__.py
|   +-- engine.py           # PokerKit wrapper (refactored from game.py)
|   +-- session.py          # Game session management
|   +-- actions.py          # Action parsing (existing)
|
+-- players/
|   +-- __init__.py
|   +-- base.py             # Player base class
|   +-- human.py            # Human player (WebSocket-based)
|   +-- ollama.py           # Ollama player (streaming)
|
+-- streaming/
|   +-- __init__.py
|   +-- ollama_client.py    # Streaming Ollama client
|   +-- token_broadcaster.py # Broadcast tokens to WebSocket
|
+-- models/
    +-- __init__.py
    +-- game.py             # Game state models
    +-- events.py           # WebSocket event models
    +-- api.py              # API request/response models
```

### 7.3 Key Backend Classes

#### 7.3.1 GameSession

```python
class GameSession:
    """Manages a single poker game session."""
    
    def __init__(
        self,
        session_id: str,
        human_player: HumanWebPlayer,
        llm_players: List[OllamaStreamingPlayer],
        config: GameConfig,
    ):
        self.session_id = session_id
        self.players = [human_player] + llm_players
        self.config = config
        self.engine = PokerEngine(config)
        self.websocket_manager = WebSocketManager()
        self.current_hand: Optional[HandState] = None
        
    async def start_hand(self) -> None:
        """Initialize and start a new hand."""
        
    async def process_action(self, player_id: int, action: ParsedAction) -> None:
        """Process a player action and advance game state."""
        
    async def get_llm_action(self, player_id: int) -> ParsedAction:
        """Get action from LLM player with streaming."""
        
    async def broadcast_state(self) -> None:
        """Broadcast current game state to all connected clients."""
        
    async def broadcast_thinking_token(self, player_id: int, token: str) -> None:
        """Broadcast a single thinking token to clients."""
```

#### 7.3.2 OllamaStreamingClient

```python
class OllamaStreamingClient:
    """Async streaming client for Ollama API."""
    
    def __init__(
        self,
        endpoint: str = "http://localhost:11434",
        timeout: float = 120.0,
    ):
        self.endpoint = endpoint
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def generate_streaming(
        self,
        model: str,
        messages: List[Dict],
        on_token: Callable[[str], Awaitable[None]],
        temperature: float = 0.6,
    ) -> str:
        """
        Generate response with streaming tokens.
        
        Args:
            model: Ollama model name
            messages: Chat messages
            on_token: Async callback for each token
            temperature: Sampling temperature
            
        Returns:
            Complete response text
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,  # KEY CHANGE: Enable streaming
            "options": {"temperature": temperature}
        }
        
        full_response = ""
        async with self.client.stream(
            "POST",
            f"{self.endpoint}/api/chat",
            json=payload,
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    if token:
                        full_response += token
                        await on_token(token)
        
        return full_response
```

---

## 8. Real-Time Communication Protocol

### 8.1 WebSocket Connection Lifecycle

```
Client                                    Server
   |                                         |
   |  1. WS Connect /ws/{session_id}         |
   |---------------------------------------->|
   |                                         |
   |  2. connection_ack {player_id}          |
   |<----------------------------------------|
   |                                         |
   |  3. game_state (full state)             |
   |<----------------------------------------|
   |                                         |
   |          ... game loop ...              |
   |                                         |
   |  N. player_action {action}              |
   |---------------------------------------->|
   |                                         |
   |  N+1. game_state_update                 |
   |<----------------------------------------|
   |                                         |
   |  N+2. thinking_start {player_id}        |
   |<----------------------------------------|
   |                                         |
   |  N+3. thinking_token {token}  (repeated)|
   |<----------------------------------------|
   |                                         |
   |  N+4. thinking_complete {action}        |
   |<----------------------------------------|
   |                                         |
   |  N+5. game_state_update                 |
   |<----------------------------------------|
```

### 8.2 WebSocket Event Types

#### 8.2.1 Server-to-Client Events

| Event Type | Payload | Description |
|------------|---------|-------------|
| `connection_ack` | `{player_id, session_id}` | Connection confirmed |
| `game_state` | Full `GameState` | Complete state snapshot |
| `game_state_update` | Partial `GameState` | Incremental update |
| `your_turn` | `{available_actions}` | Prompt human for action |
| `thinking_start` | `{player_id, player_name}` | LLM started thinking |
| `thinking_token` | `{player_id, token}` | Single token from LLM |
| `thinking_complete` | `{player_id, action, full_text}` | LLM finished |
| `hand_complete` | `{winners, amounts, revealed_cards}` | Hand finished |
| `session_complete` | `{final_stacks, summary}` | Session ended |
| `error` | `{code, message}` | Error notification |

#### 8.2.2 Client-to-Server Events

| Event Type | Payload | Description |
|------------|---------|-------------|
| `player_action` | `{action_type, amount?}` | Human player's action |
| `start_hand` | `{}` | Request to start next hand |
| `end_session` | `{}` | Request to end session |
| `ping` | `{}` | Keep-alive |

### 8.3 Event Schemas (Pydantic)

```python
from pydantic import BaseModel
from typing import Literal, Optional, List

class ThinkingTokenEvent(BaseModel):
    type: Literal["thinking_token"] = "thinking_token"
    player_id: int
    token: str
    timestamp: float

class ThinkingCompleteEvent(BaseModel):
    type: Literal["thinking_complete"] = "thinking_complete"
    player_id: int
    action: ParsedAction
    full_text: str
    duration_ms: int

class PlayerActionEvent(BaseModel):
    type: Literal["player_action"] = "player_action"
    action_type: Literal["fold", "check", "call", "raise", "all_in"]
    amount: Optional[int] = None

class GameStateUpdateEvent(BaseModel):
    type: Literal["game_state_update"] = "game_state_update"
    hand_number: int
    street: str
    pot: int
    current_actor: Optional[int]
    community_cards: List[str]
    player_stacks: List[int]
    player_bets: List[int]
    last_actions: List[Optional[str]]
    available_actions: Optional[AvailableActions] = None
```

---

## 9. API Specification

### 9.1 REST Endpoints

#### POST /api/sessions

Create a new game session.

**Request:**
```json
{
  "opponents": [
    {"name": "Ollama-1", "model": "qwen3:latest"},
    {"name": "Ollama-2", "model": "llama3:latest"}
  ],
  "config": {
    "starting_stack": 10000,
    "small_blind": 50,
    "big_blind": 100,
    "num_hands": 10
  }
}
```

**Response:**
```json
{
  "session_id": "abc123",
  "websocket_url": "/ws/abc123",
  "players": [
    {"id": 0, "name": "You", "type": "human"},
    {"id": 1, "name": "Ollama-1", "type": "llm", "model": "qwen3:latest"},
    {"id": 2, "name": "Ollama-2", "type": "llm", "model": "llama3:latest"}
  ]
}
```

#### GET /api/sessions/{session_id}

Get current session state.

**Response:**
```json
{
  "session_id": "abc123",
  "status": "in_progress",
  "hand_number": 3,
  "player_stacks": [10500, 9200, 10300]
}
```

#### DELETE /api/sessions/{session_id}

End and cleanup a session.

#### GET /api/models

List available Ollama models.

**Response:**
```json
{
  "models": [
    {"name": "qwen3:latest", "size": "4B"},
    {"name": "llama3:latest", "size": "8B"}
  ]
}
```

#### GET /api/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "ollama_connected": true,
  "active_sessions": 2
}
```

---

## 10. Data Models

### 10.1 Core Game Models

```python
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum

class Street(Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"

class ActionType(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"
    ALL_IN = "all_in"

@dataclass
class Card:
    rank: str  # 2-9, T, J, Q, K, A
    suit: str  # c, d, h, s
    
    def to_dict(self) -> dict:
        return {"rank": self.rank, "suit": self.suit}
    
    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

@dataclass
class ParsedAction:
    action_type: ActionType
    amount: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type.value,
            "amount": self.amount
        }

@dataclass
class PlayerState:
    id: int
    name: str
    player_type: str  # "human" or "llm"
    stack: int
    current_bet: int
    hole_cards: Optional[Tuple[Card, Card]]
    is_active: bool  # Still in this hand
    is_busted: bool  # Out of tournament
    last_action: Optional[str]

@dataclass
class HandState:
    hand_number: int
    street: Street
    pot: int
    community_cards: List[Card]
    button_position: int
    current_actor: Optional[int]
    players: List[PlayerState]
    min_raise: int
    max_raise: int

@dataclass
class GameConfig:
    starting_stack: int = 10000
    small_blind: int = 50
    big_blind: int = 100
    num_hands: int = 10
```

### 10.2 Database Schema (Optional - for persistent sessions)

[DECISION NEEDED: Is session persistence required for MVP?]

If persistent sessions are needed:

```sql
-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active',
    config JSONB,
    current_hand_number INT DEFAULT 0
);

-- Players table
CREATE TABLE session_players (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    player_index INT,
    name VARCHAR(100),
    player_type VARCHAR(20),
    model VARCHAR(200),
    current_stack INT
);

-- Hand history (optional)
CREATE TABLE hand_history (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    hand_number INT,
    actions JSONB,
    result JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 11. State Management

### 11.1 Server-Side State

The server is the source of truth for all game state. State is held in memory within `GameSession` objects.

```python
class GameSessionManager:
    """Manages all active game sessions."""
    
    def __init__(self):
        self._sessions: Dict[str, GameSession] = {}
        self._lock = asyncio.Lock()
    
    async def create_session(self, config: SessionConfig) -> GameSession:
        async with self._lock:
            session_id = str(uuid.uuid4())[:8]
            session = GameSession(session_id, config)
            self._sessions[session_id] = session
            return session
    
    async def get_session(self, session_id: str) -> Optional[GameSession]:
        return self._sessions.get(session_id)
    
    async def remove_session(self, session_id: str) -> None:
        async with self._lock:
            if session_id in self._sessions:
                await self._sessions[session_id].cleanup()
                del self._sessions[session_id]
```

### 11.2 Client-Side State (Zustand)

```typescript
import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

interface GameStore {
  // Connection state
  sessionId: string | null;
  isConnected: boolean;
  connectionError: string | null;
  
  // Game state (from server)
  gameState: GameState | null;
  
  // Thinking streams (accumulated locally)
  thinkingStreams: Record<number, ThinkingStream>;
  
  // UI state
  isMyTurn: boolean;
  availableActions: AvailableActions | null;
  
  // Actions
  connect: (sessionId: string) => Promise<void>;
  disconnect: () => void;
  sendAction: (action: PlayerAction) => void;
  
  // Internal handlers
  handleGameStateUpdate: (update: Partial<GameState>) => void;
  handleThinkingToken: (playerId: number, token: string) => void;
  handleThinkingComplete: (playerId: number, action: ParsedAction) => void;
}

export const useGameStore = create<GameStore>()(
  immer((set, get) => ({
    sessionId: null,
    isConnected: false,
    connectionError: null,
    gameState: null,
    thinkingStreams: {},
    isMyTurn: false,
    availableActions: null,
    
    handleThinkingToken: (playerId, token) => {
      set((state) => {
        if (!state.thinkingStreams[playerId]) {
          state.thinkingStreams[playerId] = {
            playerId,
            isActive: true,
            tokens: '',
            parsedAction: null,
            startTime: Date.now(),
          };
        }
        state.thinkingStreams[playerId].tokens += token;
      });
    },
    
    handleThinkingComplete: (playerId, action) => {
      set((state) => {
        if (state.thinkingStreams[playerId]) {
          state.thinkingStreams[playerId].isActive = false;
          state.thinkingStreams[playerId].parsedAction = action;
        }
      });
    },
    
    // ... other implementations
  }))
);
```

### 11.3 State Synchronization Protocol

1. **Initial Load**: Client receives full `game_state` on WebSocket connect
2. **Incremental Updates**: Server sends `game_state_update` with only changed fields
3. **Optimistic Updates**: None for MVP (all state changes are server-authoritative)
4. **Reconnection**: Client requests full state resync on reconnect

---

## 12. Streaming Token Implementation

### 12.1 Ollama Streaming Integration

The key change from the existing implementation is switching from `"stream": false` to `"stream": true` in the Ollama API call.

**Current Implementation (players.py line 115):**
```python
payload = {
    "model": self.model,
    "messages": [...],
    "stream": False,  # Blocks until complete
    ...
}
```

**New Streaming Implementation:**
```python
async def stream_ollama_response(
    self,
    prompt: str,
    on_token: Callable[[str], Awaitable[None]],
) -> str:
    """Stream response from Ollama, calling on_token for each piece."""
    
    payload = {
        "model": self.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "stream": True,  # Enable streaming
        "options": {
            "temperature": self.temperature,
            "num_predict": self.max_tokens
        }
    }
    
    full_response = ""
    
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{self.endpoint}/api/chat",
            json=payload,
            timeout=120.0,
        ) as response:
            async for line in response.aiter_lines():
                if not line:
                    continue
                    
                try:
                    data = json.loads(line)
                    
                    # Handle regular content
                    content = data.get("message", {}).get("content", "")
                    if content:
                        full_response += content
                        await on_token(content)
                    
                    # Handle thinking content (for thinking models)
                    thinking = data.get("message", {}).get("thinking", "")
                    if thinking:
                        full_response += thinking
                        await on_token(thinking)
                    
                    # Check if done
                    if data.get("done", False):
                        break
                        
                except json.JSONDecodeError:
                    continue
    
    return full_response
```

### 12.2 Token Broadcasting Flow

```
+-------------------------------------------------------------+
|                    OllamaStreamingPlayer                     |
|                                                             |
|  async def get_action_streaming(...):                       |
|      async def broadcast_token(token):                      |
|          await self.session.broadcast_thinking_token(       |
|              self.player_id, token                          |
|          )                                                  |
|                                                             |
|      response = await self.client.stream_ollama_response(   |
|          prompt, on_token=broadcast_token                   |
|      )                                                      |
|      return self.parser.parse(response)                     |
+-------------------------------------------------------------+
                              |
                              | For each token
                              v
+-------------------------------------------------------------+
|                      GameSession                            |
|                                                             |
|  async def broadcast_thinking_token(player_id, token):      |
|      event = ThinkingTokenEvent(                            |
|          player_id=player_id,                               |
|          token=token,                                       |
|          timestamp=time.time()                              |
|      )                                                      |
|      await self.websocket_manager.broadcast(event)          |
+-------------------------------------------------------------+
                              |
                              | WebSocket broadcast
                              v
+-------------------------------------------------------------+
|                   WebSocket Manager                         |
|                                                             |
|  async def broadcast(event):                                |
|      message = event.model_dump_json()                      |
|      for connection in self.active_connections:             |
|          await connection.send_text(message)                |
+-------------------------------------------------------------+
                              |
                              | To each client
                              v
+-------------------------------------------------------------+
|                   Browser (React)                           |
|                                                             |
|  websocket.onmessage = (event) => {                         |
|      const data = JSON.parse(event.data);                   |
|      if (data.type === 'thinking_token') {                  |
|          store.handleThinkingToken(                         |
|              data.player_id, data.token                     |
|          );                                                 |
|      }                                                      |
|  }                                                          |
|                                                             |
|  // ThinkingBubble re-renders with new token                |
+-------------------------------------------------------------+
```

### 12.3 Token Batching (Performance Optimization)

To avoid overwhelming the WebSocket with individual character updates, tokens can be batched:

```python
class TokenBatcher:
    """Batch tokens before broadcasting to reduce WebSocket messages."""
    
    def __init__(
        self,
        broadcast_fn: Callable[[str], Awaitable[None]],
        batch_size: int = 5,          # Characters per batch
        max_delay_ms: float = 50.0,   # Max delay before flush
    ):
        self.broadcast_fn = broadcast_fn
        self.batch_size = batch_size
        self.max_delay_ms = max_delay_ms
        self._buffer = ""
        self._last_flush = time.time()
    
    async def add_token(self, token: str) -> None:
        self._buffer += token
        
        should_flush = (
            len(self._buffer) >= self.batch_size or
            (time.time() - self._last_flush) * 1000 >= self.max_delay_ms
        )
        
        if should_flush:
            await self.flush()
    
    async def flush(self) -> None:
        if self._buffer:
            await self.broadcast_fn(self._buffer)
            self._buffer = ""
            self._last_flush = time.time()
```

---

## 13. UI/UX Design Specification

### 13.1 Visual Design Principles

| Principle | Application |
|-----------|-------------|
| **Clarity** | Game state must be immediately understandable |
| **Focus** | Current actor and action options are visually prominent |
| **Engagement** | Thinking streams create anticipation and entertainment |
| **Accessibility** | Sufficient contrast, readable fonts, color not sole indicator |

### 13.2 Color Palette

| Element | Color | Hex | Usage |
|---------|-------|-----|-------|
| Table Felt | Deep Green | `#1a472a` | Background |
| Table Edge | Walnut Brown | `#5c4033` | Table border |
| Card White | Off White | `#f5f5f0` | Card background |
| Card Red | Crimson | `#dc143c` | Hearts, diamonds |
| Card Black | Rich Black | `#1a1a1a` | Clubs, spades |
| Chip Gold | Gold | `#ffd700` | Pot, stack highlights |
| Active Player | Bright Blue | `#3b82f6` | Current actor indicator |
| Thinking Bubble | Soft Purple | `#8b5cf6` | LLM thinking box |
| Action Button | Emerald | `#10b981` | Positive actions |
| Fold Button | Rose | `#f43f5e` | Fold action |
| Human Player | Teal | `#14b8a6` | Human seat highlight |

### 13.3 Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Player Names | Inter | 16px | 600 |
| Stack Amounts | JetBrains Mono | 14px | 500 |
| Pot Amount | JetBrains Mono | 20px | 700 |
| Thinking Text | JetBrains Mono | 12px | 400 |
| Action Buttons | Inter | 14px | 600 |
| Card Ranks | Custom or Roboto | 24px | 700 |

### 13.4 Layout Specifications

#### 13.4.1 Poker Table (Desktop - 1280px+)

```
+--------------------------------------------------------------------------+
|  Header: Hand #3 | Blinds: 50/100 | Pot: 450                              |
+--------------------------------------------------------------------------+
|                                                                          |
|                        +---------------------+                           |
|     +---------+        |     Seat 3          |        +---------+        |
|     | Seat 2  |        |  [Think Box]        |        | Seat 4  |        |
|     | [Box]   |        |  [  ] [  ]  5,200   |        |  [Box]  |        |
|     | [  ][  ]|        +---------------------+        | [  ][  ]|        |
|     | 4,800   |                                       | 6,100   |        |
|     +---------+                                       +---------+        |
|                                                                          |
|                    +-----------------------------+                       |
|                    |   AS  KH  QD  JC  10S      |                       |
|                    |        Community Cards      |                       |
|                    |          POT: 450           |                       |
|                    +-----------------------------+                       |
|                                                                          |
|     +---------+                                       +---------+        |
|     | Seat 1  |                                       | Seat 5  |        |
|     | [Box]   |                                       |  [Box]  |        |
|     | [  ][  ]|                                       | [  ][  ]|        |
|     | 5,500   |                                       | 4,200   |        |
|     +---------+                                       +---------+        |
|                                                                          |
|                   +-------------------------------+                      |
|                   |          YOU (Seat 0)         |                      |
|                   |        +----+  +----+         |                      |
|                   |        | AS |  | KH |         |                      |
|                   |        +----+  +----+         |                      |
|                   |           10,000              |                      |
|                   +-------------------------------+                      |
|                                                                          |
+--------------------------------------------------------------------------+
|  +---------+  +-------------+  +-------------------------+  +---------+ |
|  |  FOLD   |  | CALL 100   |  | RAISE [====|====] 500   |  | ALL-IN  | |
|  +---------+  +-------------+  +-------------------------+  +---------+ |
+--------------------------------------------------------------------------+
```

#### 13.4.2 Thinking Bubble Detail

```
+-----------------------------------------+
| Ollama-1 is thinking...                 |
+-----------------------------------------+
|                                         |  ^
| I have Kh Qd in the cutoff. The pot    |  |
| is 450 with 100 to call. My hand has   |  | Scrollable
| good broadway potential. Given my       |  | area
| position and stack depth of 52bb...    |  |
|                                         |  v
| +-------------------------------------+ |
| | <action>cbr 300</action>            | |  <-- Highlighted
| +-------------------------------------+ |      when detected
+-----------------------------------------+
     \
      \ Pointer to player seat
```

### 13.5 Card Design

```
+--------------+     +--------------+
| A            |     | ############ |
|              |     | ############ |
|      S       |     | ############ |
|              |     | ############ |
|            A |     | ############ |
+--------------+     +--------------+
   Face Up            Face Down
```

Card dimensions: 60px x 84px (ratio 5:7)

### 13.6 Responsive Breakpoints

| Breakpoint | Layout Changes |
|------------|---------------|
| 1280px+ | Full desktop layout as shown |
| 1024px-1279px | Compact thinking boxes, smaller cards |
| 768px-1023px | Thinking boxes as modals, simplified table |
| <768px | [ASSUMPTION: Not a primary target for MVP] |

---

## 14. Security Considerations

### 14.1 Threat Model

| Threat | Mitigation |
|--------|------------|
| **WebSocket injection** | Validate all incoming messages against Pydantic schemas |
| **Session hijacking** | Generate cryptographically random session IDs |
| **DoS via many sessions** | Limit concurrent sessions per IP (default: 3) |
| **Malicious Ollama responses** | Sanitize LLM output before display (escape HTML) |
| **Resource exhaustion** | Timeout LLM requests, limit token count |

### 14.2 Input Validation

```python
from pydantic import BaseModel, validator, conint

class PlayerActionRequest(BaseModel):
    action_type: Literal["fold", "check", "call", "raise", "all_in"]
    amount: Optional[conint(ge=0, le=1_000_000)] = None
    
    @validator('amount')
    def amount_required_for_raise(cls, v, values):
        if values.get('action_type') == 'raise' and v is None:
            raise ValueError('amount required for raise action')
        return v
```

### 14.3 Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/sessions")
@limiter.limit("5/minute")
async def create_session(request: Request, config: SessionConfig):
    ...
```

---

## 15. Error Handling

### 15.1 Error Categories

| Category | HTTP Status | WebSocket Event | User Message |
|----------|-------------|-----------------|--------------|
| Validation Error | 400 | `error` | "Invalid action: [details]" |
| Session Not Found | 404 | - | "Game session not found" |
| Ollama Unavailable | 503 | `error` | "AI service unavailable" |
| Ollama Timeout | 504 | `error` | "AI took too long to respond" |
| Internal Error | 500 | `error` | "Something went wrong" |

### 15.2 Ollama Error Recovery

```python
async def get_llm_action_with_retry(
    self,
    player: OllamaStreamingPlayer,
    max_retries: int = 2,
) -> ParsedAction:
    """Get LLM action with retry logic."""
    
    for attempt in range(max_retries + 1):
        try:
            return await asyncio.wait_for(
                player.get_action_streaming(...),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            if attempt < max_retries:
                await self.broadcast_error(
                    f"{player.name} is taking a while, retrying..."
                )
                continue
            # Final fallback: default action
            return ParsedAction(ActionType.CALL if can_check else ActionType.FOLD)
        except httpx.ConnectError:
            await self.broadcast_error("Lost connection to AI service")
            return ParsedAction(ActionType.FOLD)
```

### 15.3 Client-Side Error Handling

```typescript
// WebSocket reconnection logic
const useWebSocketConnection = (sessionId: string) => {
  const [retryCount, setRetryCount] = useState(0);
  const maxRetries = 3;
  
  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);
      
      ws.onclose = (event) => {
        if (!event.wasClean && retryCount < maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, retryCount), 10000);
          setTimeout(() => {
            setRetryCount(c => c + 1);
            connect();
          }, delay);
        }
      };
      
      ws.onerror = () => {
        store.setConnectionError("Connection lost. Reconnecting...");
      };
    };
    
    connect();
  }, [sessionId, retryCount]);
};
```

---

## 16. Testing Strategy

### 16.1 Testing Pyramid

```
                    +-------------+
                    |    E2E      |  <-- Playwright: Full user flows
                   -+-------------+-
                  +-----------------+
                  |  Integration    |  <-- pytest: WebSocket + Game logic
                 -+-----------------+-
                +---------------------+
                |        Unit         |  <-- pytest: Components, functions
               -+---------------------+-
```

### 16.2 Unit Tests

**Backend (pytest):**
```python
# test_action_parser.py
def test_parse_action_tag():
    parser = ActionParser()
    result = parser.parse("<action>cbr 500</action>", can_check=False, stack=1000)
    assert result.action_type == ActionType.RAISE
    assert result.amount == 500

# test_game_engine.py
def test_hand_progression():
    engine = PokerEngine(GameConfig())
    state = engine.create_hand(stacks=[1000, 1000])
    
    engine.execute_action(state, ParsedAction(ActionType.CALL))
    engine.execute_action(state, ParsedAction(ActionType.CHECK))
    
    assert state.street == Street.FLOP

# test_token_batcher.py
@pytest.mark.asyncio
async def test_batching():
    received = []
    async def on_batch(text):
        received.append(text)
    
    batcher = TokenBatcher(on_batch, batch_size=3)
    for char in "Hello":
        await batcher.add_token(char)
    await batcher.flush()
    
    assert "".join(received) == "Hello"
```

**Frontend (Vitest + React Testing Library):**
```typescript
// ThinkingBubble.test.tsx
describe('ThinkingBubble', () => {
  it('streams tokens character by character', async () => {
    const { rerender, getByTestId } = render(
      <ThinkingBubble playerId={1} isThinking={true} tokens="" />
    );
    
    rerender(
      <ThinkingBubble playerId={1} isThinking={true} tokens="Thinking" />
    );
    
    expect(getByTestId('thinking-text')).toHaveTextContent('Thinking');
  });
  
  it('highlights action tag when complete', () => {
    const { getByTestId } = render(
      <ThinkingBubble 
        playerId={1} 
        isThinking={false} 
        tokens="I should call. <action>cc</action>"
        parsedAction={{ action_type: 'call' }}
      />
    );
    
    expect(getByTestId('action-highlight')).toHaveClass('bg-green-200');
  });
});
```

### 16.3 Integration Tests

```python
# test_websocket_flow.py
@pytest.mark.asyncio
async def test_full_hand_websocket_flow():
    """Test complete hand through WebSocket."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create session
        response = await client.post("/api/sessions", json={
            "opponents": [{"name": "Test-AI", "model": "test-model"}],
            "config": {"starting_stack": 1000}
        })
        session_id = response.json()["session_id"]
        
        # Connect WebSocket
        async with websockets.connect(f"ws://test/ws/{session_id}") as ws:
            # Receive initial state
            state = json.loads(await ws.recv())
            assert state["type"] == "game_state"
            
            # Wait for our turn
            while True:
                msg = json.loads(await ws.recv())
                if msg["type"] == "your_turn":
                    break
            
            # Send action
            await ws.send(json.dumps({
                "type": "player_action",
                "action_type": "call"
            }))
            
            # Verify state update
            update = json.loads(await ws.recv())
            assert update["type"] == "game_state_update"
```

### 16.4 E2E Tests (Playwright)

```typescript
// e2e/poker-game.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Poker Game', () => {
  test('should play a complete hand', async ({ page }) => {
    await page.goto('/');
    
    // Configure game
    await page.selectOption('[data-testid="opponent-count"]', '2');
    await page.click('[data-testid="start-game"]');
    
    // Wait for game to load
    await expect(page.locator('[data-testid="poker-table"]')).toBeVisible();
    
    // Wait for our turn
    await expect(page.locator('[data-testid="action-panel"]')).toBeVisible();
    
    // Take action
    await page.click('[data-testid="call-button"]');
    
    // Verify action was recorded
    await expect(page.locator('[data-testid="last-action-0"]'))
      .toContainText('Call');
  });
  
  test('should stream LLM thinking tokens', async ({ page }) => {
    await page.goto('/');
    await page.click('[data-testid="start-game"]');
    
    // Wait for LLM turn
    const thinkingBubble = page.locator('[data-testid="thinking-bubble-1"]');
    await expect(thinkingBubble).toContainText('thinking', { timeout: 10000 });
    
    // Verify text is streaming (content should grow)
    const initialLength = await thinkingBubble.textContent()
      .then(t => t?.length || 0);
    
    await page.waitForTimeout(500);
    
    const laterLength = await thinkingBubble.textContent()
      .then(t => t?.length || 0);
    
    expect(laterLength).toBeGreaterThan(initialLength);
  });
});
```

---

## 17. Migration & Rollout Plan

### 17.1 Development Phases

| Phase | Duration | Deliverables |
|-------|----------|-------------|
| **Phase 1: Backend Foundation** | 1 week | FastAPI server, WebSocket manager, PokerKit integration |
| **Phase 2: Streaming Integration** | 1 week | Ollama streaming client, token broadcasting |
| **Phase 3: Frontend Core** | 1.5 weeks | React app, poker table UI, state management |
| **Phase 4: Thinking UI** | 1 week | Thinking bubbles, streaming display |
| **Phase 5: Polish & Testing** | 1 week | E2E tests, bug fixes, UX improvements |

### 17.2 Phase 1 Detail: Backend Foundation

Tasks:
1. Set up FastAPI project structure
2. Create Pydantic models for game state and events
3. Implement WebSocket connection manager
4. Refactor `PokerGame` class to be async-compatible
5. Implement REST endpoints (sessions, health)
6. Add basic test suite

Acceptance Criteria:
- WebSocket connection can be established
- Game state can be serialized and sent to client
- Health endpoint returns Ollama connection status

### 17.3 Phase 2 Detail: Streaming Integration

Tasks:
1. Implement `OllamaStreamingClient` with async streaming
2. Create `TokenBatcher` for performance
3. Integrate streaming into game session flow
4. Implement `thinking_start`, `thinking_token`, `thinking_complete` events
5. Add timeout and retry logic

Acceptance Criteria:
- Tokens stream to connected clients in <100ms
- LLM timeout falls back gracefully
- Trace logging works as before

### 17.4 Phase 3 Detail: Frontend Core

Tasks:
1. Set up Vite + React + TypeScript project
2. Implement Zustand store with game state
3. Create WebSocket client hook
4. Build poker table layout components
5. Implement card rendering (face up/down)
6. Build action panel with buttons and raise slider

Acceptance Criteria:
- Poker table renders correctly
- Human can take actions via UI
- State syncs with server

### 17.5 Phase 4 Detail: Thinking UI

Tasks:
1. Design and implement `ThinkingBubble` component
2. Add streaming text display with cursor
3. Implement action tag highlighting
4. Add scroll behavior for long content
5. Style and animate bubble appearance/disappearance

Acceptance Criteria:
- Tokens appear character-by-character
- Action tag is visually highlighted
- Bubble scrolls to show latest content

### 17.6 Phase 5 Detail: Polish & Testing

Tasks:
1. Write E2E tests with Playwright
2. Fix visual bugs across browsers
3. Add error state UI components
4. Implement keyboard shortcuts
5. Performance optimization
6. Documentation

Acceptance Criteria:
- All tests pass
- Game is playable in Chrome, Firefox, Safari
- No critical bugs

---

## 18. Technology Stack Recommendations

### 18.1 Recommended Stack

| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| **Backend Runtime** | Python | 3.10+ | Match existing codebase |
| **Backend Framework** | FastAPI | 0.100+ | Async, WebSocket, auto-docs |
| **ASGI Server** | uvicorn | 0.23+ | Production-ready |
| **HTTP Client** | httpx | 0.24+ | Async streaming support |
| **Game Engine** | PokerKit | 0.5+ | Already integrated |
| **Frontend Runtime** | Node.js | 20 LTS | Build tooling |
| **Frontend Framework** | React | 18+ | Hooks, Suspense |
| **Type Safety** | TypeScript | 5+ | Catch errors early |
| **State Management** | Zustand | 4+ | Simple, performant |
| **Styling** | Tailwind CSS | 3+ | Rapid development |
| **Animations** | Framer Motion | 10+ | Smooth transitions |
| **Build Tool** | Vite | 5+ | Fast, modern |
| **Testing (BE)** | pytest | 7+ | Standard Python testing |
| **Testing (FE)** | Vitest | 1+ | Fast, Vite-native |
| **E2E Testing** | Playwright | 1.40+ | Cross-browser |

### 18.2 Alternative Considerations

**Backend Alternatives:**

| Alternative | Pros | Cons | Recommendation |
|-------------|------|------|----------------|
| **Node.js + Express** | Single language with frontend | Lose PokerKit, rewrite game logic | Not recommended |
| **Go + Gorilla** | Performance | Lose PokerKit, rewrite | Not recommended |
| **Django Channels** | Mature WebSocket | Heavier than FastAPI | Viable but overkill |

**Frontend Alternatives:**

| Alternative | Pros | Cons | Recommendation |
|-------------|------|------|----------------|
| **Vue 3** | Simpler reactivity | Smaller ecosystem | Viable |
| **Svelte** | Less boilerplate | Smaller ecosystem | Viable |
| **HTMX + Alpine** | Server-driven | Complex streaming UI | Not recommended |
| **Vanilla JS** | No build step | More code, harder state | Not recommended |

### 18.3 Dependencies (requirements.txt additions)

```
# Existing
pokerkit>=0.5.0
requests>=2.28.0

# New for web server
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
websockets>=11.0
httpx>=0.24.0
pydantic>=2.0.0
python-multipart>=0.0.6  # For form data if needed

# Development
pytest>=7.0.0
pytest-asyncio>=0.21.0
black>=23.0.0
ruff>=0.0.280
```

### 18.4 Frontend Dependencies (package.json)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "zustand": "^4.4.0",
    "framer-motion": "^10.16.0",
    "clsx": "^2.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.0.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0",
    "vitest": "^1.0.0",
    "@testing-library/react": "^14.0.0",
    "@playwright/test": "^1.40.0"
  }
}
```

---

## 19. Open Questions

| ID | Question | Impact | Proposed Resolution |
|----|----------|--------|---------------------|
| OQ1 | Should session state persist across server restarts? | Architecture complexity | **No for MVP** - sessions are ephemeral |
| OQ2 | Support for remote Ollama instances (not localhost)? | Configuration, security | **Yes** - configurable endpoint, document security implications |
| OQ3 | Multiple browser tabs/sessions for same game? | Sync complexity | **No** - one tab per session, reject duplicate connections |
| OQ4 | Hand history export feature? | Scope creep | **Defer** - add in future iteration |
| OQ5 | Should thinking text persist between hands? | UX decision | **No** - clear on new hand for focus |
| OQ6 | Minimum viable viewport size? | Responsive design effort | **1024px width** - focus on desktop |
| OQ7 | Auto-play when human is away/timed out? | UX, implementation | **Fold** - with warning toast |

---

## 20. Appendices

### Appendix A: Ollama Streaming Response Format

When `"stream": true` is set, Ollama returns newline-delimited JSON:

```json
{"model":"qwen3:latest","created_at":"2025-01-15T10:30:00Z","message":{"role":"assistant","content":"I"},"done":false}
{"model":"qwen3:latest","created_at":"2025-01-15T10:30:00Z","message":{"role":"assistant","content":" have"},"done":false}
{"model":"qwen3:latest","created_at":"2025-01-15T10:30:00Z","message":{"role":"assistant","content":" A"},"done":false}
...
{"model":"qwen3:latest","created_at":"2025-01-15T10:30:01Z","message":{"role":"assistant","content":""},"done":true,"total_duration":1234567890}
```

For thinking models, there is an additional `thinking` field:
```json
{"message":{"role":"assistant","content":"","thinking":"Let me analyze"}}
```

### Appendix B: WebSocket Message Examples

**Server to Client - Game State:**
```json
{
  "type": "game_state",
  "hand_number": 3,
  "street": "flop",
  "pot": 450,
  "community_cards": [
    {"rank": "A", "suit": "s"},
    {"rank": "K", "suit": "h"},
    {"rank": "Q", "suit": "d"}
  ],
  "players": [
    {"id": 0, "name": "You", "stack": 9550, "current_bet": 100, "is_active": true},
    {"id": 1, "name": "Ollama-1", "stack": 10000, "current_bet": 100, "is_active": true}
  ],
  "current_actor": 0,
  "button_position": 1
}
```

**Server to Client - Thinking Token:**
```json
{
  "type": "thinking_token",
  "player_id": 1,
  "token": "Given my position",
  "timestamp": 1705312200.123
}
```

**Client to Server - Player Action:**
```json
{
  "type": "player_action",
  "action_type": "raise",
  "amount": 300
}
```

### Appendix C: Existing Code Reference

Key existing patterns to preserve:

1. **Action Format**: `<action>f|cc|cbr AMOUNT</action>` - keep this LLM output format
2. **Player Index**: Human is always index 0
3. **PokerKit Delegation**: All rules handled by PokerKit, not custom logic
4. **Error Recovery Chain**: Action execution falls back (requested -> check/call -> fold)

Files to refactor:
- `src/players.py`: Extract `OllamaPlayer` to support async streaming
- `src/game.py`: Make `PokerGame` async-compatible, add state serialization
- `src/actions.py`: Keep as-is, works for both terminal and web

### Appendix D: File Structure (Final)

```
player_poker_bot/
+-- src/                          # Existing + refactored
|   +-- __init__.py
|   +-- cards.py                  # Keep (remove ANSI for web)
|   +-- actions.py                # Keep
|   +-- players.py                # Refactor (add streaming)
|   +-- game.py                   # Refactor (add async)
|
+-- server/                       # New backend
|   +-- __init__.py
|   +-- main.py                   # FastAPI app
|   +-- config.py
|   +-- api/
|   |   +-- routes.py
|   |   +-- websocket.py
|   +-- game/
|   |   +-- engine.py
|   |   +-- session.py
|   +-- streaming/
|   |   +-- ollama_client.py
|   |   +-- token_broadcaster.py
|   +-- models/
|       +-- game.py
|       +-- events.py
|       +-- api.py
|
+-- web/                          # New frontend
|   +-- index.html
|   +-- package.json
|   +-- tsconfig.json
|   +-- vite.config.ts
|   +-- tailwind.config.js
|   +-- src/
|   |   +-- main.tsx
|   |   +-- App.tsx
|   |   +-- store/
|   |   |   +-- gameStore.ts
|   |   +-- hooks/
|   |   |   +-- useWebSocket.ts
|   |   +-- components/
|   |   |   +-- PokerTable.tsx
|   |   |   +-- PlayerSeat.tsx
|   |   |   +-- ThinkingBubble.tsx
|   |   |   +-- ActionPanel.tsx
|   |   |   +-- Card.tsx
|   |   |   +-- ...
|   |   +-- types/
|   |       +-- index.ts
|   +-- tests/
|       +-- ...
|
+-- scripts/
|   +-- play.py                   # Keep for terminal version
|
+-- tests/                        # Backend tests
|   +-- test_engine.py
|   +-- test_streaming.py
|   +-- test_websocket.py
|
+-- e2e/                          # E2E tests
|   +-- poker-game.spec.ts
|
+-- docs/
|   +-- browser-poker-spec.md    # This document
|
+-- requirements.txt              # Updated
+-- pyproject.toml
+-- README.md
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-29 | Specification | Initial draft |

---

*End of Specification*
