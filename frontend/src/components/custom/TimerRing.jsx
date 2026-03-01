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
      {/* Outer glow ring */}
      <div 
        className="absolute inset-0 rounded-full"
        style={{
          background: urgent 
            ? 'radial-gradient(circle, hsl(0 100% 60% / 0.3) 0%, transparent 70%)'
            : 'radial-gradient(circle, hsl(180 100% 50% / 0.3) 0%, transparent 70%)',
          filter: 'blur(8px)',
        }}
      />
      
      <svg className="w-24 h-24 -rotate-90 relative z-10" viewBox="0 0 100 100" aria-hidden="true">
        {/* Background circle */}
        <circle
          cx="50"
          cy="50"
          r="36"
          className="text-white/10"
          stroke="currentColor"
          strokeWidth="6"
          fill="none"
        />
        {/* Neon progress circle */}
        <motion.circle
          cx="50"
          cy="50"
          r="36"
          strokeWidth="6"
          fill="none"
          strokeLinecap="round"
          stroke={urgent ? 'url(#gradient-red)' : 'url(#gradient-cyan)'}
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          style={{
            filter: urgent 
              ? 'drop-shadow(0 0 8px hsl(0 100% 60%)) drop-shadow(0 0 16px hsl(0 100% 60% / 0.5))'
              : 'drop-shadow(0 0 8px hsl(180 100% 50%)) drop-shadow(0 0 16px hsl(180 100% 50% / 0.5))'
          }}
          animate={urgent ? { 
            opacity: [1, 0.7, 1],
          } : {}}
          transition={{ repeat: urgent ? Infinity : 0, duration: 0.5 }}
        />
        
        {/* Gradient definitions */}
        <defs>
          <linearGradient id="gradient-cyan" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="hsl(180, 100%, 60%)" />
            <stop offset="100%" stopColor="hsl(140, 100%, 50%)" />
          </linearGradient>
          <linearGradient id="gradient-red" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="hsl(0, 100%, 70%)" />
            <stop offset="100%" stopColor="hsl(25, 100%, 60%)" />
          </linearGradient>
        </defs>
      </svg>
      
      {/* Timer text with glow */}
      <motion.div
        className="absolute inset-0 grid place-items-center font-space text-2xl font-bold"
        style={{
          color: urgent ? 'hsl(0, 100%, 70%)' : 'hsl(180, 100%, 80%)',
          textShadow: urgent 
            ? '0 0 10px hsl(0 100% 60%), 0 0 20px hsl(0 100% 60% / 0.5)'
            : '0 0 10px hsl(180 100% 50%), 0 0 20px hsl(180 100% 50% / 0.5)'
        }}
        animate={urgent ? { scale: [1, 1.1, 1] } : {}}
        transition={{ repeat: urgent ? Infinity : 0, duration: 0.6 }}
      >
        {seconds}
      </motion.div>
    </div>
  );
};
