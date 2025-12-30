import { create } from 'zustand';
import type {
  GameState,
  AvailableActions,
  ThinkingStream,
  TurnTimerState,
  ParsedAction,
  Card,
  Street,
  PlayerReasoningHistory,
  ReasoningEntry,
} from '../types';

interface HandCompleteInfo {
  winners: number[];
  amounts: number[];
  revealedCards: Record<number, Card[]>;
  isVisible: boolean;
}

interface GameStore {
  // Connection state
  sessionId: string | null;
  isConnected: boolean;
  connectionError: string | null;

  // Game state
  gameState: GameState | null;

  // Thinking streams (per player)
  thinkingStreams: Record<number, ThinkingStream>;

  // Reasoning history (per player) - accumulated across the session
  reasoningHistory: Record<number, PlayerReasoningHistory>;

  // Turn timer
  timer: TurnTimerState | null;

  // Hand complete state
  handComplete: HandCompleteInfo | null;

  // UI state
  isMyTurn: boolean;
  availableActions: AvailableActions | null;
  lastActions: (string | null)[];

  // Actions
  setSessionId: (id: string | null) => void;
  setConnected: (connected: boolean) => void;
  setConnectionError: (error: string | null) => void;

  // Game state actions
  setGameState: (state: GameState) => void;
  updateGameState: (update: {
    hand_number: number;
    street: Street;
    pot: number;
    current_actor: number | null;
    community_cards: Card[];
    player_stacks: number[];
    player_bets: number[];
    last_actions: (string | null)[];
    available_actions?: AvailableActions;
  }) => void;

  // Turn actions
  setMyTurn: (isMyTurn: boolean, actions?: AvailableActions) => void;

  // Thinking stream actions
  startThinking: (playerId: number, playerName: string) => void;
  addThinkingToken: (playerId: number, token: string) => void;
  completeThinking: (playerId: number, action: ParsedAction) => void;
  clearThinking: (playerId: number) => void;
  clearAllThinking: () => void;

  // Reasoning history actions
  toggleReasoningExpanded: (playerId: number) => void;
  clearReasoningHistory: () => void;

  // Timer actions
  startTimer: (playerId: number, totalSeconds: number) => void;
  updateTimer: (remainingSeconds: number) => void;
  expireTimer: () => void;
  clearTimer: () => void;

  // Hand complete actions
  setHandComplete: (winners: number[], amounts: number[], revealedCards: Record<number, Card[]>) => void;
  dismissHandComplete: () => void;

  // Reset
  reset: () => void;
}

const initialState = {
  sessionId: null,
  isConnected: false,
  connectionError: null,
  gameState: null,
  thinkingStreams: {},
  reasoningHistory: {},
  timer: null,
  handComplete: null,
  isMyTurn: false,
  availableActions: null,
  lastActions: [],
};

