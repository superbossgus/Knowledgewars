import React from 'react';
import { Swords } from 'lucide-react';

export const ScoreBoard = ({ me, opponent }) => {
  return (
    <div
      className="flex items-center gap-4 rounded-xl border-2 border-[hsl(220,100%,50%,0.3)] bg-black/40 p-3 backdrop-blur-xl"
      style={{ boxShadow: '0 0 20px hsl(220 100% 50% / 0.15)' }}
      data-testid="scoreboard"
    >
      {/* Player Me */}
      <div className="flex items-center gap-3">
        <span className={`fi fi-${me.flag?.toLowerCase()} h-5 w-7 rounded shadow-md`}></span>
        <div className="text-left">
          <div className="text-sm font-bold text-white truncate max-w-[80px]">{me.name}</div>
          <div className="text-xs text-[hsl(220,100%,70%)] font-medium">YOU</div>
        </div>
        <div
          className="rounded-lg bg-[hsl(220,100%,50%,0.2)] border border-[hsl(220,100%,50%,0.4)] px-3 py-1.5 font-brand text-xl font-extrabold text-white"
          style={{ textShadow: '0 0 10px hsl(220 100% 50%)' }}
        >
          {me.score}
        </div>
      </div>

      {/* VS Divider */}
      <div className="flex flex-col items-center px-2">
        <Swords className="w-5 h-5 text-[hsl(25,100%,50%)]" style={{ filter: 'drop-shadow(0 0 6px hsl(25 100% 50%))' }} />
        <span className="text-xs font-bold text-[hsl(25,100%,50%)] mt-1">VS</span>
      </div>

      {/* Opponent */}
      <div className="flex items-center gap-3">
        <div
          className="rounded-lg bg-[hsl(25,100%,50%,0.2)] border border-[hsl(25,100%,50%,0.4)] px-3 py-1.5 font-brand text-xl font-extrabold text-white"
          style={{ textShadow: '0 0 10px hsl(25 100% 50%)' }}
        >
          {opponent.score}
        </div>
        <div className="text-right">
          <div className="text-sm font-bold text-white truncate max-w-[80px]">{opponent.name}</div>
          <div className="text-xs text-[hsl(25,100%,70%)] font-medium">RIVAL</div>
        </div>
        <span className={`fi fi-${opponent.flag?.toLowerCase()} h-5 w-7 rounded shadow-md`}></span>
      </div>
    </div>
  );
};

export default ScoreBoard;
