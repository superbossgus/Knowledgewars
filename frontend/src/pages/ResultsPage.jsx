import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { EloBadge } from '../components/custom/EloBadge';
import { fireConfetti } from '../lib/confetti';
import { Trophy, TrendingUp, TrendingDown, Home, Swords, Shield, RotateCcw, Pencil, Check } from 'lucide-react';
import { toast } from 'sonner';
import api from '../lib/api';

export default function ResultsPage() {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  
  const matchData = location.state?.matchData;
  const [showRematchDialog, setShowRematchDialog] = useState(false);
  const [rematchTopic, setRematchTopic] = useState('');
  const [useNewTopic, setUseNewTopic] = useState(false);
  const [sendingRematch, setSendingRematch] = useState(false);

  const userId = localStorage.getItem('user') && JSON.parse(localStorage.getItem('user')).id;

  useEffect(() => {
    if (matchData && matchData.winner_id) {
      if (matchData.winner_id === userId) {
        setTimeout(() => fireConfetti(), 500);
      }
    }
  }, [matchData, userId]);

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

  const isWinner = matchData.winner_id === userId;
  const isDraw = !matchData.winner_id;
  const myScore = matchData.score_a;
  const opponentScore = matchData.score_b;
  const eloDelta = matchData.elo_delta_a;
  const originalTopic = matchData.topic || '';

  // Determine opponent info
  const isPlayerA = matchData.player_a_id === userId;
  const opponentId = isPlayerA ? matchData.player_b_id : matchData.player_a_id;
  const opponentName = isPlayerA ? matchData.player_b_name : matchData.player_a_name;

  const handleRematchClick = () => {
    setRematchTopic(originalTopic);
    setUseNewTopic(false);
    setShowRematchDialog(true);
  };

  const handleSendRematch = async () => {
    const topic = useNewTopic ? rematchTopic.trim() : originalTopic;
    if (!topic) {
      toast.error('Escribe un tema para la revancha');
      return;
    }

    setSendingRematch(true);
    try {
      await api.post('/api/matches/create', {
        opponent_id: opponentId,
        topic: topic,
        language: 'es',
        is_rematch: true
      });
      toast.success(`Solicitud de revancha enviada a ${opponentName}. Esperando respuesta...`);
      setShowRematchDialog(false);
      navigate('/home');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al enviar la revancha');
    } finally {
      setSendingRematch(false);
    }
  };

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
              <div className="text-sm text-[hsl(25,100%,70%)] font-bold">{opponentName || 'RIVAL'}</div>
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
              data-testid="result-home-button"
            >
              <Home className="w-5 h-5 mr-2 inline" />
              {t('results.back_home')}
            </button>
            <button
              onClick={handleRematchClick}
              className="btn-primary px-8 py-4 text-lg"
              data-testid="result-rematch-button"
            >
              <RotateCcw className="w-5 h-5 mr-2 inline" />
              Revancha
            </button>
          </motion.div>
        </div>
      </motion.div>

      {/* Rematch Dialog */}
      <AnimatePresence>
        {showRematchDialog && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-card/95 border-2 border-[hsl(45,92%,48%,0.5)] rounded-2xl p-6 max-w-md w-full backdrop-blur-xl"
              style={{ boxShadow: '0 0 40px hsl(45 92% 48% / 0.2)' }}
              data-testid="rematch-dialog"
            >
              <div className="flex items-center gap-3 mb-5">
                <RotateCcw className="w-7 h-7 text-[hsl(45,92%,48%)]" style={{ filter: 'drop-shadow(0 0 6px hsl(45 92% 48%))' }} />
                <h3 className="text-xl font-bold text-white font-brand">Revancha vs {opponentName}</h3>
              </div>

              <p className="text-sm text-gray-300 mb-5">
                Elige el tema para la revancha. Se descontará 1 crédito a cada jugador.
              </p>

              {/* Same topic option */}
              <button
                onClick={() => { setUseNewTopic(false); setRematchTopic(originalTopic); }}
                className={`w-full mb-3 p-4 rounded-xl border-2 text-left transition-all ${
                  !useNewTopic 
                    ? 'border-[hsl(45,92%,48%)] bg-[hsl(45,92%,48%,0.1)]' 
                    : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                }`}
                data-testid="rematch-same-topic"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-bold text-white text-sm mb-1">Mismo tema</div>
                    <div className="text-[hsl(45,92%,48%)] text-sm font-semibold">{originalTopic}</div>
                  </div>
                  {!useNewTopic && <Check className="w-5 h-5 text-[hsl(45,92%,48%)]" />}
                </div>
              </button>

              {/* New topic option */}
              <button
                onClick={() => { setUseNewTopic(true); setRematchTopic(''); }}
                className={`w-full mb-3 p-4 rounded-xl border-2 text-left transition-all ${
                  useNewTopic 
                    ? 'border-[hsl(220,100%,50%)] bg-[hsl(220,100%,50%,0.1)]' 
                    : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                }`}
                data-testid="rematch-new-topic"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-bold text-white text-sm mb-1">Nuevo tema</div>
                    <div className="text-gray-400 text-sm">Escribe un tema diferente</div>
                  </div>
                  <Pencil className="w-5 h-5 text-gray-400" />
                </div>
              </button>

              {/* New topic input */}
              <AnimatePresence>
                {useNewTopic && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden mb-4"
                  >
                    <input
                      type="text"
                      value={rematchTopic}
                      onChange={(e) => setRematchTopic(e.target.value)}
                      placeholder="Ej: Historia de México, Fútbol, Ciencia..."
                      className="w-full px-4 py-3 rounded-xl bg-gray-800/80 border-2 border-[hsl(220,100%,50%,0.3)] text-white placeholder-gray-500 focus:border-[hsl(220,100%,50%)] focus:outline-none transition-colors"
                      autoFocus
                      data-testid="rematch-topic-input"
                    />
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Action buttons */}
              <div className="flex gap-3 mt-2">
                <button
                  onClick={() => setShowRematchDialog(false)}
                  className="flex-1 btn-secondary-glass py-3 font-semibold"
                  data-testid="rematch-cancel"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSendRematch}
                  disabled={sendingRematch || (useNewTopic && !rematchTopic.trim())}
                  className="flex-1 btn-primary py-3 font-semibold disabled:opacity-50"
                  data-testid="rematch-send"
                >
                  {sendingRematch ? 'Enviando...' : 'Enviar Revancha'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
