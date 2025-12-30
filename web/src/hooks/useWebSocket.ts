import { useEffect, useRef, useCallback } from 'react';
import { useGameStore } from '../store/gameStore';
import type { ServerEvent, ClientMessage } from '../types';

interface UseWebSocketOptions {
  sessionId: string;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: string) => void;
}

export function useWebSocket({
  sessionId,
  onConnect,
  onDisconnect,
  onError,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const hasConnectedRef = useRef(false);

  // Store callbacks in refs to avoid dependency issues
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const onErrorRef = useRef(onError);

  // Update refs when callbacks change
  onConnectRef.current = onConnect;
  onDisconnectRef.current = onDisconnect;
  onErrorRef.current = onError;

  const sendMessage = useCallback((message: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket not connected');
    }
  }, []);

  const sendAction = useCallback(
    (actionType: string, amount?: number) => {
      sendMessage({
        type: 'player_action',
        action_type: actionType,
        amount,
      });
      useGameStore.getState().setMyTurn(false);
      useGameStore.getState().clearTimer();
    },
    [sendMessage]
  );

  // Single connection effect - only depends on sessionId
  useEffect(() => {
    // Prevent duplicate connections
    if (hasConnectedRef.current) {
      console.log('Already connected, skipping');
      return;
    }

    hasConnectedRef.current = true;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/${sessionId}`;

    console.log('Creating WebSocket connection:', url);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket opened');
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data: ServerEvent = JSON.parse(event.data);
        const store = useGameStore.getState();

        switch (data.type) {
          case 'connection_ack':
            console.log('Connected to session:', data.session_id);
            store.setConnected(true);
            store.setConnectionError(null);
            onConnectRef.current?.();
            break;

          case 'game_state':
            store.setGameState(data.state);
            store.clearAllThinking();
            break;

          case 'game_state_update':
            store.updateGameState({
              hand_number: data.hand_number,
              street: data.street,
              pot: data.pot,
              current_actor: data.current_actor,
              community_cards: data.community_cards,
              player_stacks: data.player_stacks,
              player_bets: data.player_bets,
              last_actions: data.last_actions,
              available_actions: data.available_actions,
            });
            break;

          case 'your_turn':
            store.setMyTurn(true, data.available_actions);
            break;

          case 'thinking_start':
            store.startThinking(data.player_id, data.player_name);
            break;

          case 'thinking_token':
            store.addThinkingToken(data.player_id, data.token);
            break;

          case 'thinking_complete':
            store.completeThinking(data.player_id, data.action);
            break;

          case 'timer_start':
            store.startTimer(data.player_id, data.total_seconds);
            break;

          case 'timer_tick':
            store.updateTimer(data.remaining_seconds);
            break;

          case 'timer_expired':
            store.expireTimer();
            break;

          case 'hand_complete':
            store.clearTimer();
            store.setHandComplete(data.winners, data.amounts, data.revealed_cards);
            console.log('Hand complete:', data);
            break;

          case 'session_complete':
            console.log('Session complete:', data);
            break;

          case 'error':
            console.error('Server error:', data.message);
            store.setConnectionError(data.message);
            onErrorRef.current?.(data.message);
            break;

          case 'pong':
            break;

          default:
            console.log('Unknown event:', data);
        }
      } catch (e) {
        console.error('Failed to parse message:', e);
      }
    };

    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      useGameStore.getState().setConnected(false);
      onDisconnectRef.current?.();
      wsRef.current = null;
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      useGameStore.getState().setConnectionError('Connection error');
    };

    // Cleanup on unmount only
    return () => {
      console.log('Cleaning up WebSocket');
      hasConnectedRef.current = false;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [sessionId]); // Only sessionId as dependency

  return {
    sendMessage,
    sendAction,
  };
}
