import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuthStore } from '../store/store';
import api from '../lib/api';
import { toast } from 'sonner';
import { CheckCircle, Loader2, XCircle, ArrowLeft } from 'lucide-react';

export default function PaymentSuccessPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setAuth } = useAuthStore();
  const [status, setStatus] = useState('checking'); // checking, success, error
  const [gamesRemaining, setGamesRemaining] = useState(null);
  const [attempts, setAttempts] = useState(0);
  const maxAttempts = 10;

  useEffect(() => {
    const sessionId = searchParams.get('session_id');
    
    if (!sessionId) {
      toast.error('Sesión de pago no encontrada');
      navigate('/store');
      return;
    }

    // Poll payment status
    pollPaymentStatus(sessionId);
  }, []);

  const pollPaymentStatus = async (sessionId, currentAttempt = 0) => {
    if (currentAttempt >= maxAttempts) {
      setStatus('error');
      toast.error('No se pudo verificar el pago. Por favor contacta soporte.');
      return;
    }

    try {
      const response = await api.get(`/api/payments/checkout/status/${sessionId}`);
      
      if (response.data.payment_status === 'paid') {
        // Payment successful!
        setStatus('success');
        setGamesRemaining(response.data.games_remaining);
        toast.success('¡Pago completado exitosamente! 🎉');
        
        // Refresh user data
        const meResponse = await api.get('/api/auth/me');
        const token = localStorage.getItem('auth_token');
        setAuth(meResponse.data, token);
        
        // Redirect to home after 3 seconds
        setTimeout(() => {
          navigate('/home');
        }, 3000);
      } else if (response.data.status === 'expired') {
        setStatus('error');
        toast.error('La sesión de pago expiró');
      } else {
        // Still processing, try again
        setAttempts(currentAttempt + 1);
        setTimeout(() => {
          pollPaymentStatus(sessionId, currentAttempt + 1);
        }, 2000); // Poll every 2 seconds
      }
    } catch (error) {
      console.error('Error checking payment status:', error);
      setAttempts(currentAttempt + 1);
      
      if (currentAttempt < maxAttempts - 1) {
        setTimeout(() => {
          pollPaymentStatus(sessionId, currentAttempt + 1);
        }, 2000);
      } else {
        setStatus('error');
        toast.error('Error al verificar el pago');
      }
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative z-10">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-card/95 backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-3xl p-8 max-w-md w-full text-center"
        style={{ boxShadow: '0 0 50px hsl(220 100% 50% / 0.15)' }}
      >
        {status === 'checking' && (
          <>
            <Loader2 className="w-16 h-16 mx-auto mb-6 text-[hsl(220,100%,50%)] animate-spin" />
            <h2 className="text-2xl font-bold text-white mb-3 font-brand">
              Verificando Pago...
            </h2>
            <p className="text-muted-foreground mb-4">
              Por favor espera mientras confirmamos tu pago con Stripe
            </p>
            <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <span>Intento {attempts + 1} de {maxAttempts}</span>
            </div>
          </>
        )}

        {status === 'success' && (
          <>
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 200, damping: 10 }}
            >
              <CheckCircle 
                className="w-20 h-20 mx-auto mb-6 text-[hsl(140,100%,50%)]" 
                style={{ filter: 'drop-shadow(0 0 20px hsl(140 100% 50%))' }}
              />
            </motion.div>
            <h2 className="text-3xl font-extrabold text-white mb-3 font-brand">
              ¡Pago Exitoso!
            </h2>
            <p className="text-lg text-muted-foreground mb-6">
              Tu compra de <strong className="text-[hsl(45,92%,48%)]">50 partidas</strong> se ha completado
            </p>
            {gamesRemaining !== null && (
              <div className="bg-[hsl(220,100%,50%,0.1)] border border-[hsl(220,100%,50%,0.3)] rounded-xl p-4 mb-6">
                <p className="text-sm text-muted-foreground mb-1">Partidas Disponibles</p>
                <p className="text-4xl font-extrabold text-[hsl(45,92%,48%)] font-brand" style={{ textShadow: '0 0 20px hsl(45 92% 48%)' }}>
                  {gamesRemaining}
                </p>
              </div>
            )}
            <p className="text-sm text-muted-foreground">
              Redirigiendo al inicio...
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="w-16 h-16 mx-auto mb-6 text-[hsl(0,100%,60%)]" />
            <h2 className="text-2xl font-bold text-white mb-3 font-brand">
              Error en la Verificación
            </h2>
            <p className="text-muted-foreground mb-6">
              No pudimos verificar tu pago. Si completaste el pago, por favor contacta soporte.
            </p>
            <button
              onClick={() => navigate('/store')}
              className="btn-secondary-glass px-6 py-3 flex items-center gap-2 mx-auto"
            >
              <ArrowLeft className="w-4 h-4" />
              Volver a la Tienda
            </button>
          </>
        )}
      </motion.div>
    </div>
  );
}
