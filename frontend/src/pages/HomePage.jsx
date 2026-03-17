import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { useAuthStore } from '../store/store';
import { EloBadge } from '../components/custom/EloBadge';
import api from '../lib/api';
import { toast } from 'sonner';
import { Swords, Trophy, Flame, LogOut, Shield, Zap, Coins, AlertTriangle, ShoppingCart } from 'lucide-react';

export default function HomePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  
  const [topTopics, setTopTopics] = useState([]);
  const [credits, setCredits] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [topicsRes, creditsRes] = await Promise.all([
        api.get('/api/topics/top'),
        api.get('/api/users/credits')
      ]);
      
      setTopTopics(topicsRes.data.topics || []);
      setCredits(creditsRes.data);
    } catch (error) {
      // Fallback for users without credits field
      setTopTopics([]);
      setCredits({ games_remaining: 0, low_credits_warning: true, no_credits: true });
    } finally {
      setLoading(false);
    }
  };

  const handlePlayRandom = async () => {
    // Check if user has credits (but don't deduct yet)
    if (credits?.no_credits || credits?.games_remaining <= 0) {
      toast.error('¡No tienes partidas disponibles! Compra más en la tienda.');
      navigate('/store');
      return;
    }
    
    // Show warning if low on credits
    if (credits?.games_remaining <= 5) {
      toast.warning(`¡Te quedan solo ${credits.games_remaining} partidas!`);
    }
    
    // Navigate to lobby - credit will be deducted when match actually starts
    navigate('/lobby');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[hsl(220,100%,50%)] mx-auto mb-4"></div>
          <p className="text-white">{t('common.loading')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8 relative z-10">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-8"
        >
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Shield className="w-8 h-8 text-[hsl(220,100%,50%)]" style={{ filter: 'drop-shadow(0 0 8px hsl(220 100% 50%))' }} />
              <div>
                <h1 className="text-2xl md:text-3xl font-extrabold font-brand text-white">
                  KNOWLEDGE <span className="text-[hsl(25,100%,50%)]">WARS</span>
                </h1>
                <p className="text-sm text-muted-foreground">{t('common.welcome_back')}, <span className="text-[hsl(220,100%,70%)] font-semibold">{user?.display_name}</span>!</p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <EloBadge tier={user?.league || 'bronce'} />
            <button
              onClick={handleLogout}
              className="p-2 rounded-xl bg-muted/30 hover:bg-muted/50 transition-all border border-[hsl(220,100%,50%,0.2)] hover:border-[hsl(220,100%,50%,0.4)]"
              title={t('auth.logout')}
            >
              <LogOut className="w-5 h-5 text-white" />
            </button>
          </div>
        </motion.div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 md:gap-6">
          {/* Play Random - Main CTA */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 }}
            className="xl:col-span-2 bg-card/60 backdrop-blur-xl border-2 border-[hsl(25,100%,50%,0.3)] rounded-2xl p-6 md:p-8 relative overflow-hidden group"
            style={{ boxShadow: '0 0 30px hsl(25 100% 50% / 0.1)' }}
          >
            <div className="absolute inset-0 bg-gradient-to-br from-[hsl(25,100%,50%,0.1)] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-4">
                <Swords className="w-10 h-10 text-[hsl(25,100%,50%)]" style={{ filter: 'drop-shadow(0 0 10px hsl(25 100% 50%))' }} />
                <h2 className="text-2xl font-bold font-brand text-white">{t('home.play_random')}</h2>
              </div>
              <p className="text-muted-foreground mb-6 text-lg">
                Challenge a random opponent and prove your knowledge!
              </p>
              <button
                onClick={handlePlayRandom}
                className="btn-primary text-lg px-10 py-4 w-full md:w-auto"
                data-testid="play-random-button"
              >
                <Zap className="w-5 h-5 mr-2 inline" />
                {t('common.play')}
              </button>
            </div>
          </motion.div>

          {/* Games Remaining */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className={`bg-card/60 backdrop-blur-xl border-2 rounded-2xl p-6 ${
              credits?.no_credits 
                ? 'border-[hsl(0,100%,50%,0.4)]' 
                : credits?.low_credits_warning 
                  ? 'border-[hsl(45,92%,48%,0.4)]'
                  : 'border-[hsl(220,100%,50%,0.3)]'
            }`}
            style={{ boxShadow: credits?.low_credits_warning ? '0 0 20px hsl(45 92% 48% / 0.2)' : '0 0 20px hsl(220 100% 50% / 0.1)' }}
            data-testid="games-remaining-card"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Coins className="w-6 h-6 text-[hsl(45,92%,48%)]" style={{ filter: 'drop-shadow(0 0 6px hsl(45 92% 48%))' }} />
                <h3 className="font-bold text-white text-lg">Partidas</h3>
              </div>
              {credits?.low_credits_warning && (
                <AlertTriangle className={`w-5 h-5 ${credits?.no_credits ? 'text-[hsl(0,100%,60%)]' : 'text-[hsl(45,92%,48%)]'}`} />
              )}
            </div>
            <div className="text-4xl font-extrabold font-brand mb-3">
              <span className={credits?.no_credits ? 'text-[hsl(0,100%,60%)]' : 'text-[hsl(45,92%,48%)]'} style={{ textShadow: '0 0 10px hsl(45 92% 48% / 0.5)' }}>
                {credits?.games_remaining || 0}
              </span>
            </div>
            {credits?.low_credits_warning && (
              <button
                onClick={() => navigate('/store')}
                className="w-full text-sm py-2 rounded-lg bg-[hsl(25,100%,50%,0.2)] text-[hsl(25,100%,50%)] font-bold hover:bg-[hsl(25,100%,50%,0.3)] transition-colors"
              >
                {credits?.no_credits ? '¡Comprar Partidas!' : '¡Pocas partidas! Comprar más'}
              </button>
            )}
          </motion.div>

          {/* Store Button */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 }}
            className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(25,100%,50%,0.3)] rounded-2xl p-6"
            style={{ boxShadow: '0 0 20px hsl(25 100% 50% / 0.1)' }}
          >
            <div className="flex items-center gap-2 mb-3">
              <ShoppingCart className="w-6 h-6 text-[hsl(25,100%,50%)]" style={{ filter: 'drop-shadow(0 0 6px hsl(25 100% 50%))' }} />
              <h3 className="font-bold text-white text-lg">Tienda</h3>
            </div>
            <p className="text-muted-foreground text-sm mb-4">50 partidas por $99 MXN</p>
            <button
              onClick={() => navigate('/store')}
              className="w-full btn-primary py-3"
            >
              Ir a la Tienda
            </button>
          </motion.div>

          {/* Top Topics */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.4 }}
            className="xl:col-span-2 bg-card/60 backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-2xl p-6"
            style={{ boxShadow: '0 0 20px hsl(220 100% 50% / 0.1)' }}
          >
            <h3 className="font-bold mb-4 flex items-center gap-2 text-white text-lg">
              <Flame className="w-6 h-6 text-[hsl(25,100%,50%)]" style={{ filter: 'drop-shadow(0 0 6px hsl(25 100% 50%))' }} />
              {t('home.top_topics')}
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {topTopics.slice(0, 6).map((topic) => (
                <button
                  key={topic.topic}
                  onClick={() => navigate('/lobby', { state: { topic: topic.topic } })}
                  className="text-left px-4 py-3 rounded-xl bg-muted/30 hover:bg-[hsl(220,100%,50%,0.15)] border border-transparent hover:border-[hsl(220,100%,50%,0.3)] transition-all text-sm font-medium text-white"
                >
                  {topic.topic}
                </button>
              ))}
            </div>
          </motion.div>

          {/* Quick Actions */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5 }}
            className="xl:col-span-2 bg-card/60 backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-2xl p-6"
            style={{ boxShadow: '0 0 20px hsl(220 100% 50% / 0.1)' }}
          >
            <h3 className="font-bold mb-4 text-white text-lg">Acciones Rápidas</h3>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => navigate('/rankings')}
                className="p-5 rounded-xl bg-muted/30 hover:bg-[hsl(220,100%,50%,0.15)] border border-transparent hover:border-[hsl(220,100%,50%,0.3)] transition-all text-center"
              >
                <Trophy className="w-8 h-8 mx-auto mb-2 text-[hsl(220,100%,50%)]" style={{ filter: 'drop-shadow(0 0 6px hsl(220 100% 50%))' }} />
                <span className="text-sm font-bold text-white">Rankings</span>
              </button>
              <button
                onClick={() => navigate('/store')}
                className="p-5 rounded-xl bg-muted/30 hover:bg-[hsl(25,100%,50%,0.15)] border border-transparent hover:border-[hsl(25,100%,50%,0.3)] transition-all text-center"
              >
                <Coins className="w-8 h-8 mx-auto mb-2 text-[hsl(25,100%,50%)]" style={{ filter: 'drop-shadow(0 0 6px hsl(25 100% 50%))' }} />
                <span className="text-sm font-bold text-white">Tienda</span>
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
