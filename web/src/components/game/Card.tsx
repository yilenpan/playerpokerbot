import { motion } from 'framer-motion';
import clsx from 'clsx';
import type { Card as CardType } from '../../types';

interface CardProps {
  card?: CardType;
  faceDown?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

// Suit image paths - handle multiple formats
const suitImages: Record<string, string> = {
  h: '/suits/heart.svg',
  d: '/suits/diamond.svg',
  c: '/suits/club.svg',
  s: '/suits/spade.svg',
  hearts: '/suits/heart.svg',
  diamonds: '/suits/diamond.svg',
  clubs: '/suits/club.svg',
  spades: '/suits/spade.svg',
};

// Suit symbols as fallback
const suitSymbols: Record<string, string> = {
  h: '♥',
  d: '♦',
  c: '♣',
  s: '♠',
  hearts: '♥',
  diamonds: '♦',
  clubs: '♣',
  spades: '♠',
};

// Normalize suit to single letter
function normalizeSuit(suit: string): string {
  const s = suit.toLowerCase();
  if (s === 'hearts' || s === 'heart') return 'h';
  if (s === 'diamonds' || s === 'diamond') return 'd';
  if (s === 'clubs' || s === 'club') return 'c';
  if (s === 'spades' || s === 'spade') return 's';
  return s.charAt(0); // Take first character
}

// Normalize rank
function normalizeRank(rank: string): string {
  if (!rank) return '?';
  const r = rank.toUpperCase();
  if (r === '10') return 'T';
  // Valid ranks only
  const validRanks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
  if (validRanks.includes(r)) return r;
  if (validRanks.includes(r.charAt(0))) return r.charAt(0);
  return '?';
}

const sizeClasses = {
  sm: 'w-10 h-14 text-sm',
  md: 'w-14 h-20 text-base',
  lg: 'w-20 h-28 text-xl',
};

// Check if card data is valid
function isValidCard(card: CardType | undefined): boolean {
  if (!card || !card.rank || !card.suit) return false;
  const rank = normalizeRank(card.rank);
  const suit = normalizeSuit(card.suit);
  const validRanks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
  const validSuits = ['h', 'd', 'c', 's'];
  return validRanks.includes(rank) && validSuits.includes(suit);
}

export function Card({ card, faceDown = false, size = 'md', className }: CardProps) {
  // Show face-down card if no card, faceDown requested, or invalid card data
  if (faceDown || !card || !isValidCard(card)) {
    return (
      <motion.div
        initial={{ rotateY: 180 }}
        animate={{ rotateY: 0 }}
        className={clsx(
          'rounded-lg bg-gradient-to-br from-blue-800 to-blue-950',
          'border-2 border-blue-700 shadow-lg',
          'flex items-center justify-center',
          sizeClasses[size],
          className
        )}
      >
        <div className="w-3/4 h-3/4 rounded border border-blue-600 bg-blue-900/50" />
      </motion.div>
    );
  }

  const suit = normalizeSuit(card.suit);
  const rank = normalizeRank(card.rank);
  const suitImage = suitImages[suit];
  const suitSymbol = suitSymbols[suit] || suit;
  const isRed = suit === 'h' || suit === 'd';

  // Size-specific icon sizes
  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };
  const centerIconSizes = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  // Always render suit as image
  const renderSuit = (sizeClass: string) => {
    // Default to spade if suit not recognized
    const imagePath = suitImage || '/suits/spade.svg';
    return (
      <img
        src={imagePath}
        alt={suitSymbol}
        className={sizeClass}
      />
    );
  };

  return (
    <motion.div
      initial={{ rotateY: -180, opacity: 0 }}
      animate={{ rotateY: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
      className={clsx(
        'rounded-lg bg-white shadow-lg',
        'border border-gray-200',
        'flex flex-col p-1',
        sizeClasses[size],
        className
      )}
    >
      {/* Top left corner */}
      <div className={clsx('flex items-center gap-0.5 font-bold leading-none', isRed ? 'text-red-600' : 'text-gray-900')}>
        <span>{rank}</span>
        {renderSuit(iconSizes[size])}
      </div>
      {/* Center suit */}
      <div className="flex-1 flex items-center justify-center">
        {renderSuit(centerIconSizes[size])}
      </div>
      {/* Bottom right corner (rotated) */}
      <div className={clsx('flex items-center justify-end gap-0.5 font-bold leading-none rotate-180', isRed ? 'text-red-600' : 'text-gray-900')}>
        <span>{rank}</span>
        {renderSuit(iconSizes[size])}
      </div>
    </motion.div>
  );
}

interface CardGroupProps {
  cards: CardType[];
  faceDown?: boolean;
  size?: 'sm' | 'md' | 'lg';
  overlap?: boolean;
}

export function CardGroup({ cards, faceDown = false, size = 'md', overlap = true }: CardGroupProps) {
  return (
    <div className="flex">
      {cards.map((card, idx) => (
        <Card
          key={`${card.rank}${card.suit}`}
          card={card}
          faceDown={faceDown}
          size={size}
          className={clsx(overlap && idx > 0 && '-ml-4')}
        />
      ))}
    </div>
  );
}
