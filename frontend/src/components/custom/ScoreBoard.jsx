import React from 'react';
import { Swords, Shield, Award, Star, Zap, Diamond, Crown, Trophy, Gem, Brain } from 'lucide-react';

// Tier icons mapping
const tierIcons = {
  bronce: Shield,
  plata: Award,
  oro: Star,
  platino: Zap,
  diamante: Diamond,
  maestro: Crown,
  campeon: Trophy,
  gran_maestro: Gem,
  genio: Brain
};

// Tier colors
const tierColors = {
  bronce: 'hsl(28, 65%, 46%)',
  plata: 'hsl(214, 10%, 76%)',
  oro: 'hsl(45, 92%, 48%)',
  platino: 'hsl(185, 60%, 55%)',
  diamante: 'hsl(200, 100%, 55%)',
  maestro: 'hsl(280, 80%, 60%)',
  campeon: 'hsl(340, 80%, 55%)',
  gran_maestro: 'hsl(25, 100%, 55%)',
  genio: 'hsl(50, 100%, 50%)'
};

const PlayerRankIcon = ({ tier }) => {
  const Icon = tierIcons[tier] || Shield;
  const color = tierColors[tier] || tierColors.bronce;
  
  return (
    <Icon 
      className="w-4 h-4" 
      style={{ 
        color: color,
        filter: `drop-shadow(0 0 4px ${color})`
      }} 
    />
  );
};

export const ScoreBoard = ({ me, opponent }) => {
  return (
    <div
      className="flex items-center gap-3 md:gap-6 rounded-xl border-2 border-[hsl(220,100%,50%,0.3)] bg-black/40 p-3 md:p-4 backdrop-blur-xl"
      style={{ boxShadow: '0 0 20px hsl(220 100% 50% / 0.15)' }}
      data-testid="scoreboard"
    >
      {/* Player Me */}
      <div className="flex items-center gap-2 md:gap-3 flex-1 min-w-0">
        <span className={`fi fi-${me.flag?.toLowerCase()} h-6 w-8 rounded shadow-md shrink-0`}></span>
        <div className="text-left min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <PlayerRankIcon tier={me.tier || 'bronce'} />
            <span 
              className="text-sm md:text-base font-bold text-white truncate block"
              style={{ maxWidth: '120px' }}
              title={me.name}
            >
              {me.name}
            </span>
          </div>
          <div className="text-xs text-[hsl(220,100%,70%)] font-semibold flex items-center gap-1">
            <span className="uppercase">Tú</span>
            {me.elo && <span className="opacity-70">• {me.elo} ELO</span>}
          </div>
        </div>
        <div
          className="rounded-lg bg-[hsl(220,100%,50%,0.2)] border border-[hsl(220,100%,50%,0.4)] px-3 md:px-4 py-1.5 font-brand text-xl md:text-2xl font-extrabold text-white shrink-0"
          style={{ textShadow: '0 0 10px hsl(220 100% 50%)' }}
        >
          {me.score}
        </div>
      </div>

      {/* VS Divider */}
      <div className="flex flex-col items-center px-1 md:px-3 shrink-0">
        <Swords className="w-5 h-5 md:w-6 md:h-6 text-[hsl(25,100%,50%)]" style={{ filter: 'drop-shadow(0 0 6px hsl(25 100% 50%))' }} />
        <span className="text-xs font-bold text-[hsl(25,100%,50%)] mt-1">VS</span>
      </div>

      {/* Opponent */}
      <div className="flex items-center gap-2 md:gap-3 flex-1 min-w-0 justify-end">
        <div
          className="rounded-lg bg-[hsl(25,100%,50%,0.2)] border border-[hsl(25,100%,50%,0.4)] px-3 md:px-4 py-1.5 font-brand text-xl md:text-2xl font-extrabold text-white shrink-0"
          style={{ textShadow: '0 0 10px hsl(25 100% 50%)' }}
        >
          {opponent.score}
        </div>
        <div className="text-right min-w-0 flex-1">
          <div className="flex items-center gap-1.5 justify-end">
            <span 
              className="text-sm md:text-base font-bold text-white truncate block"
              style={{ maxWidth: '120px' }}
              title={opponent.name}
            >
              {opponent.name}
            </span>
            <PlayerRankIcon tier={opponent.tier || 'bronce'} />
          </div>
          <div className="text-xs text-[hsl(25,100%,70%)] font-semibold flex items-center gap-1 justify-end">
            <span className="uppercase">Rival</span>
            {opponent.elo && <span className="opacity-70">• {opponent.elo} ELO</span>}
          </div>
        </div>
        <span className={`fi fi-${opponent.flag?.toLowerCase()} h-6 w-8 rounded shadow-md shrink-0`}></span>
      </div>
    </div>
  );
};

export default ScoreBoard;
