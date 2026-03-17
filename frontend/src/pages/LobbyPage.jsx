import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { useAuthStore } from '../store/store';
import { EloBadge } from '../components/custom/EloBadge';
import api from '../lib/api';
import { toast } from 'sonner';
import { ArrowLeft, Swords, Users, Shield, Zap } from 'lucide-react';

export default function LobbyPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthStore();
  
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState(location.state?.topic || 'General Knowledge');
  const [loading, setLoading] = useState(true);
  const [challenging, setChallenging] = useState(false);

  // Change language based on user preference
  useEffect(() => {
    if (user?.language && i18n.language !== user.language) {
      i18n.changeLanguage(user.language);
    }
  }, [user?.language, i18n]);

  // Helper function to translate topic names
  const translateTopic = (topic) => {
    const topicKey = `topics.${topic}`;
    const translated = t(topicKey);
    return translated !== topicKey ? translated : topic;
  };

  useEffect(() => {
    loadOnlineUsers();
    const interval = setInterval(loadOnlineUsers, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadOnlineUsers = async () => {
    try {
      const response = await api.get('/api/users/online');
      setOnlineUsers(response.data.users || []);
    } catch (error) {
      console.error('Failed to load online users');
    } finally {
      setLoading(false);
    }
  };

  const handleChallenge = async (opponentId) => {
    setChallenging(true);
    try {
      const response = await api.post('/api/matches/create', {
        opponent_id: opponentId,
        topic: selectedTopic,
        language: user?.language || 'es'
      });
      
      toast.success(`${t('lobby.challenge_sent')} ${t('lobby.challenge_topic')}: ${translateTopic(selectedTopic)}`);
      setTimeout(() => {
        navigate('/home');
      }, 1500);
    } catch (error) {
      toast.error(error.response?.data?.detail || t('lobby.challenge_failed'));
    } finally {
      setChallenging(false);
    }
  };

  const handleRandomMatch = async () => {
    if (onlineUsers.length === 0) {
      toast.error(t('lobby.no_users'));
      return;
    }
    
    const randomUser = onlineUsers[Math.floor(Math.random() * onlineUsers.length)];
    await handleChallenge(randomUser.id);
  };

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8 relative z-10">
      <div className="container mx-auto max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <button
            onClick={() => navigate('/home')}
            className="flex items-center gap-2 text-[hsl(220,100%,70%)] hover:text-white mb-4 transition-colors font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            {t('lobby.back_home')}
          </button>
          
          <div className="flex items-center gap-3 mb-2">
            <Shield className="w-8 h-8 text-[hsl(220,100%,50%)]" style={{ filter: 'drop-shadow(0 0 8px hsl(220 100% 50%))' }} />
            <h1 className="text-3xl md:text-4xl font-extrabold font-brand text-white">{t('lobby.matchmaking')}</h1>
          </div>
          <div className="flex items-center gap-4">
            <p className="text-[hsl(220,100%,70%)] font-medium">{t('lobby.find_opponent')}</p>
            <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-muted/30 border border-[hsl(220,100%,50%,0.3)]">
              <span className="text-xs text-muted-foreground">{t('lobby.your_tier')}:</span>
              <EloBadge tier={user?.rank_tier || user?.league || 'bronce'} rankName={user?.rank_name} showLabel={true} />
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-2">{t('lobby.matchmaking_tier')}</p>
        </motion.div>

        {/* Topic Selection */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-2xl p-6 mb-6"
          style={{ boxShadow: '0 0 20px hsl(220 100% 50% / 0.1)' }}
        >
          <label className="block text-sm font-bold mb-3 text-white">{t('lobby.select_topic')}</label>
          <select
            value={selectedTopic}
            onChange={(e) => setSelectedTopic(e.target.value)}
            className="w-full px-4 py-3 bg-background/80 border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl focus:ring-2 focus:ring-[hsl(220,100%,50%)] focus:border-[hsl(220,100%,50%)] focus:outline-none text-white font-medium transition-all"
          >
            <option value="General Knowledge">{translateTopic('General Knowledge')}</option>
            <option value="Sports">{translateTopic('Sports')}</option>
            <option value="History">{translateTopic('History')}</option>
            <option value="Science">{translateTopic('Science')}</option>
            <option value="Technology">{translateTopic('Technology')}</option>
            <option value="Movies/TV">{translateTopic('Movies/TV')}</option>
            <option value="Music">{translateTopic('Music')}</option>
            <option value="Gaming">{translateTopic('Gaming')}</option>
          </select>
        </motion.div>

        {/* Random Match Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mb-6"
        >
          <button
            onClick={handleRandomMatch}
            disabled={challenging || onlineUsers.length === 0}
            className="w-full btn-primary py-4 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="matchmaking-random-button"
          >
            <Zap className="w-5 h-5 mr-2 inline" />
            {t('lobby.play_random')}
          </button>
        </motion.div>

        {/* Online Users List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-2xl p-6"
          style={{ boxShadow: '0 0 20px hsl(220 100% 50% / 0.1)' }}
        >
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-white">
            <Users className="w-6 h-6 text-[hsl(220,100%,50%)]" style={{ filter: 'drop-shadow(0 0 6px hsl(220 100% 50%))' }} />
            {t('lobby.online_players')} ({onlineUsers.length})
          </h2>

          {loading ? (
            <div className="text-center py-8 text-muted-foreground">{t('common.loading')}</div>
          ) : onlineUsers.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {t('lobby.no_online')}
            </div>
          ) : (
            <div className="space-y-3">
              {onlineUsers.map((player) => (
                <div
                  key={player.id}
                  className="flex items-center justify-between p-4 rounded-xl bg-muted/30 hover:bg-[hsl(220,100%,50%,0.1)] border border-transparent hover:border-[hsl(220,100%,50%,0.3)] transition-all"
                  data-testid="player-row"
                >
                  <div className="flex items-center gap-3">
                    <span className={`fi fi-${player.country_code?.toLowerCase()} h-6 w-8 rounded shadow-lg`}></span>
                    <div>
                      <div className="font-bold text-white text-lg">{player.display_name}</div>
                      <div className="text-sm text-[hsl(45,92%,48%)] font-semibold">
                        {player.rank_name || player.league?.toUpperCase()} • {player.elo_rating} ELO
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <EloBadge tier={player.league} rankName={player.rank_name} showLabel={false} />
                    <button
                      onClick={() => handleChallenge(player.id)}
                      disabled={challenging}
                      className="btn-secondary-glass px-4 py-2 text-sm disabled:opacity-50"
                    >
                      <Swords className="w-4 h-4 mr-1 inline" />
                      {t('lobby.challenge')}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
