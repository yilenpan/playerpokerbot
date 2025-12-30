import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import clsx from 'clsx';
import type { PlayerState } from '../../types';
import { Card, CardGroup } from './Card';

interface PlayerSeatProps {
  player: PlayerState;
  position: number;
  totalPlayers: number;
  isCurrentActor: boolean;
  isDealer: boolean;
  isSmallBlind: boolean;
  isBigBlind: boolean;
  showCards?: boolean;
  isThinking?: boolean;
}

// Random colors for thinking animation
const thinkingColors = [
  'rgba(139, 92, 246, 0.6)',   // violet
  'rgba(236, 72, 153, 0.6)',   // pink
  'rgba(59, 130, 246, 0.6)',   // blue
  'rgba(16, 185, 129, 0.6)',   // emerald
  'rgba(245, 158, 11, 0.6)',   // amber
  'rgba(239, 68, 68, 0.6)',    // red
  'rgba(6, 182, 212, 0.6)',    // cyan
  'rgba(168, 85, 247, 0.6)',   // purple
];

// Calculate position on ellipse - human (position 0) always at bottom
function getEllipsePosition(index: number, total: number): { x: number; y: number } {
  // Start from bottom (270 degrees / 3π/2) and go clockwise
  const startAngle = Math.PI * 1.5; // 270 degrees - bottom
  const angleStep = (2 * Math.PI) / total;
  const angle = startAngle + index * angleStep;

  // Ellipse radii (as percentages) - wider than tall
  const radiusX = 42; // horizontal radius
  const radiusY = 38; // vertical radius

  const x = 50 + radiusX * Math.cos(angle);
  const y = 50 + radiusY * Math.sin(angle);

  return { x, y };
}

export function PlayerSeat({
  player,
  position,
  totalPlayers,
  isCurrentActor,
  isDealer,
  isSmallBlind,
  isBigBlind,
  showCards = false,
  isThinking = false,
}: PlayerSeatProps) {
  const { x, y } = getEllipsePosition(position, totalPlayers);
  const isHuman = player.player_type === 'human';

  // Thinking color animation state
  const [thinkingColorIndex, setThinkingColorIndex] = useState(0);

  useEffect(() => {
    if (!isThinking) return;

    const interval = setInterval(() => {
      setThinkingColorIndex((prev) => {
        // Pick a random different color
        let next = Math.floor(Math.random() * thinkingColors.length);
        while (next === prev) {
          next = Math.floor(Math.random() * thinkingColors.length);
        }
        return next;
      });
    }, 800); // Change color every 800ms

    return () => clearInterval(interval);
  }, [isThinking]);

  const thinkingGlow = isThinking ? thinkingColors[thinkingColorIndex] : undefined;

  return (
    <div
      className="absolute -translate-x-1/2 -translate-y-1/2"
      style={{ left: `${x}%`, top: `${y}%` }}
    >
      {/* Player container */}
      <motion.div
        animate={{
          scale: isCurrentActor || isThinking ? 1.05 : 1,
          boxShadow: isThinking
            ? `0 0 30px ${thinkingGlow}, 0 0 60px ${thinkingGlow}`
            : isCurrentActor
              ? '0 0 20px rgba(59, 130, 246, 0.5)'
              : '0 4px 12px rgba(0, 0, 0, 0.3)',
        }}
        transition={{
          boxShadow: { duration: 0.8, ease: 'easeInOut' },
          scale: { duration: 0.3 },
        }}
        className={clsx(
          'relative rounded-xl p-3 min-w-[140px]',
          'bg-gray-800/90 border-2',
          isThinking && 'border-violet-400',
          isCurrentActor && !isThinking && 'border-blue-500',
          isHuman && !isCurrentActor && !isThinking && 'border-teal-500/50',
          !isHuman && !isCurrentActor && !isThinking && 'border-gray-600',
          !player.is_active && 'opacity-50'
        )}
      >
        {/* Position badges */}
        <div className="absolute -top-2 -right-2 flex gap-1">
          {isDealer && (
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-yellow-400 to-amber-500 text-black text-[10px] font-bold flex items-center justify-center shadow-lg border border-yellow-300">
              BTN
            </div>
          )}
          {isSmallBlind && (
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-sky-400 to-blue-500 text-white text-[10px] font-bold flex items-center justify-center shadow-lg border border-sky-300">
              SB
            </div>
          )}
          {isBigBlind && (
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-orange-400 to-red-500 text-white text-[10px] font-bold flex items-center justify-center shadow-lg border border-orange-300">
              BB
            </div>
          )}
        </div>

        {/* Player name */}
        <div className="flex items-center gap-2 mb-2">
          <div
            className={clsx(
              'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold',
              isHuman ? 'bg-teal-600 text-white' : 'bg-violet-600 text-white'
            )}
          >
            {player.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="text-sm font-semibold text-white">{player.name}</div>
            {player.model && (
              <div className="text-xs text-gray-400 truncate max-w-[80px]">{player.model}</div>
            )}
          </div>
        </div>

        {/* Hole cards */}
        <div className="flex justify-center mb-2">
          {(isHuman && player.hole_cards) || showCards ? (
            <CardGroup
              cards={player.hole_cards || []}
              faceDown={!isHuman && !showCards}
              size="sm"
            />
          ) : (
            <div className="flex gap-1">
              <Card faceDown size="sm" />
              <Card faceDown size="sm" />
            </div>
          )}
        </div>

        {/* Stack */}
        <div className="text-center">
          <span className="font-mono text-lg font-bold text-amber-400">
            {player.stack.toLocaleString()}
          </span>
        </div>

        {/* Current bet */}
        {player.current_bet > 0 && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute -bottom-8 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-amber-500/20 border border-amber-500/50"
          >
            <span className="font-mono text-sm text-amber-400">{player.current_bet}</span>
          </motion.div>
        )}

        {/* Last action */}
        {player.last_action && (
          <div className="absolute -top-6 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded bg-gray-700 text-xs text-gray-300">
            {player.last_action}
          </div>
        )}
      </motion.div>
    </div>
  );
}
