import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState } from 'react';
import type { Card, PlayerState } from '../../types';
import { CardGroup } from './Card';

interface WinnerOverlayProps {
  winners: number[];
  amounts: number[];
  revealedCards: Record<number, Card[]>;
  players: PlayerState[];
  onNextHand: () => void;
}

// Confetti particle component
function Confetti({ delay }: { delay: number }) {
  const colors = ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'];
  const color = colors[Math.floor(Math.random() * colors.length)];
  const startX = Math.random() * 100;
  const endX = startX + (Math.random() - 0.5) * 40;
  const rotation = Math.random() * 720 - 360;
  const size = Math.random() * 8 + 4;

  return (
    <motion.div
      className="absolute pointer-events-none"
      style={{
        left: `${startX}%`,
        top: -20,
        width: size,
        height: size * 0.6,
        backgroundColor: color,
        borderRadius: 2,
      }}
      initial={{ y: 0, x: 0, rotate: 0, opacity: 1 }}
      animate={{
        y: [0, 600],
        x: [0, (endX - startX) * 5],
        rotate: [0, rotation],
        opacity: [1, 1, 0],
      }}
      transition={{
        duration: 3,
        delay,
        ease: 'easeIn',
      }}
    />
  );
}

// Star burst animation
function StarBurst() {
  return (
    <motion.div
      className="absolute inset-0 flex items-center justify-center pointer-events-none"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {[...Array(8)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute text-4xl"
          initial={{ scale: 0, opacity: 0 }}
          animate={{
            scale: [0, 1.5, 1],
            opacity: [0, 1, 0],
            x: Math.cos((i * Math.PI) / 4) * 150,
            y: Math.sin((i * Math.PI) / 4) * 150,
          }}
          transition={{
            duration: 1,
            delay: i * 0.1,
            repeat: 2,
            repeatDelay: 0.5,
          }}
        >
          ✦
        </motion.div>
      ))}
    </motion.div>
  );
}

export function WinnerOverlay({
  winners,
  amounts,
  revealedCards,
  players,
  onNextHand,
}: WinnerOverlayProps) {
  const [showConfetti, setShowConfetti] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setShowConfetti(false), 3000);
    return () => clearTimeout(timer);
  }, []);

  const totalWon = amounts.reduce((a, b) => a + b, 0);
  const winnerNames = winners.map((idx) => players[idx]?.name || `Player ${idx}`).join(', ');

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        {/* Confetti */}
        {showConfetti && (
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            {[...Array(50)].map((_, i) => (
              <Confetti key={i} delay={i * 0.05} />
            ))}
          </div>
        )}

        {/* Star burst */}
        <StarBurst />

        {/* Main content */}
        <motion.div
          className="relative z-10 flex flex-col items-center gap-6 p-8 rounded-2xl bg-gradient-to-b from-gray-800 to-gray-900 border-2 border-amber-500/50 shadow-2xl max-w-2xl mx-4"
          initial={{ scale: 0.5, opacity: 0, y: 50 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          transition={{ type: 'spring', damping: 15, delay: 0.2 }}
        >
          {/* Winner banner */}
          <motion.div
            className="text-center"
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            <motion.div
              className="text-5xl mb-2"
              animate={{
                scale: [1, 1.2, 1],
                rotate: [0, 5, -5, 0],
              }}
              transition={{
                duration: 0.5,
                repeat: 3,
                repeatDelay: 0.5,
              }}
            >
              🏆
            </motion.div>
            <h2 className="text-3xl font-bold text-amber-400 mb-1">WINNER!</h2>
            <p className="text-xl text-white font-semibold">{winnerNames}</p>
            <motion.p
              className="text-2xl font-bold text-emerald-400 mt-2"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', delay: 0.6 }}
            >
              +{totalWon.toLocaleString()} chips
            </motion.p>
          </motion.div>

          {/* Revealed cards for winners */}
          {winners.some((idx) => revealedCards[idx]?.length > 0) && (
            <motion.div
              className="flex flex-col items-center gap-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
            >
              <p className="text-gray-400 text-sm">Winning Hand</p>
              {winners.map((idx) =>
                revealedCards[idx] ? (
                  <div key={idx} className="flex items-center gap-3">
                    <span className="text-gray-300 text-sm">{players[idx]?.name}:</span>
                    <CardGroup cards={revealedCards[idx]} size="sm" />
                  </div>
                ) : null
              )}
            </motion.div>
          )}

          {/* All player stacks */}
          <motion.div
            className="w-full mt-4 p-4 rounded-lg bg-gray-900/50 border border-gray-700"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1 }}
          >
            <h3 className="text-gray-400 text-sm font-medium mb-3 text-center">Current Stacks</h3>
            <div className="space-y-2">
              {players.map((player, idx) => {
                const isWinner = winners.includes(idx);
                const wonAmount = isWinner ? amounts[winners.indexOf(idx)] : 0;

                return (
                  <motion.div
                    key={player.id}
                    className={`flex items-center justify-between px-3 py-2 rounded ${
                      isWinner ? 'bg-amber-500/20 border border-amber-500/30' : 'bg-gray-800/50'
                    }`}
                    initial={isWinner ? { x: -10 } : {}}
                    animate={isWinner ? { x: 0 } : {}}
                    transition={{ delay: 1.1 + idx * 0.1 }}
                  >
                    <div className="flex items-center gap-2">
                      {isWinner && <span className="text-amber-400">★</span>}
                      <span className={isWinner ? 'text-amber-300 font-semibold' : 'text-gray-300'}>
                        {player.name}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-white font-mono font-bold">
                        {player.stack.toLocaleString()}
                      </span>
                      {wonAmount > 0 && (
                        <span className="text-emerald-400 text-sm font-medium">
                          +{wonAmount.toLocaleString()}
                        </span>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>

          {/* Next hand button */}
          <motion.button
            onClick={onNextHand}
            className="mt-4 px-8 py-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-xl text-white font-bold text-lg shadow-lg hover:shadow-xl transition-all"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.3 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            Start Next Hand
          </motion.button>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
