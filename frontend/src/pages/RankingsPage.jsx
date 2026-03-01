import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { EloBadge } from '../components/custom/EloBadge';
import api from '../lib/api';
import { ArrowLeft, Trophy, TrendingUp } from 'lucide-react';

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
    <div className="min-h-screen p-4 md:p-6 lg:p-8">
      <div className="container mx-auto max-w-5xl">
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
          
          <h1 className="text-3xl md:text-4xl font-bold font-space mb-2 flex items-center gap-3">
            <Trophy className="w-8 h-8 text-accent" />
            {t('rankings.global')}
          </h1>
          <p className="text-muted-foreground">Top players worldwide</p>
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
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              activeTab === 'global' ? 'bg-primary text-primary-foreground' : 'bg-muted/30 text-muted-foreground'
            }`}
            data-testid="leaderboard-tab-global"
          >
            {t('rankings.global')}
          </button>
          <button
            onClick={() => setActiveTab('weekly')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              activeTab === 'weekly' ? 'bg-primary text-primary-foreground' : 'bg-muted/30 text-muted-foreground'
            }`}
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
          className="bg-card/50 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden"
        >
          {loading ? (
            <div className="text-center py-12 text-muted-foreground">Loading rankings...</div>
          ) : rankings.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">No rankings data available</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/10 bg-muted/20">
                    <th className="px-4 py-3 text-left text-sm font-semibold">{t('rankings.rank')}</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold">{t('rankings.player')}</th>
                    <th className="px-4 py-3 text-center text-sm font-semibold">League</th>
                    <th className="px-4 py-3 text-right text-sm font-semibold">{t('rankings.elo')}</th>
                    <th className="px-4 py-3 text-right text-sm font-semibold">{t('rankings.wins')}</th>
                    <th className="px-4 py-3 text-right text-sm font-semibold">{t('rankings.losses')}</th>
                  </tr>
                </thead>
                <tbody>
                  {rankings.map((entry) => (
                    <tr
                      key={entry.user_id}
                      className="border-b border-white/5 hover:bg-white/5 transition-colors"
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
                            />
                          )}
                          <span className="font-semibold font-space">#{entry.rank}</span>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          <span className={`fi fi-${entry.country_code?.toLowerCase()} h-4 w-6 rounded-sm`}></span>
                          <span className="font-medium">{entry.display_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-center">
                        <EloBadge tier={entry.league} showIcon={false} />
                      </td>
                      <td className="px-4 py-4 text-right font-bold font-space">{entry.elo_rating}</td>
                      <td className="px-4 py-4 text-right text-emerald-400 font-semibold">{entry.wins}</td>
                      <td className="px-4 py-4 text-right text-red-400 font-semibold">{entry.losses}</td>
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
