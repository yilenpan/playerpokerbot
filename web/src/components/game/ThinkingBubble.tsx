import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { ThinkingStream } from '../../types';

interface ThinkingBubbleProps {
  stream?: ThinkingStream;
  playerName: string;
  className?: string;
  isExpanded?: boolean;
  onToggle?: () => void;
}

export function ThinkingBubble({
  stream,
  playerName,
  className,
  isExpanded = true,
  onToggle,
}: ThinkingBubbleProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom as new tokens arrive
  useEffect(() => {
    if (scrollRef.current && stream?.isActive) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [stream?.tokens, stream?.isActive]);

  if (!stream) {
    return null;
  }

  const { isActive, tokens, parsedAction } = stream;

  // Highlight action tags in the text
  const renderTokens = () => {
    const actionMatch = tokens.match(/<action>(.+?)<\/action>/i);

    if (actionMatch) {
      const beforeAction = tokens.slice(0, actionMatch.index);
      const actionText = actionMatch[1];
      const afterAction = tokens.slice((actionMatch.index || 0) + actionMatch[0].length);

      return (
        <>
          <span>{beforeAction}</span>
          <span className="inline-block px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded font-semibold">
            {actionText}
          </span>
          <span>{afterAction}</span>
        </>
      );
    }

    return tokens;
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className={clsx(
          'bg-gray-900/95 rounded-lg border-2 shadow-xl',
          'max-w-xs w-64',
          isActive ? 'border-violet-500 thinking-active' : 'border-violet-500/50',
          className
        )}
      >
        {/* Header - clickable to toggle collapse */}
        <button
          onClick={onToggle}
          className="w-full px-3 py-2 border-b border-gray-700 flex items-center gap-2 hover:bg-gray-800/50 transition-colors cursor-pointer"
        >
          <div
            className={clsx(
              'w-2 h-2 rounded-full',
              isActive ? 'bg-violet-500 animate-pulse' : 'bg-gray-500'
            )}
          />
          <span className="text-sm font-medium text-gray-300 flex-1 text-left">
            {playerName} {isActive ? 'is thinking...' : 'decided'}
          </span>
          <svg
            className={clsx(
              'w-4 h-4 text-gray-400 transition-transform duration-200',
              !isExpanded ? '-rotate-90' : 'rotate-0'
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* Collapsible content */}
        <AnimatePresence initial={false}>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              {/* Content */}
              <div
                ref={scrollRef}
                className={clsx(
                  'px-3 py-2 max-h-32 overflow-y-auto thinking-scroll',
                  'text-sm font-mono text-gray-300 leading-relaxed'
                )}
              >
                {tokens ? (
                  <span className={isActive ? 'typing-cursor' : ''}>
                    {renderTokens()}
                  </span>
                ) : (
                  <span className="text-gray-500 italic">Thinking...</span>
                )}
              </div>

              {/* Action result */}
              {!isActive && parsedAction && (
                <div className="px-3 py-2 border-t border-gray-700 bg-gray-800/50">
                  <span className="text-xs text-gray-400">Action: </span>
                  <span className="text-sm font-semibold text-emerald-400">
                    {parsedAction.action_type.toUpperCase()}
                    {parsedAction.amount && ` ${parsedAction.amount}`}
                  </span>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Pointer triangle */}
        <div
          className={clsx(
            'absolute -bottom-2 left-6 w-4 h-4',
            'bg-gray-900 border-b-2 border-r-2',
            isActive ? 'border-violet-500' : 'border-violet-500/50',
            'transform rotate-45'
          )}
        />
      </motion.div>
    </AnimatePresence>
  );
}
