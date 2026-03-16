import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { useAuthStore } from '../store/store';
import api from '../lib/api';
import { toast } from 'sonner';
import { Swords, Shield, Chrome } from 'lucide-react';

const countries = [
  { code: 'us', name: 'United States' },
  { code: 'mx', name: 'Mexico' },
  { code: 'es', name: 'Spain' },
  { code: 'ar', name: 'Argentina' },
  { code: 'br', name: 'Brazil' },
  { code: 'co', name: 'Colombia' },
  { code: 'cl', name: 'Chile' },
  { code: 'pe', name: 'Peru' },
];

const topics = [
  'Sports', 'History', 'Geography', 'Science', 'Technology',
  'Movies/TV', 'Music', 'Gaming', 'General Knowledge'
];

export default function LoginPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const setAuth = useAuthStore((state) => state.setAuth);
  const hasProcessedCallback = useRef(false);
  
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(() => {
    // Check if user previously selected remember me
    return localStorage.getItem('remember_me') === 'true';
  });
  const [formData, setFormData] = useState(() => {
    // Pre-fill email if remembered
    const savedEmail = localStorage.getItem('remembered_email') || '';
    return {
      email: savedEmail,
      password: '',
      display_name: '',
      country_code: 'us',
      favorite_topic: 'General Knowledge',
      language: i18n.language || 'es'
    };
  });

  // Handle Google OAuth callback
  useEffect(() => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const hash = window.location.hash;
    if (hash && hash.includes('session_id=') && !hasProcessedCallback.current) {
      hasProcessedCallback.current = true;
      const sessionId = hash.split('session_id=')[1]?.split('&')[0];
      if (sessionId) {
        processGoogleCallback(sessionId);
      }
    }
  }, []);

  const processGoogleCallback = async (sessionId) => {
    setGoogleLoading(true);
    try {
      const response = await api.post('/api/auth/google/session', {
        session_id: sessionId,
        remember_me: rememberMe
      });
      
      const { token, user } = response.data;
      setAuth(user, token);
      
      // Save remember_me preference
      if (rememberMe) {
        localStorage.setItem('remember_me', 'true');
        localStorage.setItem('remembered_email', user.email || '');
      }
      
      // Clear the hash from URL
      window.history.replaceState(null, '', window.location.pathname);
      
      toast.success('¡Bienvenido con Google!');
      navigate('/home');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al iniciar sesión con Google');
      // Clear hash on error
      window.history.replaceState(null, '', window.location.pathname);
    } finally {
      setGoogleLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/login';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login';
      const payload = isRegister ? formData : { email: formData.email, password: formData.password };
      
      const response = await api.post(endpoint, payload);
      const { token, user } = response.data;
      
      // Save remember_me preference and email
      if (rememberMe) {
        localStorage.setItem('remember_me', 'true');
        localStorage.setItem('remembered_email', formData.email);
      } else {
        localStorage.removeItem('remember_me');
        localStorage.removeItem('remembered_email');
      }
      
      setAuth(user, token);
      toast.success(isRegister ? t('auth.register') + ' ' + t('common.success') : t('auth.login') + ' ' + t('common.success'));
      navigate('/home');
    } catch (error) {
      toast.error(error.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  // Show loading state if processing Google callback
  if (googleLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center hero-gradient">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-[hsl(220,100%,50%)] mx-auto mb-4"></div>
          <p className="text-white text-xl font-brand">Iniciando sesión con Google...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 hero-gradient">
      <div className="noise-overlay" />
      
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md relative z-10"
      >
        {/* Brand Logo Section */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <Shield className="w-12 h-12 text-[hsl(220,100%,50%)]" style={{ filter: 'drop-shadow(0 0 15px hsl(220 100% 50%))' }} />
            <Swords className="w-10 h-10 text-[hsl(25,100%,50%)]" style={{ filter: 'drop-shadow(0 0 10px hsl(25 100% 50%))' }} />
          </div>
          <h1 
            className="text-5xl md:text-6xl font-extrabold font-brand mb-2 text-white brand-title"
            data-testid="app-title"
          >
            KNOWLEDGE
          </h1>
          <h1 
            className="text-5xl md:text-6xl font-extrabold font-brand mb-3 text-[hsl(25,100%,50%)]" 
            style={{ textShadow: '0 0 20px hsl(25 100% 50%), 0 0 40px hsl(25 100% 50% / 0.5)' }}
          >
            WARS
          </h1>
          <p className="text-[hsl(220,100%,70%)] text-lg font-medium" style={{ textShadow: '0 0 10px hsl(220 100% 50% / 0.5)' }}>
            PvP Trivia Real-Time
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-[hsl(220,28%,10%,0.85)] backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-2xl p-6 shadow-2xl" style={{ boxShadow: '0 0 40px hsl(220 100% 50% / 0.15)' }}>
          
          {/* Google Login Button */}
          <button
            onClick={handleGoogleLogin}
            className="w-full flex items-center justify-center gap-3 py-4 px-6 mb-6 rounded-xl bg-white hover:bg-gray-50 text-gray-800 font-bold transition-all duration-200 shadow-lg hover:shadow-xl hover:-translate-y-0.5"
            data-testid="google-login-button"
          >
            <svg className="w-6 h-6" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continuar con Google
          </button>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/20"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-[hsl(220,28%,10%)] text-muted-foreground">o</span>
            </div>
          </div>

          {/* Tab Buttons */}
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => setIsRegister(false)}
              className={`flex-1 py-3 rounded-xl font-bold font-brand uppercase tracking-wide transition-all duration-200 ${
                !isRegister 
                  ? 'bg-[hsl(220,100%,50%)] text-white shadow-lg' 
                  : 'bg-muted/30 text-muted-foreground hover:bg-muted/50'
              }`}
              style={!isRegister ? { boxShadow: '0 0 20px hsl(220 100% 50% / 0.5)' } : {}}
              data-testid="login-tab"
            >
              {t('auth.login')}
            </button>
            <button
              onClick={() => setIsRegister(true)}
              className={`flex-1 py-3 rounded-xl font-bold font-brand uppercase tracking-wide transition-all duration-200 ${
                isRegister 
                  ? 'bg-[hsl(25,100%,50%)] text-white shadow-lg' 
                  : 'bg-muted/30 text-muted-foreground hover:bg-muted/50'
              }`}
              style={isRegister ? { boxShadow: '0 0 20px hsl(25 100% 50% / 0.5)' } : {}}
              data-testid="register-tab"
            >
              {t('auth.register')}
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold mb-2 text-white">{t('auth.email')}</label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-4 py-3 bg-background/50 border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl focus:ring-2 focus:ring-[hsl(220,100%,50%)] focus:border-[hsl(220,100%,50%)] focus:outline-none text-white placeholder-muted-foreground transition-all"
                placeholder="email@example.com"
                data-testid="login-email-input"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold mb-2 text-white">{t('auth.password')}</label>
              <input
                type="password"
                required
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-4 py-3 bg-background/50 border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl focus:ring-2 focus:ring-[hsl(220,100%,50%)] focus:border-[hsl(220,100%,50%)] focus:outline-none text-white placeholder-muted-foreground transition-all"
                placeholder="••••••••"
                data-testid="login-password-input"
              />
            </div>

            {isRegister && (
              <>
                <div>
                  <label className="block text-sm font-semibold mb-2 text-white">{t('auth.display_name')}</label>
                  <input
                    type="text"
                    required
                    value={formData.display_name}
                    onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                    className="w-full px-4 py-3 bg-background/50 border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl focus:ring-2 focus:ring-[hsl(220,100%,50%)] focus:border-[hsl(220,100%,50%)] focus:outline-none text-white placeholder-muted-foreground transition-all"
                    placeholder="YourGamertag"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold mb-2 text-white">{t('auth.country')}</label>
                  <select
                    value={formData.country_code}
                    onChange={(e) => setFormData({ ...formData, country_code: e.target.value })}
                    className="w-full px-4 py-3 bg-background/80 border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl focus:ring-2 focus:ring-[hsl(220,100%,50%)] focus:border-[hsl(220,100%,50%)] focus:outline-none text-white transition-all"
                  >
                    {countries.map((c) => (
                      <option key={c.code} value={c.code}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold mb-2 text-white">{t('auth.favorite_topic')}</label>
                  <select
                    value={formData.favorite_topic}
                    onChange={(e) => setFormData({ ...formData, favorite_topic: e.target.value })}
                    className="w-full px-4 py-3 bg-background/80 border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl focus:ring-2 focus:ring-[hsl(220,100%,50%)] focus:border-[hsl(220,100%,50%)] focus:outline-none text-white transition-all"
                  >
                    {topics.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold mb-2 text-white">{t('auth.language')}</label>
                  <select
                    value={formData.language}
                    onChange={(e) => {
                      setFormData({ ...formData, language: e.target.value });
                      i18n.changeLanguage(e.target.value);
                    }}
                    className="w-full px-4 py-3 bg-background/80 border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl focus:ring-2 focus:ring-[hsl(220,100%,50%)] focus:border-[hsl(220,100%,50%)] focus:outline-none text-white transition-all"
                  >
                    <option value="es">Español</option>
                    <option value="en">English</option>
                    <option value="pt">Português</option>
                  </select>
                </div>
              </>
            )}

            {/* Remember Me Checkbox */}
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="remember-me"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-5 h-5 rounded border-2 border-[hsl(220,100%,50%,0.5)] bg-background/50 text-[hsl(220,100%,50%)] focus:ring-[hsl(220,100%,50%)] focus:ring-2 cursor-pointer"
                data-testid="remember-me-checkbox"
              />
              <label htmlFor="remember-me" className="text-sm text-white/80 cursor-pointer select-none">
                Recordarme
              </label>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary py-4 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="login-submit-button"
            >
              {loading ? t('common.loading') : (isRegister ? t('auth.register') : t('auth.login'))}
            </button>
          </form>
        </div>
      </motion.div>
    </div>
  );
}
