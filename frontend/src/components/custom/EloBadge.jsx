import React from 'react';
import { Shield, Award, Star, Diamond, Crown, Gem, Zap, Trophy, Brain } from 'lucide-react';

// Official league colors from brand manual with new tiers
const leagueConfig = {
  bronce: {
    color: 'hsl(28, 65%, 46%)',
    bg: 'hsl(28, 65%, 46%, 0.2)',
    border: 'hsl(28, 65%, 46%, 0.5)',
    icon: Shield,
    label: 'Bronce'
  },
  plata: {
    color: 'hsl(214, 10%, 76%)',
    bg: 'hsl(214, 10%, 76%, 0.2)',
    border: 'hsl(214, 10%, 76%, 0.5)',
    icon: Award,
    label: 'Plata'
  },
  oro: {
    color: 'hsl(45, 92%, 48%)', // Oro Escudo #F2B705
    bg: 'hsl(45, 92%, 48%, 0.2)',
    border: 'hsl(45, 92%, 48%, 0.5)',
    icon: Star,
    label: 'Oro'
  },
  platino: {
    color: 'hsl(185, 60%, 55%)',
    bg: 'hsl(185, 60%, 55%, 0.2)',
    border: 'hsl(185, 60%, 55%, 0.5)',
    icon: Zap,
    label: 'Platino'
  },
  diamante: {
    color: 'hsl(200, 100%, 55%)',
    bg: 'hsl(200, 100%, 55%, 0.2)',
    border: 'hsl(200, 100%, 55%, 0.5)',
    icon: Diamond,
    label: 'Diamante'
  },
  maestro: {
    color: 'hsl(280, 80%, 60%)', // Purple
    bg: 'hsl(280, 80%, 60%, 0.2)',
    border: 'hsl(280, 80%, 60%, 0.5)',
    icon: Crown,
    label: 'Maestro'
  },
  campeon: {
    color: 'hsl(340, 80%, 55%)', // Red/Pink
    bg: 'hsl(340, 80%, 55%, 0.2)',
    border: 'hsl(340, 80%, 55%, 0.5)',
    icon: Trophy,
    label: 'Campeón'
  },
  gran_maestro: {
    color: 'hsl(25, 100%, 55%)', // Naranja Guerra variant
    bg: 'hsl(25, 100%, 55%, 0.2)',
    border: 'hsl(25, 100%, 55%, 0.5)',
    icon: Gem,
    label: 'Gran Maestro'
  },
  genio: {
    color: 'hsl(50, 100%, 50%)', // Golden
    bg: 'linear-gradient(135deg, hsl(45, 92%, 48%, 0.3), hsl(25, 100%, 50%, 0.3))',
    border: 'hsl(50, 100%, 50%, 0.8)',
    icon: Brain,
    label: 'Genio'
  }
};

export const EloBadge = ({ tier = 'bronce', rankName = null, elo = null, showLabel = true, showElo = false }) => {
  const config = leagueConfig[tier] || leagueConfig.bronce;
  const Icon = config.icon;
  
  // Use full rank name if provided, otherwise use tier label
  const displayLabel = rankName || config.label;
  
  return (
    <span
      className="league-badge"
      style={{
        background: config.bg,
        borderColor: config.border,
        borderWidth: '2px',
        borderStyle: 'solid',
        color: config.color,
        boxShadow: `0 0 15px ${config.color.replace(')', ', 0.3)')}`
      }}
      data-testid="elo-badge"
    >
      <Icon className="w-4 h-4" style={{ filter: `drop-shadow(0 0 4px ${config.color})` }} />
      {showLabel && <span className="font-semibold">{displayLabel}</span>}
      {showElo && elo !== null && <span className="ml-1 text-xs opacity-80">({elo})</span>}
    </span>
  );
};

// New component to show rank with ELO and progress
export const RankDisplay = ({ tier, rankName, elo, progress }) => {
  const config = leagueConfig[tier] || leagueConfig.bronce;
  const Icon = config.icon;
  
  return (
    <div className="flex flex-col items-center gap-2">
      <div 
        className="flex items-center gap-2 px-4 py-2 rounded-xl"
        style={{
          background: config.bg,
          borderColor: config.border,
          borderWidth: '2px',
          borderStyle: 'solid',
          boxShadow: `0 0 20px ${config.color.replace(')', ', 0.3)')}`
        }}
      >
        <Icon className="w-6 h-6" style={{ color: config.color, filter: `drop-shadow(0 0 6px ${config.color})` }} />
        <div className="flex flex-col">
          <span className="font-bold text-white">{rankName}</span>
          <span className="text-sm" style={{ color: config.color }}>{elo} ELO</span>
        </div>
      </div>
      
      {progress && progress.next_rank && (
        <div className="w-full max-w-[200px]">
          <div className="flex justify-between text-xs text-muted-foreground mb-1">
            <span>{progress.current_rank}</span>
            <span>{progress.next_rank}</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div 
              className="h-full transition-all duration-500"
              style={{ 
                width: `${progress.progress}%`,
                background: `linear-gradient(90deg, ${config.color}, ${config.color.replace(')', ', 0.7)')})`
              }}
            />
          </div>
          <div className="text-xs text-center mt-1 text-muted-foreground">
            {progress.points_to_next} puntos para subir
          </div>
        </div>
      )}
    </div>
  );
};

export default EloBadge;
