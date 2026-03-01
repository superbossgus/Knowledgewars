import React from 'react';
import { Trophy, Shield, Award, Crown, Gem, Zap } from 'lucide-react';

const LEAGUE_MAP = {
  bronce: { 
    color: '28 65% 46%', 
    glow: '0 0 15px hsl(28 65% 46% / 0.5), 0 0 30px hsl(28 65% 46% / 0.3)',
    icon: Shield 
  },
  plata: { 
    color: '214 10% 76%', 
    glow: '0 0 15px hsl(214 10% 76% / 0.6), 0 0 30px hsl(214 10% 76% / 0.4)',
    icon: Award 
  },
  oro: { 
    color: '45 92% 54%', 
    glow: '0 0 15px hsl(45 92% 54% / 0.6), 0 0 30px hsl(45 92% 54% / 0.4)',
    icon: Trophy 
  },
  diamante: { 
    color: '180 100% 55%', 
    glow: '0 0 15px hsl(180 100% 55% / 0.6), 0 0 30px hsl(180 100% 55% / 0.4)',
    icon: Gem 
  },
  maestro: { 
    color: '280 100% 65%', 
    glow: '0 0 15px hsl(280 100% 65% / 0.6), 0 0 30px hsl(280 100% 65% / 0.4)',
    icon: Crown 
  },
  gran_maestro: { 
    color: '85 100% 56%', 
    glow: '0 0 15px hsl(85 100% 56% / 0.7), 0 0 30px hsl(85 100% 56% / 0.5), 0 0 45px hsl(85 100% 56% / 0.3)',
    icon: Zap 
  },
};

export const EloBadge = ({ tier = 'bronce', showIcon = true }) => {
  const config = LEAGUE_MAP[tier] || LEAGUE_MAP.bronce;
  const Icon = config.icon;

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider font-space border-2 relative"
      style={{
        background: `linear-gradient(135deg, hsl(${config.color}) 0%, hsl(${config.color} / 0.7) 100%)`,
        color: 'hsl(220, 25%, 6%)',
        borderColor: `hsl(${config.color})`,
        boxShadow: config.glow,
      }}
      data-testid="elo-badge"
    >
      {/* Inner glow */}
      <div 
        className="absolute inset-0 rounded-lg opacity-30 pointer-events-none"
        style={{
          background: `radial-gradient(circle at center, hsl(${config.color}) 0%, transparent 70%)`,
        }}
      />
      
      {showIcon && <Icon className="w-3.5 h-3.5 relative z-10" style={{ filter: 'drop-shadow(0 0 2px rgba(0,0,0,0.5))' }} />}
      <span className="relative z-10" style={{ textShadow: '0 1px 2px rgba(0,0,0,0.3)' }}>
        {tier.replace('_', ' ')}
      </span>
    </span>
  );
};
