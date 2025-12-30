import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useGameStore } from '../../store/gameStore';
import { PlayerSeat } from './PlayerSeat';
import { CardGroup } from './Card';
import { TurnTimer } from './TurnTimer';
import { ActionPanel } from './ActionPanel';
import { WinnerOverlay } from './WinnerOverlay';

interface PokerTableProps {
  onAction: (actionType: string, amount?: number) => void;
  onStartHand: () => void;
}

export function PokerTable({ onAction, onStartHand }: PokerTableProps) {
  const { gameState, thinkingStreams, reasoningHistory, timer, isMyTurn, availableActions, toggleReasoningExpanded, handComplete, dismissHandComplete } = useGameStore();

  const handleNextHand = () => {
    dismissHandComplete();
    onStartHand();
  };

  const isWaitingToStart = gameState?.hand_number === 0;

  if (!gameState) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400">Waiting for game to start...</div>
      </div>
    );
  }

  const { players, community_cards, pot, button_position, current_actor, hand_number, street } =
    gameState;

  // Calculate blind positions
  const numPlayers = players.length;
  const sbPosition = (button_position + 1) % numPlayers;
  const bbPosition = (button_position + 2) % numPlayers;

  // Highlight action tags in the text
  const renderThinkingTokens = (tokens: string) => {
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
    <div className="relative w-full h-full flex flex-col">
      {/* Header */}
      <div className="flex justify-between items-center px-6 py-3 bg-gray-900/50">
        <div className="text-gray-400">
          <span className="font-semibold text-white">Hand #{hand_number}</span>
          <span className="mx-2">|</span>
          <span className="capitalize">{street}</span>
        </div>
        <div className="text-amber-400 font-mono">
          <span className="text-gray-400">Pot: </span>
          <span className="text-xl font-bold">{pot.toLocaleString()}</span>
        </div>
      </div>

      {/* Table area - larger */}
      <div className="flex-1 relative mx-auto w-full max-w-6xl min-h-[650px]">
        {/* Table felt */}
        <div
          className={clsx(
            'absolute inset-4 rounded-[120px]',
            'bg-gradient-to-br from-emerald-800 to-emerald-950',
            'border-8 border-amber-900',
            'shadow-[inset_0_4px_20px_rgba(0,0,0,0.5)]'
          )}
        >
          {/* Table edge pattern */}
          <div className="absolute inset-2 rounded-[110px] border-2 border-amber-800/30" />
        </div>

        {/* Community cards */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
          <div className="flex flex-col items-center gap-4">
            {/* Cards */}
            {community_cards.length > 0 ? (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <CardGroup cards={community_cards} size="md" overlap={false} />
              </motion.div>
            ) : (
              <div className="h-20 flex items-center text-gray-500 text-sm">
                Waiting for cards...
              </div>
            )}

            {/* Pot display */}
            <motion.div
              key={pot}
              initial={{ scale: 1.2 }}
              animate={{ scale: 1 }}
              className="px-4 py-2 rounded-full bg-black/50 border border-amber-500/30"
            >
              <span className="text-amber-400 font-mono font-bold text-lg">
                {pot.toLocaleString()}
              </span>
            </motion.div>
          </div>
        </div>

        {/* Player seats */}
        {players.map((player, idx) => (
          <PlayerSeat
            key={player.id}
            player={player}
            position={idx}
            totalPlayers={numPlayers}
            isCurrentActor={current_actor === idx}
            isDealer={button_position === idx}
            isSmallBlind={sbPosition === idx}
            isBigBlind={bbPosition === idx}
            showCards={false}
            isThinking={thinkingStreams[player.id]?.isActive ?? false}
          />
        ))}

        {/* Turn timer for current human player */}
        {isMyTurn && timer && (
          <div className="absolute bottom-24 left-1/2 -translate-x-1/2">
            <TurnTimer timer={timer} size={70} />
          </div>
        )}
      </div>

      {/* Bottom section: Action panel on top, Thinking panel below - full width */}
      <div className="flex flex-col gap-4 px-6 py-4 bg-gray-900/30 max-w-6xl mx-auto w-full">
        {/* Action panel - centered */}
        <div className="flex justify-center">
          {isWaitingToStart ? (
            <div className="flex flex-col items-center gap-4">
              <button
                onClick={onStartHand}
                className="px-8 py-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-xl text-white font-bold text-xl shadow-lg hover:shadow-xl transition-all"
              >
                Start Hand
              </button>
              <p className="text-gray-500 text-sm">Click to deal cards and begin playing</p>
            </div>
          ) : isMyTurn ? (
            <ActionPanel
              availableActions={availableActions}
              timer={timer}
              onAction={onAction}
              disabled={false}
            />
          ) : (
            <div className="h-24 flex items-center justify-center text-gray-500">
              {current_actor !== null ? (
                <span>
                  Waiting for{' '}
                  <span className="text-white font-semibold">
                    {players[current_actor]?.name || 'opponent'}
                  </span>
                  ...
                </span>
              ) : (
                <span>Waiting...</span>
              )}
            </div>
          )}
        </div>

        {/* LLM Reasoning Panel - full width with collapsible sections per player */}
        <div className="w-full bg-gray-900/95 rounded-lg border border-gray-700">
          {/* Get all LLM players */}
          {players.filter(p => p.player_type === 'llm').map(player => {
            const history = reasoningHistory[player.id];
            const activeStream = thinkingStreams[player.id];
            const isExpanded = history?.isExpanded ?? true;
            const entries = history?.entries ?? [];

            return (
              <div key={player.id} className="border-b border-gray-700 last:border-b-0">
                {/* Collapsible header */}
                <button
                  onClick={() => toggleReasoningExpanded(player.id)}
                  className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-800/50 transition-colors"
                >
                  {/* Status indicator */}
                  <div
                    className={clsx(
                      'w-2 h-2 rounded-full flex-shrink-0',
                      activeStream?.isActive ? 'bg-violet-500 animate-pulse' : 'bg-gray-500'
                    )}
                  />

                  {/* Player name */}
                  <span className="text-sm font-semibold text-gray-200">
                    {player.name}
                  </span>

                  {/* Current status */}
                  <span className="text-xs text-gray-400">
                    {activeStream?.isActive
                      ? 'thinking...'
                      : entries.length > 0
                        ? `${entries.length} decision${entries.length !== 1 ? 's' : ''}`
                        : 'waiting'}
                  </span>

                  {/* Latest action badge */}
                  {entries.length > 0 && !activeStream?.isActive && (
                    <span className="ml-auto text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                      {entries[entries.length - 1].parsedAction?.action_type.toUpperCase()}
                      {entries[entries.length - 1].parsedAction?.amount ? ` ${entries[entries.length - 1].parsedAction?.amount}` : ''}
                    </span>
                  )}

                  {/* Expand/collapse icon */}
                  <svg
                    className={clsx(
                      'w-4 h-4 text-gray-400 transition-transform duration-200 ml-auto',
                      !isExpanded && '-rotate-90'
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
                      <div className="px-4 pb-3 max-h-48 overflow-y-auto">
                        {/* Show active stream first if thinking */}
                        {activeStream?.isActive && activeStream.tokens && (
                          <div className="mb-3 p-2 bg-violet-500/10 rounded border border-violet-500/30">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs text-violet-400 font-medium">
                                Hand #{gameState?.hand_number} • {gameState?.street}
                              </span>
                              <span className="text-xs text-violet-300 animate-pulse">thinking...</span>
                            </div>
                            <p className="text-sm font-mono text-gray-300 leading-relaxed typing-cursor">
                              {renderThinkingTokens(activeStream.tokens)}
                            </p>
                          </div>
                        )}

                        {/* Show history entries (most recent first) */}
                        {[...entries].reverse().map((entry, idx) => (
                          <div
                            key={`${entry.handNumber}-${entry.street}-${idx}`}
                            className="mb-2 p-2 bg-gray-800/50 rounded border border-gray-700"
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs text-gray-400">
                                Hand #{entry.handNumber} • {entry.street}
                              </span>
                              {entry.parsedAction && (
                                <span className="text-xs font-semibold text-emerald-400">
                                  → {entry.parsedAction.action_type.toUpperCase()}
                                  {entry.parsedAction.amount && ` ${entry.parsedAction.amount}`}
                                </span>
                              )}
                            </div>
                            <p className="text-sm font-mono text-gray-300 leading-relaxed">
                              {renderThinkingTokens(entry.tokens)}
                            </p>
                          </div>
                        ))}

                        {/* Empty state */}
                        {entries.length === 0 && !activeStream?.isActive && (
                          <p className="text-sm text-gray-500 italic py-2">
                            No reasoning yet...
                          </p>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}

          {/* Empty state when no LLM players */}
          {players.filter(p => p.player_type === 'llm').length === 0 && (
            <div className="px-4 py-6 text-center text-gray-500">
              No LLM opponents in this game
            </div>
          )}
        </div>
      </div>

      {/* Winner overlay */}
      {handComplete?.isVisible && (
        <WinnerOverlay
          winners={handComplete.winners}
          amounts={handComplete.amounts}
          revealedCards={handComplete.revealedCards}
          players={players}
          onNextHand={handleNextHand}
        />
      )}
    </div>
  );
}
