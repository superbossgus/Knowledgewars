import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { EloBadge } from '../components/custom/EloBadge';
import api from '../lib/api';
import { ArrowLeft, Trophy, TrendingUp, Shield } from 'lucide-react';

export default function RankingsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  
  const [rankings, setRankings] = useState([]);
  const [activeTab, setActiveTab] = useState('global');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRankings();
  }, [activeTab]);

  const loadRankings = async () => {
    setLoading(true);
    try {
      const endpoint = activeTab === 'global' ? '/api/leaderboards/global' : '/api/leaderboards/weekly';
      const response = await api.get(endpoint);
      setRankings(response.data.entries || []);
    } catch (error) {
      console.error('Failed to load rankings');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8 relative z-10">
      <div className="container mx-auto max-w-5xl">
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
            Back to Home
          </button>
          
          <div className="flex items-center gap-3 mb-2">
            <Trophy className="w-10 h-10 text-[hsl(45,92%,48%)]" style={{ filter: 'drop-shadow(0 0 10px hsl(45 92% 48%))' }} />
            <h1 className="text-3xl md:text-4xl font-extrabold font-brand text-white">
              {t('rankings.global')}
            </h1>
          </div>
          <p className="text-muted-foreground font-medium">Top players worldwide</p>
        </motion.div>

        {/* Tabs */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="flex gap-2 mb-6"
        >
          <button
            onClick={() => setActiveTab('global')}
            className={`px-6 py-3 rounded-xl font-bold font-brand uppercase tracking-wide transition-all duration-200 ${
              activeTab === 'global' 
                ? 'bg-[hsl(220,100%,50%)] text-white shadow-lg' 
                : 'bg-muted/30 text-muted-foreground hover:bg-muted/50'
            }`}
            style={activeTab === 'global' ? { boxShadow: '0 0 20px hsl(220 100% 50% / 0.5)' } : {}}
            data-testid="leaderboard-tab-global"
          >
            {t('rankings.global')}
          </button>
          <button
            onClick={() => setActiveTab('weekly')}
            className={`px-6 py-3 rounded-xl font-bold font-brand uppercase tracking-wide transition-all duration-200 ${
              activeTab === 'weekly' 
                ? 'bg-[hsl(25,100%,50%)] text-white shadow-lg' 
                : 'bg-muted/30 text-muted-foreground hover:bg-muted/50'
            }`}
            style={activeTab === 'weekly' ? { boxShadow: '0 0 20px hsl(25 100% 50% / 0.5)' } : {}}
            data-testid="leaderboard-tab-weekly"
          >
            {t('rankings.weekly')}
          </button>
        </motion.div>

        {/* Rankings Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-2xl overflow-hidden"
          style={{ boxShadow: '0 0 30px hsl(220 100% 50% / 0.1)' }}
        >
          {loading ? (
            <div className="text-center py-12 text-muted-foreground">Loading rankings...</div>
          ) : rankings.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">No rankings data available</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b-2 border-[hsl(220,100%,50%,0.2)] bg-muted/20">
                    <th className="px-4 py-4 text-left text-sm font-bold text-white">{t('rankings.rank')}</th>
                    <th className="px-4 py-4 text-left text-sm font-bold text-white">{t('rankings.player')}</th>
                    <th className="px-4 py-4 text-center text-sm font-bold text-white">League</th>
                    <th className="px-4 py-4 text-right text-sm font-bold text-white">{t('rankings.elo')}</th>
                    <th className="px-4 py-4 text-right text-sm font-bold text-white">{t('rankings.wins')}</th>
                    <th className="px-4 py-4 text-right text-sm font-bold text-white">{t('rankings.losses')}</th>
                  </tr>
                </thead>
                <tbody>
                  {rankings.map((entry) => (
                    <tr
                      key={entry.user_id}
                      className="border-b border-white/5 hover:bg-[hsl(220,100%,50%,0.08)] transition-colors"
                      data-testid="leaderboard-row"
                    >
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          {entry.rank <= 3 && (
                            <Trophy
                              className={`w-5 h-5 ${
                                entry.rank === 1 ? 'text-[hsl(45,92%,54%)]' :
                                entry.rank === 2 ? 'text-[hsl(214,10%,76%)]' :
                                'text-[hsl(28,65%,46%)]'
                              }`}
                              style={{ filter: entry.rank === 1 ? 'drop-shadow(0 0 6px hsl(45 92% 54%))' : 'none' }}
                            />
                          )}
                          <span className="font-bold font-brand text-white">#{entry.rank}</span>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <span className={`fi fi-${entry.country_code?.toLowerCase()} h-5 w-7 rounded-sm shadow-md`}></span>
                          <span className="font-bold text-white">{entry.display_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-center">
                        <EloBadge tier={entry.league} showLabel={false} />
                      </td>
                      <td className="px-4 py-4 text-right">
                        <span className="font-extrabold font-brand text-[hsl(45,92%,48%)]" style={{ textShadow: '0 0 8px hsl(45 92% 48% / 0.5)' }}>
                          {entry.elo_rating}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-right text-[hsl(140,100%,50%)] font-bold">{entry.wins}</td>
                      <td className="px-4 py-4 text-right text-[hsl(0,100%,60%)] font-bold">{entry.losses}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