export const useGameStore = create<GameStore>((set) => ({
  ...initialState,

  setSessionId: (id) => set({ sessionId: id }),
  setConnected: (connected) => set({ isConnected: connected }),
  setConnectionError: (error) => set({ connectionError: error }),

  setGameState: (state) =>
    set({
      gameState: state,
      isMyTurn: state.current_actor === 0,
      availableActions: state.available_actions || null,
    }),

  updateGameState: (update) =>
    set((state) => {
      if (!state.gameState) return state;

      // Update player states
      const updatedPlayers = state.gameState.players.map((player, idx) => ({
        ...player,
        stack: update.player_stacks[idx] ?? player.stack,
        current_bet: update.player_bets[idx] ?? player.current_bet,
        last_action: update.last_actions[idx] ?? player.last_action,
      }));

      return {
        gameState: {
          ...state.gameState,
          hand_number: update.hand_number,
          street: update.street,
          pot: update.pot,
          current_actor: update.current_actor,
          community_cards: update.community_cards,
          players: updatedPlayers,
          available_actions: update.available_actions,
        },
        isMyTurn: update.current_actor === 0,
        availableActions: update.available_actions || null,
        lastActions: update.last_actions,
      };
    }),

  setMyTurn: (isMyTurn, actions) =>
    set({
      isMyTurn,
      availableActions: actions || null,
    }),

  startThinking: (playerId, playerName) =>
    set((state) => {
      // Initialize reasoning history for this player if needed
      const existingHistory = state.reasoningHistory[playerId];
      const updatedHistory = existingHistory || {
        playerId,
        playerName,
        entries: [],
        isExpanded: true,
      };

      return {
        thinkingStreams: {
          ...state.thinkingStreams,
          [playerId]: {
            playerId,
            isActive: true,
            tokens: '',
            startTime: Date.now(),
          },
        },
        reasoningHistory: {
          ...state.reasoningHistory,
          [playerId]: updatedHistory,
        },
      };
    }),

  addThinkingToken: (playerId, token) =>
    set((state) => {
      const stream = state.thinkingStreams[playerId];
      if (!stream) return state;

      return {
        thinkingStreams: {
          ...state.thinkingStreams,
          [playerId]: {
            ...stream,
            tokens: stream.tokens + token,
          },
        },
      };
    }),

  completeThinking: (playerId, action) =>
    set((state) => {
      const stream = state.thinkingStreams[playerId];
      if (!stream) return state;

      // Create a new reasoning entry
      const newEntry: ReasoningEntry = {
        handNumber: state.gameState?.hand_number ?? 0,
        street: state.gameState?.street ?? 'preflop',
        tokens: stream.tokens,
        parsedAction: action,
        timestamp: Date.now(),
      };

      // Append to reasoning history
      const playerHistory = state.reasoningHistory[playerId];
      const updatedHistory = playerHistory
        ? {
            ...playerHistory,
            entries: [...playerHistory.entries, newEntry],
          }
        : {
            playerId,
            playerName: `Player ${playerId}`,
            entries: [newEntry],
            isExpanded: true,
          };

      return {
        thinkingStreams: {
          ...state.thinkingStreams,
          [playerId]: {
            ...stream,
            isActive: false,
            parsedAction: action,
          },
        },
        reasoningHistory: {
          ...state.reasoningHistory,
          [playerId]: updatedHistory,
        },
      };
    }),

  clearThinking: (playerId) =>
    set((state) => {
      const { [playerId]: _, ...rest } = state.thinkingStreams;
      return { thinkingStreams: rest };
    }),

  clearAllThinking: () => set({ thinkingStreams: {} }),

  toggleReasoningExpanded: (playerId) =>
    set((state) => {
      const playerHistory = state.reasoningHistory[playerId];
      if (!playerHistory) return state;

      return {
        reasoningHistory: {
          ...state.reasoningHistory,
          [playerId]: {
            ...playerHistory,
            isExpanded: !playerHistory.isExpanded,
          },
        },
      };
    }),

  clearReasoningHistory: () => set({ reasoningHistory: {} }),

  startTimer: (playerId, totalSeconds) =>
    set({
      timer: {
        playerId,
        totalSeconds,
        remainingSeconds: totalSeconds,
        isExpired: false,
      },
    }),

  updateTimer: (remainingSeconds) =>
    set((state) => {
      if (!state.timer) return state;
      return {
        timer: {
          ...state.timer,
          remainingSeconds,
        },
      };
    }),

  expireTimer: () =>
    set((state) => {
      if (!state.timer) return state;
      return {
        timer: {
          ...state.timer,
          isExpired: true,
          remainingSeconds: 0,
        },
        isMyTurn: false,
      };
    }),

  clearTimer: () => set({ timer: null }),

  setHandComplete: (winners, amounts, revealedCards) =>
    set({
      handComplete: {
        winners,
        amounts,
        revealedCards,
        isVisible: true,
      },
      // Clear reasoning traces when hand completes
      reasoningHistory: {},
      thinkingStreams: {},
    }),

  dismissHandComplete: () =>
    set({
      handComplete: null,
    }),

  reset: () => set(initialState),
}));
