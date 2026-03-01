import React, { useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { EloBadge } from '../components/custom/EloBadge';
import { fireConfetti } from '../lib/confetti';
import { Trophy, TrendingUp, TrendingDown, Home, Swords } from 'lucide-react';

export default function ResultsPage() {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  
  const matchData = location.state?.matchData;

  useEffect(() => {
    if (matchData && matchData.winner_id) {
      // Fire confetti if we won
      const userId = localStorage.getItem('user') && JSON.parse(localStorage.getItem('user')).id;
      if (matchData.winner_id === userId) {
        setTimeout(() => fireConfetti(), 500);
      }
    }
  }, [matchData]);

  if (!matchData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="mb-4">Loading results...</p>
          <button onClick={() => navigate('/home')} className="btn-primary">
            {t('results.back_home')}
          </button>
        </div>
      </div>
    );
  }

  const userId = localStorage.getItem('user') && JSON.parse(localStorage.getItem('user')).id;
  const isWinner = matchData.winner_id === userId;
  const isDraw = !matchData.winner_id;
  const myScore = matchData.score_a; // Simplified, should check player
  const opponentScore = matchData.score_b;
  const eloDelta = matchData.elo_delta_a;

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-2xl"
      >
        {/* Result Card */}
        <div className="bg-card/50 backdrop-blur-md border border-white/10 rounded-3xl p-8 md:p-12 text-center">
          {/* Result Icon */}
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring' }}
            className="mb-6"
          >
            {isWinner ? (
              <Trophy className="w-20 h-20 mx-auto text-accent" />
            ) : isDraw ? (
              <div className="text-6xl">🤝</div>
            ) : (
              <div className="text-6xl">💪</div>
            )}
          </motion.div>

          {/* Result Title */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="text-4xl md:text-5xl font-bold font-space mb-4"
          >
            {isWinner ? t('results.victory') : isDraw ? t('results.draw') : t('results.defeat')}
          </motion.h1>

          {/* Scores */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="flex items-center justify-center gap-8 mb-8"
          >
            <div className="text-center">
              <div className="text-5xl font-bold font-space mb-1">{myScore}</div>
              <div className="text-sm text-muted-foreground">You</div>
            </div>
            <div className="text-3xl text-muted-foreground">:</div>
            <div className="text-center">
              <div className="text-5xl font-bold font-space mb-1">{opponentScore}</div>
              <div className="text-sm text-muted-foreground">Opponent</div>
            </div>
          </motion.div>

          {/* ELO Change */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-muted/30 mb-8"
            data-testid="result-elo-delta"
          >
            {eloDelta > 0 ? (
              <TrendingUp className="w-5 h-5 text-emerald-400" />
            ) : eloDelta < 0 ? (
              <TrendingDown className="w-5 h-5 text-red-400" />
            ) : null}
            <span className="font-semibold">
              {t('results.elo_change')}:
            </span>
            <span className={`font-bold font-space text-lg ${
              eloDelta > 0 ? 'text-emerald-400' : eloDelta < 0 ? 'text-red-400' : 'text-muted-foreground'
            }`}>
              {eloDelta > 0 ? '+' : ''}{eloDelta}
            </span>
          </motion.div>

          {/* Actions */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <button
              onClick={() => navigate('/home')}
              className="btn-secondary-glass px-8 py-3"
            >
              <Home className="w-5 h-5 mr-2 inline" />
              {t('results.back_home')}
            </button>
            <button
              onClick={() => navigate('/lobby')}
              className="btn-primary px-8 py-3"
              data-testid="result-rematch-button"
            >
              <Swords className="w-5 h-5 mr-2 inline" />
              Play Again
            </button>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
