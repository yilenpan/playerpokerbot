// Game state types matching backend models

export type Street = 'preflop' | 'flop' | 'turn' | 'river' | 'showdown';

export type ActionType = 'fold' | 'check' | 'call' | 'raise' | 'all_in';

export interface Card {
  rank: string; // 2-9, T, J, Q, K, A
  suit: string; // c, d, h, s
}

export interface ParsedAction {
  action_type: ActionType;
  amount?: number;
}

export interface PlayerState {
  id: number;
  name: string;
  player_type: 'human' | 'llm';
  model?: string;
  stack: number;
  current_bet: number;
  hole_cards?: Card[];
  is_active: boolean;
  is_busted: boolean;
  last_action?: string;
}

export interface AvailableActions {
  can_fold: boolean;
  can_check: boolean;
  can_call: boolean;
  call_amount: number;
  can_raise: boolean;
  min_raise: number;
  max_raise: number;
}

export interface GameState {
  session_id: string;
  hand_number: number;
  street: Street;
  pot: number;
  community_cards: Card[];
  button_position: number;
  current_actor: number | null;
  players: PlayerState[];
  available_actions?: AvailableActions;
}

export interface ThinkingStream {
  playerId: number;
  isActive: boolean;
  tokens: string;
  parsedAction?: ParsedAction;
  startTime: number;
}

export interface ReasoningEntry {
  handNumber: number;
  street: Street;
  tokens: string;
  parsedAction?: ParsedAction;
  timestamp: number;
}

export interface PlayerReasoningHistory {
  playerId: number;
  playerName: string;
  entries: ReasoningEntry[];
  isExpanded: boolean;
}

export interface TurnTimerState {
  playerId: number;
  totalSeconds: number;
  remainingSeconds: number;
  isExpired: boolean;
}

// WebSocket event types

export interface ConnectionAckEvent {
  type: 'connection_ack';
  session_id: string;
  player_id: number;
}

export interface GameStateEvent {
  type: 'game_state';
  state: GameState;
}

export interface GameStateUpdateEvent {
  type: 'game_state_update';
  hand_number: number;
  street: Street;
  pot: number;
  current_actor: number | null;
  community_cards: Card[];
  player_stacks: number[];
  player_bets: number[];
  last_actions: (string | null)[];
  available_actions?: AvailableActions;
}

export interface YourTurnEvent {
  type: 'your_turn';
  available_actions: AvailableActions;
}

export interface ThinkingStartEvent {
  type: 'thinking_start';
  player_id: number;
  player_name: string;
}

export interface ThinkingTokenEvent {
  type: 'thinking_token';
  player_id: number;
  token: string;
  timestamp: number;
}

export interface ThinkingCompleteEvent {
  type: 'thinking_complete';
  player_id: number;
  action: ParsedAction;
  full_text: string;
  duration_ms: number;
}

export interface TimerStartEvent {
  type: 'timer_start';
  player_id: number;
  total_seconds: number;
  timestamp: number;
}

export interface TimerTickEvent {
  type: 'timer_tick';
  player_id: number;
  remaining_seconds: number;
}

export interface TimerExpiredEvent {
  type: 'timer_expired';
  player_id: number;
  action_taken: string;
}

export interface HandCompleteEvent {
  type: 'hand_complete';
  winners: number[];
  amounts: number[];
  revealed_cards: Record<number, Card[]>;
}

export interface SessionCompleteEvent {
  type: 'session_complete';
  final_stacks: number[];
  hands_played: number;
}

export interface ErrorEvent {
  type: 'error';
  code: string;
  message: string;
}

export type ServerEvent =
  | ConnectionAckEvent
  | GameStateEvent
  | GameStateUpdateEvent
  | YourTurnEvent
  | ThinkingStartEvent
  | ThinkingTokenEvent
  | ThinkingCompleteEvent
  | TimerStartEvent
  | TimerTickEvent
  | TimerExpiredEvent
  | HandCompleteEvent
  | SessionCompleteEvent
  | ErrorEvent
  | { type: 'pong' };

// Client to server messages

export interface PlayerActionMessage {
  type: 'player_action';
  action_type: string;
  amount?: number;
}

export interface StartHandMessage {
  type: 'start_hand';
}

export interface EndSessionMessage {
  type: 'end_session';
}

export interface PingMessage {
  type: 'ping';
}

export type ClientMessage =
  | PlayerActionMessage
  | StartHandMessage
  | EndSessionMessage
  | PingMessage;

// API types

export interface OpponentConfig {
  name: string;
  model: string;
  temperature?: number;
}

export interface SessionConfigRequest {
  opponents: OpponentConfig[];
  starting_stack?: number;
  small_blind?: number;
  big_blind?: number;
  num_hands?: number;
  turn_timeout_seconds?: number;
}

export interface PlayerInfo {
  id: number;
  name: string;
  player_type: 'human' | 'llm';
  model?: string;
}

export interface SessionResponse {
  session_id: string;
  websocket_url: string;
  players: PlayerInfo[];
}

export interface ModelInfo {
  name: string;
  size?: string;
}

export interface ModelsResponse {
  models: ModelInfo[];
}

export interface HealthResponse {
  status: string;
  ollama_connected: boolean;
  active_sessions: number;
}
