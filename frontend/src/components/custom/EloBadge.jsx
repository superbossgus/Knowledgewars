import React from 'react';
import { Shield, Award, Star, Diamond, Crown, Gem } from 'lucide-react';

// Official league colors from brand manual
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
  diamante: {
    color: 'hsl(200, 100%, 55%)',
    bg: 'hsl(200, 100%, 55%, 0.2)',
    border: 'hsl(200, 100%, 55%, 0.5)',
    icon: Diamond,
    label: 'Diamante'
  },
  maestro: {
    color: 'hsl(220, 100%, 60%)', // Azul Energía variant
    bg: 'hsl(220, 100%, 60%, 0.2)',
    border: 'hsl(220, 100%, 60%, 0.5)',
    icon: Crown,
    label: 'Maestro'
  },
  gran_maestro: {
    color: 'hsl(25, 100%, 55%)', // Naranja Guerra variant
    bg: 'hsl(25, 100%, 55%, 0.2)',
    border: 'hsl(25, 100%, 55%, 0.5)',
    icon: Gem,
    label: 'Gran Maestro'
  }
};

export const EloBadge = ({ tier = 'bronce', showLabel = true }) => {
  const config = leagueConfig[tier] || leagueConfig.bronce;
  const Icon = config.icon;
  
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
      {showLabel && <span>{config.label}</span>}
    </span>
  );
};

export default EloBadge;
