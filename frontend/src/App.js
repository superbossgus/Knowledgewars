import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import { useAuthStore } from './store/store';
import api from './lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Swords, X, Shield } from 'lucide-react';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import LobbyPage from './pages/LobbyPage';
import MatchPage from './pages/MatchPage';
import ResultsPage from './pages/ResultsPage';
import RankingsPage from './pages/RankingsPage';
import StorePage from './pages/StorePage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import AdminPage from './pages/AdminPage';
import './i18n';
import './App.css';
import 'flag-icons/css/flag-icons.min.css';

function ProtectedRoute({ children }) {
  const token = useAuthStore((state) => state.token);
  return token ? children : <Navigate to="/login" replace />;
}

function ChallengeNotification({ challenge, onAccept, onReject }) {
  return (
    <motion.div
      initial={{ x: 400, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 400, opacity: 0 }}
      className="fixed top-4 right-4 z-[100] max-w-md w-full"
    >
      <div 
        className="bg-card/95 backdrop-blur-xl border-2 border-[hsl(25,100%,50%)] rounded-2xl p-6 shadow-2xl"
        style={{ boxShadow: '0 0 40px hsl(25 100% 50% / 0.5), 0 0 80px hsl(25 100% 50% / 0.25)' }}
      >
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-[hsl(220,100%,50%)]" style={{ filter: 'drop-shadow(0 0 8px hsl(220 100% 50%))' }} />
            <Swords className="w-6 h-6 text-[hsl(25,100%,50%)]" style={{ filter: 'drop-shadow(0 0 6px hsl(25 100% 50%))' }} />
            <div>
              <h3 className="text-xl font-extrabold text-white font-brand">¡DESAFÍO!</h3>
              <p className="text-sm text-[hsl(220,100%,70%)]">Challenge received</p>
            </div>
          </div>
          <button 
            onClick={onReject}
            className="text-white/60 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="mb-4 p-4 rounded-xl bg-muted/20 border-2 border-[hsl(220,100%,50%,0.3)]">
          <div className="flex items-center gap-3 mb-2">
            <span className={`fi fi-${challenge.player_a_country?.toLowerCase()} h-6 w-8 rounded shadow-lg`}></span>
            <div>
              <div className="font-bold text-white text-lg">{challenge.player_a_name}</div>
              <div className="text-sm text-[hsl(45,92%,48%)] font-bold">📚 {challenge.topic}</div>
            </div>
          </div>
        </div>
        
        <div className="flex gap-3">
          <button
            onClick={onAccept}
            className="flex-1 btn-primary py-3 text-base font-bold"
          >
            ⚔️ ACEPTAR
          </button>
          <button
            onClick={onReject}
            className="flex-1 btn-secondary-glass py-3 text-base"
          >
            Rechazar
          </button>
        </div>
      </div>
    </motion.div>
  );
}

function App() {
  const { token } = useAuthStore();
  const [pendingChallenge, setPendingChallenge] = useState(null);

  useEffect(() => {
    if (!token) return;

    const checkChallenges = async () => {
      try {
        const response = await api.get('/api/matches/pending');
        if (response.data.matches && response.data.matches.length > 0) {
          const latestChallenge = response.data.matches[0];
          
          if (!pendingChallenge || pendingChallenge.id !== latestChallenge.id) {
            setPendingChallenge(latestChallenge);
            
            try {
              const audio = new Audio('data:audio/wav;base64,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');
              audio.play().catch(() => {});
            } catch (e) {}
          }
        }
      } catch (error) {
        // Silently fail
      }
    };

    checkChallenges();
    const interval = setInterval(checkChallenges, 3000);
    
    return () => clearInterval(interval);
  }, [token, pendingChallenge]);

  const handleAcceptChallenge = async () => {
    if (!pendingChallenge) return;
    
    try {
      await api.post(`/api/matches/${pendingChallenge.id}/accept`);
      toast.success('¡Desafío aceptado!');
      setPendingChallenge(null);
      window.location.href = `/match/${pendingChallenge.id}`;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al aceptar el desafío');
    }
  };

  const handleRejectChallenge = async () => {
    if (!pendingChallenge) return;
    
    try {
      await api.post(`/api/matches/${pendingChallenge.id}/reject`);
      toast.info('Desafío rechazado');
      setPendingChallenge(null);
    } catch (error) {
      toast.error('Error al rechazar el desafío');
    }
  };

  return (
    <BrowserRouter>
      <div className="App">
        <AnimatePresence>
          {pendingChallenge && (
            <ChallengeNotification
              challenge={pendingChallenge}
              onAccept={handleAcceptChallenge}
              onReject={handleRejectChallenge}
            />
          )}
        </AnimatePresence>

        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/home"
            element={
              <ProtectedRoute>
                <HomePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/lobby"
            element={
              <ProtectedRoute>
                <LobbyPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/match/:matchId"
            element={
              <ProtectedRoute>
                <MatchPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/results/:matchId"
            element={
              <ProtectedRoute>
                <ResultsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/rankings"
            element={
              <ProtectedRoute>
                <RankingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/store"
            element={
              <ProtectedRoute>
                <StorePage />
              </ProtectedRoute>
            }
          />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/" element={<Navigate to="/home" replace />} />
        </Routes>
        <Toaster position="top-center" richColors />
      </div>
    </BrowserRouter>
  );
}

export default App;
