import React, { useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { EloBadge } from '../components/custom/EloBadge';
import { fireConfetti } from '../lib/confetti';
import { Trophy, TrendingUp, TrendingDown, Home, Swords, Shield } from 'lucide-react';

export default function ResultsPage() {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  
  const matchData = location.state?.matchData;

  useEffect(() => {
    if (matchData && matchData.winner_id) {
      const userId = localStorage.getItem('user') && JSON.parse(localStorage.getItem('user')).id;
      if (matchData.winner_id === userId) {
        setTimeout(() => fireConfetti(), 500);
      }
    }
  }, [matchData]);

  if (!matchData) {
    return (
      <div className="min-h-screen flex items-center justify-center relative z-10">
        <div className="text-center">
          <p className="mb-4 text-white font-medium">Loading results...</p>
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
  const myScore = matchData.score_a;
  const opponentScore = matchData.score_b;
  const eloDelta = matchData.elo_delta_a;

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative z-10">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-2xl"
      >
        {/* Result Card */}
        <div 
          className="bg-card/60 backdrop-blur-xl border-2 rounded-3xl p-8 md:p-12 text-center"
          style={{ 
            borderColor: isWinner ? 'hsl(45, 92%, 48%)' : isDraw ? 'hsl(220, 100%, 50%)' : 'hsl(0, 100%, 55%)',
            boxShadow: isWinner 
              ? '0 0 50px hsl(45 92% 48% / 0.3)' 
              : isDraw 
                ? '0 0 50px hsl(220 100% 50% / 0.2)' 
                : '0 0 50px hsl(0 100% 55% / 0.2)'
          }}
        >
          {/* Result Icon */}
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring' }}
            className="mb-6"
          >
            {isWinner ? (
              <Trophy 
                className="w-24 h-24 mx-auto text-[hsl(45,92%,48%)]" 
                style={{ filter: 'drop-shadow(0 0 20px hsl(45 92% 48%))' }}
              />
            ) : isDraw ? (
              <Shield 
                className="w-24 h-24 mx-auto text-[hsl(220,100%,50%)]" 
                style={{ filter: 'drop-shadow(0 0 15px hsl(220 100% 50%))' }}
              />
            ) : (
              <Swords 
                className="w-24 h-24 mx-auto text-[hsl(25,100%,50%)]" 
                style={{ filter: 'drop-shadow(0 0 15px hsl(25 100% 50%))' }}
              />
            )}
          </motion.div>

          {/* Result Title */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="text-4xl md:text-5xl font-extrabold font-brand mb-4"
            style={{ 
              color: isWinner ? 'hsl(45, 92%, 48%)' : isDraw ? 'white' : 'hsl(25, 100%, 50%)',
              textShadow: isWinner 
                ? '0 0 20px hsl(45 92% 48%)' 
                : isDraw 
                  ? '0 0 15px hsl(220 100% 50%)' 
                  : '0 0 15px hsl(25 100% 50%)'
            }}
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
              <div 
                className="text-5xl font-extrabold font-brand mb-1 text-[hsl(220,100%,50%)]" 
                style={{ textShadow: '0 0 15px hsl(220 100% 50%)' }}
              >
                {myScore}
              </div>
              <div className="text-sm text-[hsl(220,100%,70%)] font-bold">YOU</div>
            </div>
            <div className="text-3xl font-bold text-muted-foreground">VS</div>
            <div className="text-center">
              <div 
                className="text-5xl font-extrabold font-brand mb-1 text-[hsl(25,100%,50%)]" 
                style={{ textShadow: '0 0 15px hsl(25 100% 50%)' }}
              >
                {opponentScore}
              </div>
              <div className="text-sm text-[hsl(25,100%,70%)] font-bold">RIVAL</div>
            </div>
          </motion.div>

          {/* ELO Change */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="inline-flex items-center gap-3 px-6 py-4 rounded-xl bg-muted/30 border-2 mb-8"
            style={{ 
              borderColor: eloDelta > 0 ? 'hsl(140, 100%, 45%, 0.5)' : eloDelta < 0 ? 'hsl(0, 100%, 55%, 0.5)' : 'hsl(220, 100%, 50%, 0.3)'
            }}
            data-testid="result-elo-delta"
          >
            {eloDelta > 0 ? (
              <TrendingUp className="w-6 h-6 text-[hsl(140,100%,50%)]" style={{ filter: 'drop-shadow(0 0 6px hsl(140 100% 50%))' }} />
            ) : eloDelta < 0 ? (
              <TrendingDown className="w-6 h-6 text-[hsl(0,100%,60%)]" style={{ filter: 'drop-shadow(0 0 6px hsl(0 100% 60%))' }} />
            ) : null}
            <span className="font-bold text-white">
              {t('results.elo_change')}:
            </span>
            <span 
              className={`font-extrabold font-brand text-xl ${
                eloDelta > 0 ? 'text-[hsl(140,100%,50%)]' : eloDelta < 0 ? 'text-[hsl(0,100%,60%)]' : 'text-muted-foreground'
              }`}
              style={{ textShadow: eloDelta !== 0 ? `0 0 10px ${eloDelta > 0 ? 'hsl(140 100% 50%)' : 'hsl(0 100% 60%)'}` : 'none' }}
            >
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
              className="btn-secondary-glass px-8 py-4 text-lg"
            >
              <Home className="w-5 h-5 mr-2 inline" />
              {t('results.back_home')}
            </button>
            <button
              onClick={() => navigate('/lobby')}
              className="btn-primary px-8 py-4 text-lg"
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
