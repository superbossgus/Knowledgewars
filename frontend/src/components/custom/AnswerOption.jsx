import React from 'react';
import { cn } from '../../lib/cn';

export const AnswerOption = ({ label, text, state = 'idle', onSelect, disabled }) => {
  const base = 'relative rounded-xl border px-4 py-3 text-left cursor-pointer select-none transition-colors';
  
  const tone =
    state === 'correct'
      ? 'border-emerald-400/60 bg-emerald-400/10 ring-2 ring-emerald-400/40'
      : state === 'wrong'
      ? 'border-red-500/50 bg-red-500/5 animate-[shake_.4s_linear]'
      : 'border-white/10 bg-white/5 hover:bg-white/8';

  return (
    <button
      data-testid={`answer-${label}`}
      disabled={disabled}
      onClick={onSelect}
      className={cn(base, tone)}
    >
      <span className="mr-2 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-white/10 font-space text-xs font-semibold">
        {label}
      </span>
      <span className="text-sm md:text-base">{text}</span>
    </button>
  );
};
