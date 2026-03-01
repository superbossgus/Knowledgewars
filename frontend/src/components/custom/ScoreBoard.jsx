import React from 'react';
import { Swords } from 'lucide-react';

export const ScoreBoard = ({ me, opponent }) => (
  <div
    className="relative grid grid-cols-[1fr_auto_1fr] gap-3 rounded-xl border-2 p-3 backdrop-blur-md"
    style={{
      borderColor: 'hsl(180 100% 50% / 0.3)',
      background: 'linear-gradient(135deg, rgba(0, 0, 0, 0.6) 0%, rgba(0, 0, 0, 0.4) 100%)',
      boxShadow: '0 0 20px hsl(180 100% 50% / 0.2), inset 0 0 20px rgba(180, 255, 255, 0.05)',
    }}
    data-testid="scoreboard"
  >
    {/* Animated border */}
    <div 
      className="absolute inset-0 rounded-xl pointer-events-none"
      style={{
        background: 'linear-gradient(90deg, hsl(180 100% 50% / 0.3), hsl(320 100% 60% / 0.3), hsl(180 100% 50% / 0.3))',
        WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
        mask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
        WebkitMaskComposite: 'xor',
        maskComposite: 'exclude',
        padding: '2px',
        animation: 'glow-rotate 4s linear infinite',
      }}
    />
    
    {/* Player 1 (You) */}
    <div className="flex items-center gap-2 min-w-0">
      <span className={`fi fi-${me.flag.toLowerCase()} h-5 w-7 rounded-sm shrink-0 shadow-lg`}></span>
      <div className="flex-1 min-w-0">
        <div className="font-space font-semibold text-sm truncate text-cyan-300" style={{ textShadow: '0 0 10px hsl(180 100% 50% / 0.5)' }}>
          {me.name}
        </div>
      </div>
      <div 
        className="rounded-lg px-3 py-1.5 font-space text-base font-bold shrink-0"
        style={{
          background: 'linear-gradient(135deg, hsl(180 100% 50% / 0.3), hsl(180 100% 50% / 0.1))',
          color: 'hsl(180 100% 80%)',
          boxShadow: '0 0 15px hsl(180 100% 50% / 0.3)',
          border: '1px solid hsl(180 100% 50% / 0.5)',
        }}
      >
        {me.score}
      </div>
    </div>
    
    {/* VS Badge */}
    <div 
      className="flex items-center justify-center px-3 py-1 rounded-lg font-space text-xs font-bold"
      style={{
        background: 'linear-gradient(135deg, hsl(320 100% 60% / 0.3), hsl(25 100% 55% / 0.3))',
        color: 'hsl(25 100% 70%)',
        boxShadow: '0 0 20px hsl(320 100% 60% / 0.4), 0 0 40px hsl(25 100% 55% / 0.3)',
        border: '1px solid hsl(320 100% 60% / 0.5)',
      }}
    >
      <Swords className="w-4 h-4" />
    </div>
    
    {/* Player 2 (Opponent) */}
    <div className="flex items-center gap-2 min-w-0 flex-row-reverse">
      <span className={`fi fi-${opponent.flag.toLowerCase()} h-5 w-7 rounded-sm shrink-0 shadow-lg`}></span>
      <div className="flex-1 min-w-0 text-right">
        <div className="font-space font-semibold text-sm truncate text-pink-300" style={{ textShadow: '0 0 10px hsl(320 100% 60% / 0.5)' }}>
          {opponent.name}
        </div>
      </div>
      <div 
        className="rounded-lg px-3 py-1.5 font-space text-base font-bold shrink-0"
        style={{
          background: 'linear-gradient(135deg, hsl(320 100% 60% / 0.3), hsl(320 100% 60% / 0.1))',
          color: 'hsl(320 100% 80%)',
          boxShadow: '0 0 15px hsl(320 100% 60% / 0.3)',
          border: '1px solid hsl(320 100% 60% / 0.5)',
        }}
      >
        {opponent.score}
      </div>
    </div>
  </div>
);
