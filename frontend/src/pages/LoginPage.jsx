import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { useAuthStore } from '../store/store';
import api from '../lib/api';
import { toast } from 'sonner';
import { Swords, Shield } from 'lucide-react';

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
  const setAuth = useAuthStore((state) => state.setAuth);
  
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    display_name: '',
    country_code: 'us',
    favorite_topic: 'General Knowledge',
    language: i18n.language || 'es'
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login';
      const payload = isRegister ? formData : { email: formData.email, password: formData.password };
      
      const response = await api.post(endpoint, payload);
      const { token, user } = response.data;
      
      setAuth(user, token);
      toast.success(isRegister ? t('auth.register') + ' ' + t('common.success') : t('auth.login') + ' ' + t('common.success'));
      navigate('/home');
    } catch (error) {
      toast.error(error.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

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
        <div className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-2xl p-6 shadow-2xl" style={{ boxShadow: '0 0 40px hsl(220 100% 50% / 0.15)' }}>
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
