import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { useAuthStore } from '../store/store';
import api from '../lib/api';
import { toast } from 'sonner';

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
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <h1 className="text-4xl md:text-5xl font-bold font-space mb-2">
            {t('common.app_name')}
          </h1>
          <p className="text-muted-foreground">PvP Trivia Real-Time</p>
        </div>

        <div className="bg-card/50 backdrop-blur-md border border-white/10 rounded-2xl p-6 shadow-2xl">
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => setIsRegister(false)}
              className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                !isRegister ? 'bg-primary text-primary-foreground' : 'bg-muted/30 text-muted-foreground'
              }`}
              data-testid="login-tab"
            >
              {t('auth.login')}
            </button>
            <button
              onClick={() => setIsRegister(true)}
              className={`flex-1 py-2 rounded-lg font-medium transition-colors ${
                isRegister ? 'bg-primary text-primary-foreground' : 'bg-muted/30 text-muted-foreground'
              }`}
              data-testid="register-tab"
            >
              {t('auth.register')}
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">{t('auth.email')}</label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-4 py-2 bg-background/50 border border-input rounded-lg focus:ring-2 focus:ring-ring focus:outline-none"
                data-testid="login-email-input"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">{t('auth.password')}</label>
              <input
                type="password"
                required
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-4 py-2 bg-background/50 border border-input rounded-lg focus:ring-2 focus:ring-ring focus:outline-none"
                data-testid="login-password-input"
              />
            </div>

            {isRegister && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-2">{t('auth.display_name')}</label>
                  <input
                    type="text"
                    required
                    value={formData.display_name}
                    onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                    className="w-full px-4 py-2 bg-background/50 border border-input rounded-lg focus:ring-2 focus:ring-ring focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">{t('auth.country')}</label>
                  <select
                    value={formData.country_code}
                    onChange={(e) => setFormData({ ...formData, country_code: e.target.value })}
                    className="w-full px-4 py-2 bg-background/50 border border-input rounded-lg focus:ring-2 focus:ring-ring focus:outline-none"
                  >
                    {countries.map((c) => (
                      <option key={c.code} value={c.code}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">{t('auth.favorite_topic')}</label>
                  <select
                    value={formData.favorite_topic}
                    onChange={(e) => setFormData({ ...formData, favorite_topic: e.target.value })}
                    className="w-full px-4 py-2 bg-background/50 border border-input rounded-lg focus:ring-2 focus:ring-ring focus:outline-none"
                  >
                    {topics.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">{t('auth.language')}</label>
                  <select
                    value={formData.language}
                    onChange={(e) => {
                      setFormData({ ...formData, language: e.target.value });
                      i18n.changeLanguage(e.target.value);
                    }}
                    className="w-full px-4 py-2 bg-background/50 border border-input rounded-lg focus:ring-2 focus:ring-ring focus:outline-none"
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
              className="w-full btn-primary py-3 disabled:opacity-50 disabled:cursor-not-allowed"
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
