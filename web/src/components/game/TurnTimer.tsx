import { useMemo } from 'react';
import clsx from 'clsx';
import type { TurnTimerState } from '../../types';

interface TurnTimerProps {
  timer: TurnTimerState | null;
  size?: number;
  className?: string;
}

export function TurnTimer({ timer, size = 80, className }: TurnTimerProps) {
  if (!timer) {
    return null;
  }

  const { totalSeconds, remainingSeconds, isExpired } = timer;

  // Calculate progress
  const progress = remainingSeconds / totalSeconds;
  const circumference = 2 * Math.PI * 35; // radius = 35
  const strokeDashoffset = circumference * (1 - progress);

  // Determine color based on remaining time
  const getColor = () => {
    if (isExpired || remainingSeconds <= 0) return '#ef4444'; // red
    if (remainingSeconds <= 5) return '#ef4444'; // red (critical)
    if (remainingSeconds <= 10) return '#f59e0b'; // yellow (warning)
    return '#10b981'; // green
  };

  const getAnimationClass = () => {
    if (remainingSeconds <= 5) return 'timer-critical';
    if (remainingSeconds <= 10) return 'timer-warning';
    return '';
  };

  const color = useMemo(getColor, [remainingSeconds, isExpired]);

  return (
    <div
      className={clsx('relative inline-flex items-center justify-center', className)}
      style={{ width: size, height: size }}
    >
      {/* Background circle */}
      <svg className="absolute" width={size} height={size} viewBox="0 0 80 80">
        <circle
          cx="40"
          cy="40"
          r="35"
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="6"
        />
      </svg>

      {/* Progress circle */}
      <svg
        className={clsx('absolute -rotate-90', getAnimationClass())}
        width={size}
        height={size}
        viewBox="0 0 80 80"
      >
        <circle
          cx="40"
          cy="40"
          r="35"
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          style={{
            transition: 'stroke-dashoffset 0.5s ease-out, stroke 0.3s ease',
          }}
        />
      </svg>

      {/* Center text */}
      <div className={clsx('flex flex-col items-center', getAnimationClass())}>
        <span
          className="font-mono font-bold"
          style={{
            fontSize: size * 0.3,
            color,
            transition: 'color 0.3s ease',
          }}
        >
          {Math.max(0, remainingSeconds)}
        </span>
        <span
          className="text-gray-400"
          style={{ fontSize: size * 0.12 }}
        >
          secs
        </span>
      </div>
    </div>
  );
}

// Compact inline timer for action panel
interface InlineTimerProps {
  timer: TurnTimerState | null;
}

export function InlineTimer({ timer }: InlineTimerProps) {
  if (!timer) return null;

  const { remainingSeconds, isExpired } = timer;

  const getColorClass = () => {
    if (isExpired || remainingSeconds <= 0) return 'text-red-500';
    if (remainingSeconds <= 5) return 'text-red-500 timer-critical';
    if (remainingSeconds <= 10) return 'text-yellow-500 timer-warning';
    return 'text-emerald-500';
  };

  return (
    <span className={clsx('font-mono font-bold', getColorClass())}>
      {Math.max(0, remainingSeconds)}s
    </span>
  );
}
