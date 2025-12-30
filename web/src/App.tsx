import { useState, useCallback, useEffect } from 'react';
import { useGameStore } from './store/gameStore';
import { useWebSocket } from './hooks/useWebSocket';
import { GameSetup, PokerTable } from './components/game';
import type { SessionConfigRequest, SessionResponse } from './types';

type GameScreen = 'setup' | 'playing' | 'complete';

function App() {
  const [screen, setScreen] = useState<GameScreen>('setup');
  const [isLoading, setIsLoading] = useState(false);
  const [_error, setError] = useState<string | null>(null);

  const { sessionId, setSessionId, reset } = useGameStore();

  // Create session on the backend
  const handleStartGame = useCallback(async (config: SessionConfigRequest) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        throw new Error('Failed to create session');
      }

      const data: SessionResponse = await response.json();
      setSessionId(data.session_id);
      setScreen('playing');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start game');
    } finally {
      setIsLoading(false);
    }
  }, [setSessionId]);

  // Handle returning to setup
  const handleReturnToSetup = useCallback(() => {
    reset();
    setScreen('setup');
  }, [reset]);

  // Render based on screen
  if (screen === 'setup' || !sessionId) {
    return (
      <GameSetup onStart={handleStartGame} isLoading={isLoading} />
    );
  }

  return (
    <GameWrapper
      sessionId={sessionId}
      onComplete={handleReturnToSetup}
      onError={(msg) => setError(msg)}
    />
  );
}

// Wrapper that handles WebSocket connection
interface GameWrapperProps {
  sessionId: string;
  onComplete: () => void;
  onError: (message: string) => void;
}

function GameWrapper({ sessionId, onComplete, onError }: GameWrapperProps) {
  const { isConnected, gameState } = useGameStore();

  const { sendAction, sendMessage } = useWebSocket({
    sessionId,
    onConnect: () => console.log('Connected to game'),
    onDisconnect: () => console.log('Disconnected from game'),
    onError: (error) => onError(error),
  });

  const handleStartHand = useCallback(() => {
    sendMessage({ type: 'start_hand' });
  }, [sendMessage]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle if we're the current actor
      const { isMyTurn, availableActions } = useGameStore.getState();
      if (!isMyTurn || !availableActions) return;

      switch (e.key.toLowerCase()) {
        case 'f':
          if (availableActions.can_fold) sendAction('fold');
          break;
        case 'c':
          if (availableActions.can_check) sendAction('check');
          else if (availableActions.can_call) sendAction('call');
          break;
        case 'r':
          // For raise, we'd need more UI handling
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [sendAction]);

  if (!isConnected) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="text-gray-400">Connecting to game...</div>
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <PokerTable onAction={sendAction} onStartHand={handleStartHand} />

      {/* Session complete overlay */}
      {gameState && (useGameStore.getState() as any).sessionComplete && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-8 max-w-md text-center">
            <h2 className="text-2xl font-bold text-white mb-4">Game Over!</h2>
            <p className="text-gray-400 mb-6">
              Session complete after {gameState.hand_number} hands
            </p>
            <button
              onClick={onComplete}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg text-white font-semibold"
            >
              Play Again
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
