import React from 'react';
import { cn } from '../../lib/cn';

const OPTION_COLORS = {
  A: { border: 'hsl(180 100% 50%)', glow: '0 0 15px hsl(180 100% 50% / 0.4), 0 0 30px hsl(180 100% 50% / 0.2)' },
  B: { border: 'hsl(140 100% 50%)', glow: '0 0 15px hsl(140 100% 50% / 0.4), 0 0 30px hsl(140 100% 50% / 0.2)' },
  C: { border: 'hsl(85 100% 55%)', glow: '0 0 15px hsl(85 100% 55% / 0.4), 0 0 30px hsl(85 100% 55% / 0.2)' },
  D: { border: 'hsl(25 100% 55%)', glow: '0 0 15px hsl(25 100% 55% / 0.4), 0 0 30px hsl(25 100% 55% / 0.2)' },
  E: { border: 'hsl(320 100% 60%)', glow: '0 0 15px hsl(320 100% 60% / 0.4), 0 0 30px hsl(320 100% 60% / 0.2)' },
  F: { border: 'hsl(280 100% 65%)', glow: '0 0 15px hsl(280 100% 65% / 0.4), 0 0 30px hsl(280 100% 65% / 0.2)' },
};

export const AnswerOption = ({ label, text, state = 'idle', onSelect, disabled }) => {
  const colors = OPTION_COLORS[label] || OPTION_COLORS.A;
  
  const getStateStyles = () => {
    if (state === 'correct') {
      return {
        borderColor: 'hsl(140 100% 50%)',
        boxShadow: '0 0 20px hsl(140 100% 50% / 0.6), 0 0 40px hsl(140 100% 50% / 0.3), inset 0 0 20px hsl(140 100% 50% / 0.1)',
        background: 'linear-gradient(135deg, rgba(52, 211, 153, 0.2) 0%, rgba(52, 211, 153, 0.05) 100%)',
      };
    }
    if (state === 'wrong') {
      return {
        borderColor: 'hsl(0 100% 60%)',
        boxShadow: '0 0 20px hsl(0 100% 60% / 0.6), 0 0 40px hsl(0 100% 60% / 0.3)',
        background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.05) 100%)',
      };
    }
    return {
      borderColor: colors.border,
      boxShadow: colors.glow,
    };
  };

  const stateStyles = getStateStyles();
  const isInteractive = state === 'idle' && !disabled;

  return (
    <button
      data-testid={`answer-${label}`}
      disabled={disabled}
      onClick={onSelect}
      className={cn(
        'relative rounded-xl border-2 px-4 py-3 text-left transition-all duration-200',
        'bg-black/20 backdrop-blur-sm',
        isInteractive && 'hover:scale-[1.02] active:scale-[0.98] cursor-pointer',
        !isInteractive && 'cursor-not-allowed opacity-80',
        state === 'wrong' && 'animate-[shake_.4s_linear]'
      )}
      style={{
        borderColor: stateStyles.borderColor,
        boxShadow: stateStyles.boxShadow,
        background: stateStyles.background,
      }}
    >
      {/* Animated border glow */}
      <div 
        className="absolute inset-0 rounded-xl opacity-0 hover:opacity-100 transition-opacity pointer-events-none"
        style={{
          background: `linear-gradient(135deg, ${colors.border}20, ${colors.border}10)`,
        }}
      />
      
      {/* Label badge */}
      <span 
        className="mr-3 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg font-space text-xs font-bold"
        style={{
          background: `linear-gradient(135deg, ${colors.border}40, ${colors.border}20)`,
          color: colors.border,
          boxShadow: `0 0 10px ${colors.border}40`,
        }}
      >
        {label}
      </span>
      
      {/* Answer text */}
      <span className="text-sm md:text-base font-medium text-white/90">{text}</span>
    </button>
  );
};
