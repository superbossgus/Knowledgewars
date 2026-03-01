import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { useAuthStore } from '../store/store';
import api from '../lib/api';
import { toast } from 'sonner';
import { Crown, Check, ArrowLeft, Zap, Star, Shield } from 'lucide-react';

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
      
      // Redirect to Stripe Checkout
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
      
      // Redirect to Stripe Checkout
      window.location.href = response.data.checkout_url;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create checkout');
    }
  };

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8">
      <div className="container mx-auto max-w-6xl">
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
          
          <div className="text-center">
            <Crown className="w-16 h-16 mx-auto mb-4 text-accent" />
            <h1 className="text-4xl md:text-5xl font-bold font-space mb-2">
              {t('premium.title')}
            </h1>
            <p className="text-muted-foreground text-lg">Unlock unlimited trivia battles</p>
          </div>
        </motion.div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
          {/* Premium Subscription */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-card/50 backdrop-blur-md border-2 border-accent/50 rounded-3xl p-8 relative overflow-hidden"
            data-testid="premium-tier-card"
          >
            <div className="absolute top-4 right-4">
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-accent text-accent-foreground text-xs font-semibold">
                <Star className="w-3 h-3" />
                POPULAR
              </span>
            </div>

            <div className="mb-6">
              <Crown className="w-12 h-12 mb-4 text-accent" />
              <h2 className="text-2xl font-bold font-space mb-2">Premium</h2>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold font-space">$3.99</span>
                <span className="text-muted-foreground">/month</span>
              </div>
            </div>

            <ul className="space-y-3 mb-8">
              <li className="flex items-center gap-2">
                <Check className="w-5 h-5 text-accent shrink-0" />
                <span>{t('premium.unlimited_duels')}</span>
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-5 h-5 text-accent shrink-0" />
                <span>{t('premium.no_ads')}</span>
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-5 h-5 text-accent shrink-0" />
                <span>{t('premium.special_themes')}</span>
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-5 h-5 text-accent shrink-0" />
                <span>Priority matchmaking</span>
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-5 h-5 text-accent shrink-0" />
                <span>Exclusive badges</span>
              </li>
            </ul>

            <button
              onClick={handleSubscribe}
              disabled={user?.premium_status}
              className="w-full btn-primary py-4 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
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
            className="bg-card/50 backdrop-blur-md border border-white/10 rounded-3xl p-8"
          >
            <div className="mb-6">
              <Zap className="w-12 h-12 mb-4 text-primary" />
              <h2 className="text-2xl font-bold font-space mb-2">Duel Pack</h2>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold font-space">$2.50</span>
                <span className="text-muted-foreground">one-time</span>
              </div>
            </div>

            <ul className="space-y-3 mb-8">
              <li className="flex items-center gap-2">
                <Check className="w-5 h-5 text-primary shrink-0" />
                <span>+100 Additional Duels</span>
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-5 h-5 text-primary shrink-0" />
                <span>No expiration</span>
              </li>
              <li className="flex items-center gap-2">
                <Check className="w-5 h-5 text-primary shrink-0" />
                <span>Stack multiple packs</span>
              </li>
              <li className="flex items-center gap-2 text-muted-foreground">
                <Shield className="w-5 h-5 shrink-0" />
                <span>Same ads experience</span>
              </li>
            </ul>

            <button
              onClick={handleBuy100}
              className="w-full btn-secondary-glass py-4 text-lg"
            >
              {t('premium.buy_100')}
            </button>
          </motion.div>
        </div>

        {/* FAQ or Features */}
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
