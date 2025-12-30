import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { AvailableActions, TurnTimerState } from '../../types';
import { InlineTimer } from './TurnTimer';

interface ActionPanelProps {
  availableActions: AvailableActions | null;
  timer: TurnTimerState | null;
  onAction: (actionType: string, amount?: number) => void;
  disabled?: boolean;
}

export function ActionPanel({ availableActions, timer, onAction, disabled }: ActionPanelProps) {
  const [raiseAmount, setRaiseAmount] = useState<number>(0);
  const [showRaiseSlider, setShowRaiseSlider] = useState(false);

  // Set initial raise amount when available actions change
  useState(() => {
    if (availableActions?.min_raise) {
      setRaiseAmount(availableActions.min_raise);
    }
  });

  const handleFold = useCallback(() => {
    onAction('fold');
  }, [onAction]);

  const handleCheckCall = useCallback(() => {
    if (availableActions?.can_check) {
      onAction('check');
    } else {
      onAction('call');
    }
  }, [onAction, availableActions]);

  const handleRaise = useCallback(() => {
    if (showRaiseSlider) {
      onAction('raise', raiseAmount);
      setShowRaiseSlider(false);
    } else {
      setShowRaiseSlider(true);
      if (availableActions?.min_raise) {
        setRaiseAmount(availableActions.min_raise);
      }
    }
  }, [onAction, raiseAmount, showRaiseSlider, availableActions]);

  const handleAllIn = useCallback(() => {
    onAction('all_in');
  }, [onAction]);

  const handleQuickBet = useCallback(
    (multiplier: number) => {
      if (!availableActions) return;
      const amount = Math.min(
        Math.floor(availableActions.max_raise * multiplier),
        availableActions.max_raise
      );
      setRaiseAmount(amount);
    },
    [availableActions]
  );

  if (!availableActions) {
    return null;
  }

  const { can_fold, can_check, call_amount, can_raise, min_raise, max_raise } =
    availableActions;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20 }}
        className="bg-gray-900/95 rounded-xl border border-gray-700 p-4 shadow-2xl"
      >
        {/* Timer indicator */}
        {timer && (
          <div className="flex items-center justify-center gap-2 mb-3 text-sm text-gray-400">
            <span>Time remaining:</span>
            <InlineTimer timer={timer} />
          </div>
        )}

        {/* Main action buttons */}
        <div className="flex gap-3 justify-center">
          {/* Fold button */}
          {can_fold && (
            <button
              onClick={handleFold}
              disabled={disabled}
              className={clsx(
                'action-btn px-6 py-3 rounded-lg font-semibold',
                'bg-rose-600 hover:bg-rose-500 text-white',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              Fold
            </button>
          )}

          {/* Check/Call button */}
          <button
            onClick={handleCheckCall}
            disabled={disabled}
            className={clsx(
              'action-btn px-6 py-3 rounded-lg font-semibold',
              'bg-blue-600 hover:bg-blue-500 text-white',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {can_check ? 'Check' : `Call ${call_amount}`}
          </button>

          {/* Raise button */}
          {can_raise && (
            <button
              onClick={handleRaise}
              disabled={disabled}
              className={clsx(
                'action-btn px-6 py-3 rounded-lg font-semibold',
                'bg-emerald-600 hover:bg-emerald-500 text-white',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                showRaiseSlider && 'ring-2 ring-emerald-400'
              )}
            >
              {showRaiseSlider ? `Raise to ${raiseAmount}` : 'Raise'}
            </button>
          )}

          {/* All-in button */}
          {can_raise && max_raise > 0 && (
            <button
              onClick={handleAllIn}
              disabled={disabled}
              className={clsx(
                'action-btn px-6 py-3 rounded-lg font-semibold',
                'bg-gradient-to-r from-amber-500 to-orange-500',
                'hover:from-amber-400 hover:to-orange-400 text-white',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              All-In
            </button>
          )}
        </div>

        {/* Raise slider */}
        <AnimatePresence>
          {showRaiseSlider && can_raise && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 space-y-3"
            >
              {/* Slider */}
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-400 w-16 text-right font-mono">
                  {min_raise}
                </span>
                <input
                  type="range"
                  min={min_raise}
                  max={max_raise}
                  value={raiseAmount}
                  onChange={(e) => setRaiseAmount(parseInt(e.target.value))}
                  className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer
                    [&::-webkit-slider-thumb]:appearance-none
                    [&::-webkit-slider-thumb]:w-4
                    [&::-webkit-slider-thumb]:h-4
                    [&::-webkit-slider-thumb]:rounded-full
                    [&::-webkit-slider-thumb]:bg-emerald-500
                    [&::-webkit-slider-thumb]:cursor-pointer"
                />
                <span className="text-sm text-gray-400 w-16 font-mono">{max_raise}</span>
              </div>

              {/* Quick bet buttons */}
              <div className="flex justify-center gap-2">
                <button
                  onClick={() => handleQuickBet(0.33)}
                  className="px-3 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-gray-300"
                >
                  1/3 Pot
                </button>
                <button
                  onClick={() => handleQuickBet(0.5)}
                  className="px-3 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-gray-300"
                >
                  1/2 Pot
                </button>
                <button
                  onClick={() => handleQuickBet(0.75)}
                  className="px-3 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-gray-300"
                >
                  3/4 Pot
                </button>
                <button
                  onClick={() => handleQuickBet(1)}
                  className="px-3 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-gray-300"
                >
                  Pot
                </button>
              </div>

              {/* Confirm/Cancel */}
              <div className="flex justify-center gap-2">
                <button
                  onClick={() => setShowRaiseSlider(false)}
                  className="px-4 py-2 text-sm rounded bg-gray-700 hover:bg-gray-600 text-gray-300"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRaise}
                  className="px-4 py-2 text-sm rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold"
                >
                  Confirm Raise
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Keyboard shortcuts hint */}
        <div className="mt-3 text-center text-xs text-gray-500">
          Keyboard: <kbd className="px-1 bg-gray-800 rounded">F</kbd> Fold{' '}
          <kbd className="px-1 bg-gray-800 rounded">C</kbd> Check/Call{' '}
          <kbd className="px-1 bg-gray-800 rounded">R</kbd> Raise
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
