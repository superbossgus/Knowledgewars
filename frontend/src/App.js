import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import { useAuthStore } from './store/store';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import LobbyPage from './pages/LobbyPage';
import MatchPage from './pages/MatchPage';
import ResultsPage from './pages/ResultsPage';
import RankingsPage from './pages/RankingsPage';
import PremiumPage from './pages/PremiumPage';
import './i18n';
import './App.css';
import 'flag-icons/css/flag-icons.min.css';

function ProtectedRoute({ children }) {
  const token = useAuthStore((state) => state.token);
  return token ? children : <Navigate to="/login" replace />;
}

function App() {
  return (
    <BrowserRouter>
      <div className="App">
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
            path="/premium"
            element={
              <ProtectedRoute>
                <PremiumPage />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/home" replace />} />
        </Routes>
        <Toaster position="top-center" richColors />
      </div>
    </BrowserRouter>
  );
}

export default App;
