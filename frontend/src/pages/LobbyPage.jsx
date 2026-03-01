import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { useAuthStore } from '../store/store';
import { EloBadge } from '../components/custom/EloBadge';
import api from '../lib/api';
import { toast } from 'sonner';
import { ArrowLeft, Swords, Users } from 'lucide-react';

export default function LobbyPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthStore();
  
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState(location.state?.topic || 'General Knowledge');
  const [loading, setLoading] = useState(true);
  const [challenging, setChallenging] = useState(false);

  useEffect(() => {
    loadOnlineUsers();
    const interval = setInterval(loadOnlineUsers, 5000);
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
      
      toast.success('Challenge sent!');
      navigate(`/match/${response.data.match.id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create match');
    } finally {
      setChallenging(false);
    }
  };

  const handleRandomMatch = async () => {
    if (onlineUsers.length === 0) {
      toast.error('No online users available');
      return;
    }
    
    const randomUser = onlineUsers[Math.floor(Math.random() * onlineUsers.length)];
    await handleChallenge(randomUser.id);
  };

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8">
      <div className="container mx-auto max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <button
            onClick={() => navigate('/home')}
            className="flex items-center gap-2 text-muted-foreground hover:text-foreground mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </button>
          
          <h1 className="text-3xl md:text-4xl font-bold font-space mb-2">Matchmaking</h1>
          <p className="text-muted-foreground">Find an opponent and start dueling!</p>
        </motion.div>

        {/* Topic Selection */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-card/50 backdrop-blur-md border border-white/10 rounded-2xl p-6 mb-6"
        >
          <label className="block text-sm font-medium mb-3">Select Topic</label>
          <select
            value={selectedTopic}
            onChange={(e) => setSelectedTopic(e.target.value)}
            className="w-full px-4 py-3 bg-background/50 border border-input rounded-lg focus:ring-2 focus:ring-ring focus:outline-none"
          >
            <option value="General Knowledge">General Knowledge</option>
            <option value="Sports">Sports</option>
            <option value="History">History</option>
            <option value="Science">Science</option>
            <option value="Technology">Technology</option>
            <option value="Movies/TV">Movies/TV</option>
            <option value="Music">Music</option>
            <option value="Gaming">Gaming</option>
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
            <Swords className="w-5 h-5 mr-2 inline" />
            Challenge Random Opponent
          </button>
        </motion.div>

        {/* Online Users List */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-card/50 backdrop-blur-md border border-white/10 rounded-2xl p-6"
        >
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-primary" />
            Online Players ({onlineUsers.length})
          </h2>

          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Loading players...</div>
          ) : onlineUsers.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No players online right now. Try again later!
            </div>
          ) : (
            <div className="space-y-3">
              {onlineUsers.map((player) => (
                <div
                  key={player.id}
                  className="flex items-center justify-between p-4 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                  data-testid="player-row"
                >
                  <div className="flex items-center gap-3">
                    <span className={`fi fi-${player.country_code?.toLowerCase()} h-6 w-8 rounded`}></span>
                    <div>
                      <div className="font-semibold">{player.display_name}</div>
                      <div className="text-sm text-muted-foreground">
                        {player.elo_rating} ELO
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <EloBadge tier={player.league} showIcon={false} />
                    <button
                      onClick={() => handleChallenge(player.id)}
                      disabled={challenging}
                      className="btn-secondary-glass px-4 py-2 text-sm disabled:opacity-50"
                    >
                      Challenge
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
