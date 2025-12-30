import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import type { ModelInfo, OpponentConfig, SessionConfigRequest } from '../../types';

interface GameSetupProps {
  onStart: (config: SessionConfigRequest) => void;
  isLoading?: boolean;
}

export function GameSetup({ onStart, isLoading }: GameSetupProps) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loadingModels, setLoadingModels] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Game config
  const [numOpponents, setNumOpponents] = useState(1);
  const [selectedModel, setSelectedModel] = useState('');
  const [startingStack, setStartingStack] = useState(10000);
  const [smallBlind, setSmallBlind] = useState(50);
  const [bigBlind, setBigBlind] = useState(100);
  const [numHands, setNumHands] = useState(10);

  // Fetch available models
  useEffect(() => {
    async function fetchModels() {
      try {
        const response = await fetch('/api/models');
        if (!response.ok) throw new Error('Failed to fetch models');
        const data = await response.json();
        setModels(data.models || []);
        if (data.models?.length > 0) {
          setSelectedModel(data.models[0].name);
        }
      } catch (e) {
        setError('Failed to connect to server. Is the backend running?');
      } finally {
        setLoadingModels(false);
      }
    }
    fetchModels();
  }, []);

  const handleStart = () => {
    const opponents: OpponentConfig[] = Array.from({ length: numOpponents }, (_, i) => ({
      name: `AI-${i + 1}`,
      model: selectedModel,
    }));

    onStart({
      opponents,
      starting_stack: startingStack,
      small_blind: smallBlind,
      big_blind: bigBlind,
      num_hands: numHands,
      turn_timeout_seconds: 30,
    });
  };

  if (loadingModels) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="text-red-400">{error}</div>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-white"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md bg-gray-800/90 rounded-2xl p-8 border border-gray-700 shadow-2xl"
      >
        <h1 className="text-3xl font-bold text-center mb-2 text-white">Poker Bot</h1>
        <p className="text-gray-400 text-center mb-8">Play against AI opponents</p>

        <div className="space-y-6">
          {/* Number of opponents */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Number of Opponents
            </label>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  onClick={() => setNumOpponents(n)}
                  className={clsx(
                    'flex-1 py-2 rounded-lg font-semibold transition-colors',
                    numOpponents === n
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  )}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>

          {/* Model selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">AI Model</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {models.map((model) => (
                <option key={model.name} value={model.name}>
                  {model.name} {model.size && `(${model.size})`}
                </option>
              ))}
            </select>
          </div>

          {/* Stack size */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Starting Stack: <span className="text-amber-400">{startingStack.toLocaleString()}</span>
            </label>
            <input
              type="range"
              min={1000}
              max={50000}
              step={1000}
              value={startingStack}
              onChange={(e) => setStartingStack(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          {/* Blinds */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Small Blind</label>
              <input
                type="number"
                value={smallBlind}
                onChange={(e) => setSmallBlind(parseInt(e.target.value) || 0)}
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Big Blind</label>
              <input
                type="number"
                value={bigBlind}
                onChange={(e) => setBigBlind(parseInt(e.target.value) || 0)}
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono"
              />
            </div>
          </div>

          {/* Number of hands */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Number of Hands: <span className="text-white">{numHands}</span>
            </label>
            <input
              type="range"
              min={1}
              max={50}
              value={numHands}
              onChange={(e) => setNumHands(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          {/* Start button */}
          <button
            onClick={handleStart}
            disabled={isLoading || !selectedModel}
            className={clsx(
              'w-full py-3 rounded-lg font-bold text-lg transition-all',
              'bg-gradient-to-r from-emerald-600 to-teal-600',
              'hover:from-emerald-500 hover:to-teal-500',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'shadow-lg hover:shadow-xl'
            )}
          >
            {isLoading ? 'Starting...' : 'Start Game'}
          </button>
        </div>

        {/* Info */}
        <div className="mt-6 text-center text-xs text-gray-500">
          Playing {numOpponents + 1}-handed No-Limit Texas Hold'em
        </div>
      </motion.div>
    </div>
  );
}
