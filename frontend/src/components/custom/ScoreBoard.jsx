import React from 'react';

export const ScoreBoard = ({ me, opponent }) => (
  <div
    className="sticky top-0 z-20 grid grid-cols-2 gap-2 rounded-xl border border-white/10 bg-black/30 p-2 backdrop-blur-md"
    data-testid="scoreboard"
  >
    {[me, opponent].map((p, i) => (
      <div key={i} className="flex items-center gap-2">
        <span className={`fi fi-${p.flag.toLowerCase()} h-4 w-6 rounded-sm`}></span>
        <span className="font-space font-semibold text-sm truncate">{p.name}</span>
        <span className="ml-auto rounded-md bg-white/10 px-2 py-1 font-space text-sm font-bold">
          {p.score}
        </span>
      </div>
    ))}
  </div>
);
