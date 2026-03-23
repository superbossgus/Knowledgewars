import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuthStore } from '../store/store';
import api from '../lib/api';
import { toast } from 'sonner';
import { ArrowLeft, Coins, Gift, Tag, AlertTriangle, CheckCircle, Zap, Sparkles } from 'lucide-react';

export default function StorePage() {
  const navigate = useNavigate();
  const { user, setAuth } = useAuthStore();
  const [credits, setCredits] = useState(null);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);
  const [couponCode, setCouponCode] = useState('');
  const [redeemingCoupon, setRedeemingCoupon] = useState(false);

  useEffect(() => {
    loadCredits();
  }, []);

  const loadCredits = async () => {
    try {
      const response = await api.get('/api/users/credits');
      setCredits(response.data);
    } catch (error) {
      toast.error('Error al cargar créditos');
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = async () => {
    setPurchasing(true);
    try {
      // Get current origin for success/cancel URLs
      const origin = window.location.origin;
      
      const purchaseResponse = await api.post('/api/games/purchase', null, {
        headers: {
          'Origin': origin
        }
      });
      
      // Redirect to Stripe Checkout
      if (purchaseResponse.data.checkout_url) {
        window.location.href = purchaseResponse.data.checkout_url;
      } else {
        throw new Error('No se recibió URL de pago');
      }
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al iniciar compra');
      setPurchasing(false);
    }
  };

  const handleRedeemCoupon = async (e) => {
    e.preventDefault();
    if (!couponCode.trim()) return;
    
    setRedeemingCoupon(true);
    try {
      const response = await api.post('/api/coupons/redeem', { code: couponCode });
      toast.success(response.data.message);
      setCouponCode('');
      setCredits(prev => ({
        ...prev,
        games_remaining: response.data.games_remaining,
        low_credits_warning: response.data.games_remaining <= 5
      }));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Cupón inválido');
    } finally {
      setRedeemingCoupon(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[hsl(220,100%,50%)]"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8 relative z-10">
      <div className="container mx-auto max-w-4xl">
        {/* Header */}
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
            Volver al inicio
          </button>
          
          <div className="text-center">
            <Coins className="w-16 h-16 mx-auto mb-4 text-[hsl(45,92%,48%)]" style={{ filter: 'drop-shadow(0 0 15px hsl(45 92% 48%))' }} />
            <h1 className="text-4xl font-extrabold font-brand text-white mb-2">Tienda</h1>
            <p className="text-muted-foreground">Compra partidas para seguir jugando</p>
          </div>
        </motion.div>

        {/* Current Credits Display */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className={`mb-8 p-6 rounded-2xl border-2 backdrop-blur-xl ${
            credits?.no_credits 
              ? 'bg-[hsl(0,100%,50%,0.1)] border-[hsl(0,100%,50%,0.4)]' 
              : credits?.low_credits_warning 
                ? 'bg-[hsl(45,92%,48%,0.1)] border-[hsl(45,92%,48%,0.4)]'
                : 'bg-card/60 border-[hsl(220,100%,50%,0.3)]'
          }`}
          data-testid="credits-display"
        >
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white mb-1">Tus Partidas Disponibles</h2>
              <div className="flex items-center gap-2">
                <span className="text-5xl font-extrabold font-brand text-[hsl(45,92%,48%)]" style={{ textShadow: '0 0 15px hsl(45 92% 48%)' }}>
                  {credits?.games_remaining || 0}
                </span>
                <span className="text-muted-foreground">partidas</span>
              </div>
            </div>
            
            {credits?.low_credits_warning && (
              <div className={`flex items-center gap-2 px-4 py-2 rounded-xl ${
                credits?.no_credits 
                  ? 'bg-[hsl(0,100%,50%,0.2)] text-[hsl(0,100%,70%)]'
                  : 'bg-[hsl(45,92%,48%,0.2)] text-[hsl(45,92%,48%)]'
              }`}>
                <AlertTriangle className="w-5 h-5" />
                <span className="font-bold text-sm">
                  {credits?.no_credits ? '¡Sin partidas!' : '¡Pocas partidas!'}
                </span>
              </div>
            )}
          </div>
        </motion.div>

        {/* Main Purchase Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(25,100%,50%,0.4)] rounded-3xl p-8 mb-8 relative overflow-hidden"
          style={{ boxShadow: '0 0 40px hsl(25 100% 50% / 0.15)' }}
          data-testid="purchase-card"
        >
          <div className="absolute top-4 right-4">
            <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-[hsl(25,100%,50%)] text-white text-xs font-bold uppercase tracking-wide">
              <Sparkles className="w-3 h-3" />
              MEJOR VALOR
            </span>
          </div>

          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <Zap className="w-12 h-12 text-[hsl(25,100%,50%)]" style={{ filter: 'drop-shadow(0 0 10px hsl(25 100% 50%))' }} />
                <div>
                  <h2 className="text-3xl font-extrabold font-brand text-white">50 Partidas</h2>
                  <p className="text-muted-foreground">Para desafiar a tus rivales</p>
                </div>
              </div>
              
              <ul className="space-y-2 mb-4">
                <li className="flex items-center gap-2 text-white">
                  <CheckCircle className="w-5 h-5 text-[hsl(140,100%,50%)]" />
                  <span>50 partidas completas</span>
                </li>
                <li className="flex items-center gap-2 text-white">
                  <CheckCircle className="w-5 h-5 text-[hsl(140,100%,50%)]" />
                  <span>Sin fecha de expiración</span>
                </li>
                <li className="flex items-center gap-2 text-white">
                  <CheckCircle className="w-5 h-5 text-[hsl(140,100%,50%)]" />
                  <span>Acceso a todos los temas</span>
                </li>
              </ul>
            </div>

            <div className="text-center md:text-right">
              <div className="mb-4">
                <span className="text-5xl font-extrabold font-brand text-white">$99</span>
                <span className="text-xl text-muted-foreground ml-1">MXN</span>
              </div>
              <button
                onClick={handlePurchase}
                disabled={purchasing}
                className="btn-primary px-10 py-4 text-lg w-full md:w-auto disabled:opacity-50"
                data-testid="purchase-button"
              >
                {purchasing ? 'Procesando...' : 'Comprar Ahora'}
              </button>
            </div>
          </div>
        </motion.div>

        {/* Coupon Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-2xl p-6"
          data-testid="coupon-section"
        >
          <div className="flex items-center gap-2 mb-4">
            <Gift className="w-6 h-6 text-[hsl(220,100%,50%)]" />
            <h3 className="text-xl font-bold text-white">¿Tienes un cupón?</h3>
          </div>
          
          <form onSubmit={handleRedeemCoupon} className="flex gap-3">
            <div className="flex-1 relative">
              <Tag className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <input
                type="text"
                value={couponCode}
                onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                placeholder="CODIGO-CUPON"
                className="w-full pl-10 pr-4 py-3 bg-background/50 border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl text-white placeholder-muted-foreground focus:ring-2 focus:ring-[hsl(220,100%,50%)] focus:outline-none uppercase font-mono tracking-wide"
                data-testid="coupon-input"
              />
            </div>
            <button
              type="submit"
              disabled={redeemingCoupon || !couponCode.trim()}
              className="btn-secondary-glass px-6 py-3 disabled:opacity-50"
              data-testid="redeem-coupon-button"
            >
              {redeemingCoupon ? 'Canjeando...' : 'Canjear'}
            </button>
          </form>
          
          <p className="text-sm text-muted-foreground mt-3">
            Los cupones pueden darte partidas gratis o descuentos en tu próxima compra.
          </p>
        </motion.div>
      </div>
    </div>
  );
}
