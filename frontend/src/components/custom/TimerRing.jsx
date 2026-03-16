import React from 'react';
import { motion } from 'framer-motion';

export const TimerRing = ({ seconds, total = 10, warningAt = 3 }) => {
  const r = 36;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, seconds / total));
  const urgent = seconds <= warningAt;
  
  // Brand colors: Blue primary, Orange for warning
  const normalColor = 'hsl(220, 100%, 50%)';
  const urgentColor = 'hsl(25, 100%, 50%)';
  
  return (
    <div className="relative w-24 h-24" data-testid="match-timer">
      <svg className="w-24 h-24 -rotate-90" viewBox="0 0 100 100" aria-hidden>
        {/* Background circle */}
        <circle
          cx="50"
          cy="50"
          r="36"
          className="text-white/10"
          stroke="currentColor"
          strokeWidth="8"
          fill="none"
        />
        {/* Progress circle */}
        <motion.circle
          cx="50"
          cy="50"
          r="36"
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          stroke={urgent ? urgentColor : normalColor}
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          animate={{
            stroke: urgent ? urgentColor : normalColor,
          }}
          transition={{ duration: 0.2 }}
          style={{
            filter: `drop-shadow(0 0 8px ${urgent ? urgentColor : normalColor})`,
          }}
        />
      </svg>
      {/* Timer text */}
      <motion.div
        className="absolute inset-0 grid place-items-center font-brand text-2xl font-extrabold"
        animate={{
          scale: urgent ? [1, 1.1, 1] : 1,
          color: urgent ? urgentColor : 'white',
        }}
        transition={{
          duration: urgent ? 0.5 : 0.2,
          repeat: urgent ? Infinity : 0,
        }}
        style={{
          textShadow: urgent
            ? `0 0 15px ${urgentColor}`
            : `0 0 10px ${normalColor}`,
        }}
      >
        {seconds}s
      </motion.div>
    </div>
  );
};

export default TimerRing;
