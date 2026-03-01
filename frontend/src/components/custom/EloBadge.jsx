import React from 'react';
import { Trophy, Shield, Award, Crown, Gem } from 'lucide-react';

const LEAGUE_MAP = {
  bronce: { color: '28 65% 46%', icon: Shield },
  plata: { color: '214 10% 76%', icon: Award },
  oro: { color: '45 92% 54%', icon: Trophy },
  diamante: { color: '173 85% 55%', icon: Gem },
  maestro: { color: '197 100% 54%', icon: Crown },
  gran_maestro: { color: '96 86% 56%', icon: Crown },
};

export const EloBadge = ({ tier = 'bronce', showIcon = true }) => {
  const config = LEAGUE_MAP[tier] || LEAGUE_MAP.bronce;
  const Icon = config.icon;

  return (
    <span
      className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold uppercase tracking-wide"
      style={{
        background: `hsl(${config.color})`,
        color: 'hsl(222, 30%, 8%)',
      }}
      data-testid="elo-badge"
    >
      {showIcon && <Icon className="w-3 h-3" />}
      {tier.replace('_', ' ')}
    </span>
  );
};
