import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import api from '../lib/api';
import { toast } from 'sonner';
import { ArrowLeft, Mail, KeyRound, CheckCircle, Shield } from 'lucide-react';

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: email, 2: code, 3: new password, 4: success
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const handleRequestReset = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await api.post('/api/auth/forgot-password', { email });
      toast.success('Código enviado a tu email');
      // In development, show the code
      if (response.data._dev_code) {
        toast.info(`Código de desarrollo: ${response.data._dev_code}`, { duration: 10000 });
      }
      setStep(2);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al enviar código');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await api.post(`/api/auth/verify-reset-code?email=${encodeURIComponent(email)}&code=${code}`);
      setResetToken(response.data.reset_token);
      toast.success('Código verificado');
      setStep(3);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Código inválido');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error('Las contraseñas no coinciden');
      return;
    }
    if (newPassword.length < 6) {
      toast.error('La contraseña debe tener al menos 6 caracteres');
      return;
    }
    setLoading(true);
    try {
      await api.post('/api/auth/reset-password', {
        token: resetToken,
        new_password: newPassword
      });
      toast.success('¡Contraseña actualizada!');
      setStep(4);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al cambiar contraseña');
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
        className="w-full max-w-md relative z-10"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <Shield className="w-16 h-16 mx-auto mb-4 text-[hsl(220,100%,50%)]" style={{ filter: 'drop-shadow(0 0 15px hsl(220 100% 50%))' }} />
          <h1 className="text-3xl font-extrabold font-brand text-white mb-2">Recuperar Contraseña</h1>
          <p className="text-muted-foreground">Sigue los pasos para restablecer tu contraseña</p>
        </div>

        {/* Card */}
        <div className="bg-[hsl(220,28%,10%,0.85)] backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-2xl p-6">
          
          {/* Step 1: Enter Email */}
          {step === 1 && (
            <form onSubmit={handleRequestReset} className="space-y-4">
              <div className="flex items-center gap-2 mb-4 text-[hsl(220,100%,70%)]">
                <Mail className="w-5 h-5" />
                <span className="font-bold">Paso 1: Ingresa tu email</span>
              </div>
              
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tu@email.com"
                className="w-full px-4 py-3 bg-background/50 border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl text-white placeholder-muted-foreground focus:ring-2 focus:ring-[hsl(220,100%,50%)] focus:outline-none"
                data-testid="forgot-email-input"
              />
              
              <button
                type="submit"
                disabled={loading}
                className="w-full btn-primary py-3 disabled:opacity-50"
                data-testid="forgot-submit-button"
              >
                {loading ? 'Enviando...' : 'Enviar Código'}
              </button>
            </form>
          )}

          {/* Step 2: Enter Code */}
          {step === 2 && (
            <form onSubmit={handleVerifyCode} className="space-y-4">
              <div className="flex items-center gap-2 mb-4 text-[hsl(25,100%,50%)]">
                <KeyRound className="w-5 h-5" />
                <span className="font-bold">Paso 2: Ingresa el código</span>
              </div>
              
              <p className="text-sm text-muted-foreground mb-4">
                Hemos enviado un código de 6 dígitos a <span className="text-white font-semibold">{email}</span>
              </p>
              
              <input
                type="text"
                required
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                placeholder="000000"
                className="w-full px-4 py-4 bg-background/50 border-2 border-[hsl(25,100%,50%,0.3)] rounded-xl text-white text-center text-2xl font-mono tracking-widest placeholder-muted-foreground focus:ring-2 focus:ring-[hsl(25,100%,50%)] focus:outline-none"
                data-testid="forgot-code-input"
              />
              
              <button
                type="submit"
                disabled={loading || code.length !== 6}
                className="w-full btn-primary py-3 disabled:opacity-50"
              >
                {loading ? 'Verificando...' : 'Verificar Código'}
              </button>
              
              <button
                type="button"
                onClick={() => setStep(1)}
                className="w-full text-sm text-muted-foreground hover:text-white"
              >
                ¿No recibiste el código? Intentar de nuevo
              </button>
            </form>
          )}

          {/* Step 3: New Password */}
          {step === 3 && (
            <form onSubmit={handleResetPassword} className="space-y-4">
              <div className="flex items-center gap-2 mb-4 text-[hsl(45,92%,48%)]">
                <KeyRound className="w-5 h-5" />
                <span className="font-bold">Paso 3: Nueva contraseña</span>
              </div>
              
              <input
                type="password"
                required
                minLength={6}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Nueva contraseña"
                className="w-full px-4 py-3 bg-background/50 border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl text-white placeholder-muted-foreground focus:ring-2 focus:ring-[hsl(220,100%,50%)] focus:outline-none"
              />
              
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirmar contraseña"
                className="w-full px-4 py-3 bg-background/50 border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl text-white placeholder-muted-foreground focus:ring-2 focus:ring-[hsl(220,100%,50%)] focus:outline-none"
              />
              
              <button
                type="submit"
                disabled={loading}
                className="w-full btn-primary py-3 disabled:opacity-50"
              >
                {loading ? 'Guardando...' : 'Guardar Nueva Contraseña'}
              </button>
            </form>
          )}

          {/* Step 4: Success */}
          {step === 4 && (
            <div className="text-center py-6">
              <CheckCircle className="w-20 h-20 mx-auto mb-4 text-[hsl(140,100%,50%)]" style={{ filter: 'drop-shadow(0 0 15px hsl(140 100% 50%))' }} />
              <h2 className="text-2xl font-bold text-white mb-2">¡Contraseña Actualizada!</h2>
              <p className="text-muted-foreground mb-6">Ya puedes iniciar sesión con tu nueva contraseña</p>
              <button
                onClick={() => navigate('/login')}
                className="btn-primary px-8 py-3"
              >
                Ir a Iniciar Sesión
              </button>
            </div>
          )}

          {/* Back to login */}
          {step !== 4 && (
            <button
              onClick={() => navigate('/login')}
              className="flex items-center gap-2 mt-6 text-muted-foreground hover:text-white transition-colors w-full justify-center"
            >
              <ArrowLeft className="w-4 h-4" />
              Volver al inicio de sesión
            </button>
          )}
        </div>
      </motion.div>
    </div>
  );
}
