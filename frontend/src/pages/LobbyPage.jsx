import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { useAuthStore } from '../store/store';
import { EloBadge } from '../components/custom/EloBadge';
import api from '../lib/api';
import { toast } from 'sonner';
import { ArrowLeft, Swords, Users, Shield, Zap, Search, Sparkles, List, Filter, UserSearch } from 'lucide-react';

// Predefined topics list
const PREDEFINED_TOPICS = [
  'General Knowledge',
  'Sports',
  'History', 
  'Science',
  'Technology',
  'Movies/TV',
  'Music',
  'Gaming',
  'Geography',
  'Art & Literature',
  'Food & Cuisine',
  'Animals & Nature'
];

export default function LobbyPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthStore();
  
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState(location.state?.topic || 'General Knowledge');
  const [customTopic, setCustomTopic] = useState('');
  const [topicMode, setTopicMode] = useState('list'); // 'list' or 'custom'
  const [loading, setLoading] = useState(true);
  const [challenging, setChallenging] = useState(false);
  const [showAllRanks, setShowAllRanks] = useState(false); // Show all ranks or just my tier
  const [searchUsername, setSearchUsername] = useState(''); // Search by username
  const [searchResults, setSearchResults] = useState(null); // Search results

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

  // Get the final topic to use
  const getFinalTopic = () => {
    if (topicMode === 'custom' && customTopic.trim()) {
      return customTopic.trim();
    }
    return selectedTopic;
  };

  useEffect(() => {
    loadOnlineUsers();
    const interval = setInterval(loadOnlineUsers, 10000);
    return () => clearInterval(interval);
  }, [showAllRanks]);

  const loadOnlineUsers = async () => {
    try {
      const endpoint = showAllRanks ? '/api/users/online?all_ranks=true' : '/api/users/online';
      const response = await api.get(endpoint);
      setOnlineUsers(response.data.users || []);
    } catch (error) {
      console.error('Failed to load online users');
    } finally {
      setLoading(false);
    }
  };

  // Search for a specific user by username
  const handleSearchUser = async () => {
    if (!searchUsername.trim()) {
      setSearchResults(null);
      return;
    }
    
    try {
      const response = await api.get(`/api/users/search?username=${encodeURIComponent(searchUsername.trim())}`);
      setSearchResults(response.data.users || []);
    } catch (error) {
      console.error('Failed to search users');
      setSearchResults([]);
    }
  };

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchUsername.trim()) {
        handleSearchUser();
      } else {
        setSearchResults(null);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchUsername]);

  const handleChallenge = async (opponentId) => {
    const finalTopic = getFinalTopic();
    
    if (!finalTopic) {
      toast.error(t('lobby.enter_topic'));
      return;
    }
    
    setChallenging(true);
    try {
      const response = await api.post('/api/matches/create', {
        opponent_id: opponentId,
        topic: finalTopic,
        language: user?.language || 'es'
      });
      
      toast.success(`${t('lobby.challenge_sent')} ${t('lobby.challenge_topic')}: ${finalTopic}`);
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
    
    const finalTopic = getFinalTopic();
    if (!finalTopic) {
      toast.error(t('lobby.enter_topic'));
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
              <span className="text-xs text-white/70">{t('lobby.your_tier')}:</span>
              <EloBadge tier={user?.rank_tier || user?.league || 'bronce'} rankName={user?.rank_name} showLabel={true} />
            </div>
          </div>
          <p className="text-sm text-white/60 mt-2 font-medium">{t('lobby.matchmaking_tier')}</p>
        </motion.div>

        {/* Topic Selection */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-2xl p-6 mb-6"
          style={{ boxShadow: '0 0 20px hsl(220 100% 50% / 0.1)' }}
        >
          <label className="block text-sm font-bold mb-4 text-white">{t('lobby.select_topic')}</label>
          
          {/* Topic Mode Toggle */}
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setTopicMode('list')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-bold transition-all ${
                topicMode === 'list' 
                  ? 'bg-[hsl(220,100%,50%)] text-white' 
                  : 'bg-muted/30 text-muted-foreground hover:bg-muted/50'
              }`}
            >
              <List className="w-4 h-4" />
              {t('lobby.from_list')}
            </button>
            <button
              onClick={() => setTopicMode('custom')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-bold transition-all ${
                topicMode === 'custom' 
                  ? 'bg-[hsl(25,100%,50%)] text-white' 
                  : 'bg-muted/30 text-muted-foreground hover:bg-muted/50'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              {t('lobby.custom_topic')}
            </button>
          </div>
          
          {/* Topic Input based on mode */}
          {topicMode === 'list' ? (
            <select
              value={selectedTopic}
              onChange={(e) => setSelectedTopic(e.target.value)}
              className="w-full px-4 py-3 bg-background/80 border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl focus:ring-2 focus:ring-[hsl(220,100%,50%)] focus:border-[hsl(220,100%,50%)] focus:outline-none text-white font-medium transition-all"
            >
              {PREDEFINED_TOPICS.map(topic => (
                <option key={topic} value={topic}>{translateTopic(topic)}</option>
              ))}
            </select>
          ) : (
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <input
                type="text"
                value={customTopic}
                onChange={(e) => setCustomTopic(e.target.value)}
                placeholder={t('lobby.custom_placeholder')}
                maxLength={100}
                className="w-full pl-12 pr-4 py-3 bg-background/80 border-2 border-[hsl(25,100%,50%,0.3)] rounded-xl focus:ring-2 focus:ring-[hsl(25,100%,50%)] focus:border-[hsl(25,100%,50%)] focus:outline-none text-white font-medium transition-all placeholder:text-muted-foreground"
              />
              {customTopic && (
                <div className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                  {customTopic.length}/100
                </div>
              )}
            </div>
          )}
          
          {/* Topic examples for custom mode */}
          {topicMode === 'custom' && (
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="text-xs text-muted-foreground">{t('lobby.examples')}:</span>
              {['Michael Jackson', 'Harry Potter', 'Copa Mundial', 'Marvel', 'Taylor Swift'].map(example => (
                <button
                  key={example}
                  onClick={() => setCustomTopic(example)}
                  className="text-xs px-2 py-1 rounded-lg bg-muted/30 hover:bg-[hsl(25,100%,50%,0.2)] text-[hsl(25,100%,70%)] transition-all"
                >
                  {example}
                </button>
              ))}
            </div>
          )}
          
          {/* Show selected topic */}
          <div className="mt-4 p-4 rounded-xl bg-[hsl(25,100%,50%,0.15)] border-2 border-[hsl(25,100%,50%,0.4)]">
            <span className="text-base text-white font-medium">{t('lobby.playing_topic')}: </span>
            <span className="text-lg font-extrabold text-[hsl(25,100%,60%)]" style={{ textShadow: '0 0 10px hsl(25 100% 50% / 0.5)' }}>
              {topicMode === 'custom' && customTopic ? customTopic : translateTopic(selectedTopic)}
            </span>
          </div>
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
          {/* Header with title and controls */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
            <h2 className="text-xl font-bold flex items-center gap-2 text-white">
              <Users className="w-6 h-6 text-[hsl(220,100%,50%)]" style={{ filter: 'drop-shadow(0 0 6px hsl(220 100% 50%))' }} />
              {t('lobby.online_players')} ({searchResults ? searchResults.length : onlineUsers.length})
            </h2>
            
            {/* Toggle for all ranks */}
            <button
              onClick={() => setShowAllRanks(!showAllRanks)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-all ${
                showAllRanks 
                  ? 'bg-[hsl(25,100%,50%)] text-white' 
                  : 'bg-muted/30 text-muted-foreground hover:bg-muted/50 border border-[hsl(220,100%,50%,0.3)]'
              }`}
            >
              <Filter className="w-4 h-4" />
              {showAllRanks ? t('lobby.all_ranks') : t('lobby.my_rank_only')}
            </button>
          </div>
          
          {/* Search by username */}
          <div className="mb-4">
            <div className="relative">
              <UserSearch className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <input
                type="text"
                value={searchUsername}
                onChange={(e) => setSearchUsername(e.target.value)}
                placeholder={t('lobby.search_player')}
                className="w-full pl-12 pr-4 py-3 bg-background/80 border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl focus:ring-2 focus:ring-[hsl(220,100%,50%)] focus:border-[hsl(220,100%,50%)] focus:outline-none text-white font-medium transition-all placeholder:text-muted-foreground"
              />
              {searchUsername && (
                <button
                  onClick={() => setSearchUsername('')}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white transition-colors"
                >
                  ✕
                </button>
              )}
            </div>
            {searchUsername && searchResults !== null && (
              <div className="mt-2 text-sm text-white/70 font-medium">
                {searchResults.length > 0 
                  ? t('lobby.search_found', { count: searchResults.length })
                  : t('lobby.search_not_found')
                }
              </div>
            )}
          </div>
          
          {/* Info message about rank filter */}
          {!showAllRanks && !searchUsername && (
            <div className="mb-4 p-4 rounded-xl bg-[hsl(220,100%,50%,0.15)] border-2 border-[hsl(220,100%,50%,0.3)]">
              <Filter className="w-5 h-5 inline mr-2 text-[hsl(220,100%,70%)]" />
              <span className="text-base font-semibold text-white">{t('lobby.matchmaking_tier')}</span>
            </div>
          )}
          
          {showAllRanks && !searchUsername && (
            <div className="mb-4 p-4 rounded-xl bg-[hsl(25,100%,50%,0.15)] border-2 border-[hsl(25,100%,50%,0.3)]">
              <Sparkles className="w-5 h-5 inline mr-2 text-[hsl(25,100%,60%)]" />
              <span className="text-base font-semibold text-white">{t('lobby.friendly_match_info')}</span>
            </div>
          )}

          {/* Players list */}
          {loading ? (
            <div className="text-center py-8 text-white/70 font-medium">{t('common.loading')}</div>
          ) : (searchResults !== null ? searchResults : onlineUsers).length === 0 ? (
            <div className="text-center py-8 text-white/70 font-medium text-lg">
              {searchUsername ? t('lobby.search_not_found') : t('lobby.no_online')}
            </div>
          ) : (
            <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
              {(searchResults !== null ? searchResults : onlineUsers).map((player) => (
                <div
                  key={player.id}
                  className="flex items-center justify-between p-4 rounded-xl bg-muted/30 hover:bg-[hsl(220,100%,50%,0.1)] border-2 border-transparent hover:border-[hsl(220,100%,50%,0.3)] transition-all"
                  data-testid="player-row"
                >
                  <div className="flex items-center gap-4">
                    <span className={`fi fi-${player.country_code?.toLowerCase()} h-8 w-10 rounded shadow-lg`}></span>
                    <div>
                      <div className="font-extrabold text-white text-xl md:text-2xl" style={{ textShadow: '0 0 10px rgba(255,255,255,0.2)' }}>
                        {player.display_name}
                      </div>
                      <div className="text-base text-[hsl(45,92%,55%)] font-bold">
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
