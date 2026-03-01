import React from 'react';
import { motion } from 'framer-motion';

export const TimerRing = ({ seconds, total = 10, warningAt = 3 }) => {
  const r = 36;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, seconds / total));
  const stroke = c * pct;
  const urgent = seconds <= warningAt;

  return (
    <div className="relative w-24 h-24" data-testid="match-timer">
      <svg className="w-24 h-24 -rotate-90" viewBox="0 0 100 100" aria-hidden="true">
        <circle
          cx="50"
          cy="50"
          r="36"
          className="text-white/10"
          stroke="currentColor"
          strokeWidth="8"
          fill="none"
        />
        <motion.circle
          cx="50"
          cy="50"
          r="36"
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          stroke={urgent ? 'hsl(8, 78%, 54%)' : 'hsl(173, 85%, 45%)'}
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          animate={{
            stroke: urgent ? 'hsl(8, 78%, 54%)' : 'hsl(173, 85%, 45%)',
          }}
          transition={{ duration: 0.2 }}
        />
      </svg>
      <motion.div
        className="absolute inset-0 grid place-items-center font-space text-lg font-semibold"
        animate={urgent ? { scale: [1, 1.06, 1] } : {}}
        transition={{ repeat: urgent ? Infinity : 0, duration: 0.6 }}
      >
        {seconds}s
      </motion.div>
    </div>
  );
};
