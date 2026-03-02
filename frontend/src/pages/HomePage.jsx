import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { useAuthStore } from '../store/store';
import { EloBadge } from '../components/custom/EloBadge';
import api from '../lib/api';
import { toast } from 'sonner';
import { Swords, Trophy, Flame, Crown, LogOut } from 'lucide-react';

export default function HomePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  
  const [topTopics, setTopTopics] = useState([]);
  const [duelsRemaining, setDuelsRemaining] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [topicsRes, duelsRes] = await Promise.all([
        api.get('/api/topics/top'),
        api.get('/api/users/duels/remaining')
      ]);
      
      setTopTopics(topicsRes.data.topics);
      setDuelsRemaining(duelsRes.data);
    } catch (error) {
      toast.error(t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const handlePlayRandom = () => {
    if (duelsRemaining && !duelsRemaining.unlimited && duelsRemaining.remaining === 0) {
      toast.error('No duels remaining. Upgrade to Premium!');
      navigate('/premium');
      return;
    }
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
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p>{t('common.loading')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-8"
        >
          <div>
            <h1 className="text-3xl md:text-4xl font-bold font-space mb-1">
              {t('common.app_name')}
            </h1>
            <p className="text-muted-foreground">Welcome back, {user?.display_name}!</p>
          </div>
          
          <div className="flex items-center gap-3">
            <EloBadge tier={user?.league || 'bronce'} />
            <button
              onClick={handleLogout}
              className="p-2 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
              title={t('auth.logout')}
            >
              <LogOut className="w-5 h-5" />
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
            className="xl:col-span-2 bg-card/50 backdrop-blur-md border border-white/10 rounded-2xl p-6 md:p-8 relative overflow-hidden group"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-4">
                <Swords className="w-8 h-8 text-primary" />
                <h2 className="text-2xl font-bold font-space">{t('home.play_random')}</h2>
              </div>
              <p className="text-muted-foreground mb-6">
                Challenge a random opponent and prove your knowledge!
              </p>
              <button
                onClick={handlePlayRandom}
                className="btn-primary text-lg px-8 py-4 w-full md:w-auto"
                data-testid="play-random-button"
              >
                <Flame className="w-5 h-5 mr-2 inline" />
                {t('common.play')}
              </button>
            </div>
          </motion.div>

          {/* Duels Remaining */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="bg-card/50 backdrop-blur-md border border-white/10 rounded-2xl p-6"
            data-testid="duels-remaining-chip"
          >
            <div className="flex items-center gap-2 mb-2">
              <Trophy className="w-5 h-5 text-accent" />
              <h3 className="font-semibold">{t('home.duels_remaining')}</h3>
            </div>
            <div className="text-3xl font-bold font-space mb-2">
              {duelsRemaining?.unlimited ? (
                <span className="text-primary">{t('home.unlimited')}</span>
              ) : (
                <span>{duelsRemaining?.remaining || 0}</span>
              )}
            </div>
            {!duelsRemaining?.unlimited && (
              <div className="w-full bg-muted/30 rounded-full h-2">
                <div
                  className="bg-primary h-2 rounded-full transition-all"
                  style={{ width: `${((duelsRemaining?.remaining || 0) / (duelsRemaining?.limit || 100)) * 100}%` }}
                />
              </div>
            )}
          </motion.div>

          {/* Premium Status */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 }}
            className="bg-card/50 backdrop-blur-md border border-white/10 rounded-2xl p-6"
            data-testid="premium-status-card"
          >
            <div className="flex items-center gap-2 mb-2">
              <Crown className="w-5 h-5 text-accent" />
              <h3 className="font-semibold">{t('home.premium_status')}</h3>
            </div>
            <div className="mb-4">
              {user?.premium_status ? (
                <span className="inline-flex items-center gap-2 px-3 py-1 rounded-lg bg-accent/20 text-accent text-sm font-semibold">
                  <Crown className="w-4 h-4" />
                  Premium Active
                </span>
              ) : (
                <span className="text-muted-foreground text-sm">Free Plan</span>
              )}
            </div>
            {!user?.premium_status && (
              <button
                onClick={() => navigate('/premium')}
                className="text-sm text-primary hover:underline"
              >
                Upgrade Now →
              </button>
            )}
          </motion.div>

          {/* Top Topics */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.4 }}
            className="xl:col-span-2 bg-card/50 backdrop-blur-md border border-white/10 rounded-2xl p-6"
          >
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Flame className="w-5 h-5 text-accent" />
              {t('home.top_topics')}
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {topTopics.slice(0, 6).map((topic) => (
                <button
                  key={topic.topic}
                  onClick={() => navigate('/lobby', { state: { topic: topic.topic } })}
                  className="text-left px-3 py-2 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors text-sm"
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
            className="xl:col-span-2 bg-card/50 backdrop-blur-md border border-white/10 rounded-2xl p-6"
          >
            <h3 className="font-semibold mb-4">Quick Actions</h3>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => navigate('/rankings')}
                className="p-4 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors text-center"
              >
                <Trophy className="w-6 h-6 mx-auto mb-2 text-primary" />
                <span className="text-sm font-medium">Rankings</span>
              </button>
              <button
                onClick={() => navigate('/profile')}
                className="p-4 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors text-center"
              >
                <Crown className="w-6 h-6 mx-auto mb-2 text-accent" />
                <span className="text-sm font-medium">Profile</span>
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
