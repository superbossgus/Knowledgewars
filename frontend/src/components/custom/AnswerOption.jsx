import React from 'react';
import { cn } from '../../lib/utils';

export const AnswerOption = ({ label, text, state = 'idle', onSelect, disabled }) => {
  const baseStyles = 'relative rounded-xl border-2 px-4 py-4 text-left cursor-pointer select-none transition-all duration-200';
  
  const stateStyles = {
    idle: 'border-[hsl(220,100%,50%,0.3)] bg-[hsl(220,100%,50%,0.05)] hover:bg-[hsl(220,100%,50%,0.12)] hover:border-[hsl(220,100%,50%,0.6)] hover:shadow-[0_0_20px_hsl(220,100%,50%,0.3)]',
    correct: 'border-[hsl(140,100%,45%)] bg-[hsl(140,100%,45%,0.15)] shadow-[0_0_25px_hsl(140,100%,45%,0.4)]',
    wrong: 'border-[hsl(0,100%,55%)] bg-[hsl(0,100%,55%,0.12)] shadow-[0_0_25px_hsl(0,100%,55%,0.4)] animate-[shake_0.4s_linear]',
  };
  
  const labelStyles = {
    idle: 'bg-[hsl(220,100%,50%,0.2)] text-[hsl(220,100%,70%)]',
    correct: 'bg-[hsl(140,100%,45%,0.3)] text-[hsl(140,100%,65%)]',
    wrong: 'bg-[hsl(0,100%,55%,0.3)] text-[hsl(0,100%,70%)]',
  };

  return (
    <button
      data-testid={`answer-${label}`}
      disabled={disabled}
      onClick={onSelect}
      className={cn(
        baseStyles,
        stateStyles[state],
        disabled && state === 'idle' && 'opacity-60 cursor-not-allowed hover:bg-[hsl(220,100%,50%,0.05)] hover:border-[hsl(220,100%,50%,0.3)] hover:shadow-none'
      )}
      style={{
        transform: state === 'correct' ? 'scale(1.02)' : 'scale(1)',
      }}
    >
      <span
        className={cn(
          'mr-3 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg font-brand text-sm font-bold',
          labelStyles[state]
        )}
      >
        {label}
      </span>
      <span className="text-white font-medium text-base">{text}</span>
    </button>
  );
};

export default AnswerOption;
