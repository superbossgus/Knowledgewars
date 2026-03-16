import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { useAuthStore } from '../store/store';
import api from '../lib/api';
import { toast } from 'sonner';
import { Crown, Check, ArrowLeft, Zap, Star, Shield, Gem } from 'lucide-react';

export default function PremiumPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const handleSubscribe = async () => {
    try {
      const response = await api.post('/api/payments/checkout', {
        product_type: 'premium_subscription',
        origin_url: window.location.origin
      });
      
      window.location.href = response.data.checkout_url;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create checkout');
    }
  };

  const handleBuy100 = async () => {
    try {
      const response = await api.post('/api/payments/checkout', {
        product_type: 'consumable_100',
        origin_url: window.location.origin
      });
      
      window.location.href = response.data.checkout_url;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create checkout');
    }
  };

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8 relative z-10">
      <div className="container mx-auto max-w-6xl">
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
          
          <div className="text-center">
            <Crown 
              className="w-20 h-20 mx-auto mb-4 text-[hsl(45,92%,48%)]" 
              style={{ filter: 'drop-shadow(0 0 20px hsl(45 92% 48%))' }}
            />
            <h1 className="text-4xl md:text-5xl font-extrabold font-brand mb-2 text-white">
              {t('premium.title')}
            </h1>
            <p className="text-[hsl(220,100%,70%)] text-lg font-medium">Unlock unlimited trivia battles</p>
          </div>
        </motion.div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
          {/* Premium Subscription */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(45,92%,48%,0.5)] rounded-3xl p-8 relative overflow-hidden"
            style={{ boxShadow: '0 0 40px hsl(45 92% 48% / 0.15)' }}
            data-testid="premium-tier-card"
          >
            <div className="absolute top-4 right-4">
              <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-[hsl(45,92%,48%)] text-black text-xs font-bold uppercase tracking-wide">
                <Star className="w-3 h-3" />
                POPULAR
              </span>
            </div>

            <div className="mb-6">
              <Gem 
                className="w-14 h-14 mb-4 text-[hsl(45,92%,48%)]" 
                style={{ filter: 'drop-shadow(0 0 10px hsl(45 92% 48%))' }}
              />
              <h2 className="text-2xl font-extrabold font-brand mb-2 text-white">Premium</h2>
              <div className="flex items-baseline gap-2">
                <span className="text-5xl font-extrabold font-brand text-[hsl(45,92%,48%)]" style={{ textShadow: '0 0 15px hsl(45 92% 48%)' }}>$3.99</span>
                <span className="text-muted-foreground font-medium">/month</span>
              </div>
            </div>

            <ul className="space-y-4 mb-8">
              <li className="flex items-center gap-3">
                <Check className="w-5 h-5 text-[hsl(45,92%,48%)] shrink-0" />
                <span className="text-white font-medium">{t('premium.unlimited_duels')}</span>
              </li>
              <li className="flex items-center gap-3">
                <Check className="w-5 h-5 text-[hsl(45,92%,48%)] shrink-0" />
                <span className="text-white font-medium">{t('premium.no_ads')}</span>
              </li>
              <li className="flex items-center gap-3">
                <Check className="w-5 h-5 text-[hsl(45,92%,48%)] shrink-0" />
                <span className="text-white font-medium">{t('premium.special_themes')}</span>
              </li>
              <li className="flex items-center gap-3">
                <Check className="w-5 h-5 text-[hsl(45,92%,48%)] shrink-0" />
                <span className="text-white font-medium">Priority matchmaking</span>
              </li>
              <li className="flex items-center gap-3">
                <Check className="w-5 h-5 text-[hsl(45,92%,48%)] shrink-0" />
                <span className="text-white font-medium">Exclusive badges</span>
              </li>
            </ul>

            <button
              onClick={handleSubscribe}
              disabled={user?.premium_status}
              className="w-full py-4 text-lg font-bold font-brand uppercase tracking-wide rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: 'linear-gradient(135deg, hsl(45, 92%, 48%) 0%, hsl(45, 92%, 40%) 100%)',
                color: 'black',
                boxShadow: '0 0 25px hsl(45 92% 48% / 0.5)',
              }}
              data-testid="premium-subscribe-button"
            >
              {user?.premium_status ? 'Already Premium' : t('premium.subscribe')}
            </button>
          </motion.div>

          {/* One-time Purchase */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-3xl p-8"
            style={{ boxShadow: '0 0 30px hsl(220 100% 50% / 0.1)' }}
          >
            <div className="mb-6">
              <Zap 
                className="w-14 h-14 mb-4 text-[hsl(220,100%,50%)]" 
                style={{ filter: 'drop-shadow(0 0 10px hsl(220 100% 50%))' }}
              />
              <h2 className="text-2xl font-extrabold font-brand mb-2 text-white">Duel Pack</h2>
              <div className="flex items-baseline gap-2">
                <span className="text-5xl font-extrabold font-brand text-[hsl(220,100%,50%)]" style={{ textShadow: '0 0 15px hsl(220 100% 50%)' }}>$2.50</span>
                <span className="text-muted-foreground font-medium">one-time</span>
              </div>
            </div>

            <ul className="space-y-4 mb-8">
              <li className="flex items-center gap-3">
                <Check className="w-5 h-5 text-[hsl(220,100%,50%)] shrink-0" />
                <span className="text-white font-medium">+100 Additional Duels</span>
              </li>
              <li className="flex items-center gap-3">
                <Check className="w-5 h-5 text-[hsl(220,100%,50%)] shrink-0" />
                <span className="text-white font-medium">No expiration</span>
              </li>
              <li className="flex items-center gap-3">
                <Check className="w-5 h-5 text-[hsl(220,100%,50%)] shrink-0" />
                <span className="text-white font-medium">Stack multiple packs</span>
              </li>
              <li className="flex items-center gap-3 text-muted-foreground">
                <Shield className="w-5 h-5 shrink-0" />
                <span className="font-medium">Same ads experience</span>
              </li>
            </ul>

            <button
              onClick={handleBuy100}
              className="w-full btn-secondary-glass py-4 text-lg font-bold"
            >
              {t('premium.buy_100')}
            </button>
          </motion.div>
        </div>

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-center text-muted-foreground text-sm"
        >
          <p>All payments are secure and processed by Stripe. Cancel anytime.</p>
        </motion.div>
      </div>
    </div>
  );
}
