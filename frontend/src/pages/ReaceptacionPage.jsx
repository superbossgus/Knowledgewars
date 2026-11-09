import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Shield, AlertTriangle } from 'lucide-react';
import { useAuthStore } from '../store/store';
import api from '../lib/api';

/**
 * El muro de reaceptacion (BOS-351, criterio §5.4).
 *
 * Lo ve el usuario cuyo ultimo consentimiento no apunta a los textos vigentes:
 * la cuenta creada antes de que existiera el aviso, y la que acepto una version
 * anterior. **Sin aceptar no se entra, pero si se puede salir:** desde esta
 * misma pantalla se elimina la cuenta. Un muro que no deja salir es un problema
 * peor que el que resuelve, y por eso el boton de eliminar no esta escondido en
 * un submenu.
 *
 * Las cuentas dormidas no se tocan: esto se dispara cuando la persona vuelve.
 */
export default function ReaceptacionPage() {
  const { user, setAuth, token, logout } = useAuthStore();
  const [aceptaTerminos, setAceptaTerminos] = useState(false);
  const [aceptaMarketing, setAceptaMarketing] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [confirmandoBaja, setConfirmandoBaja] = useState(false);

  const aceptar = async () => {
    if (!aceptaTerminos) return;
    setEnviando(true);
    try {
      const res = await api.post('/api/legal/aceptar', {
        acepta_terminos: true,
        acepta_marketing: aceptaMarketing,
      });
      setAuth({ ...user, legal: res.data.legal }, token);
      toast.success('Gracias. Ya puedes seguir jugando.');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No pudimos guardar tu aceptacion.');
    } finally {
      setEnviando(false);
    }
  };

  const eliminarCuenta = async () => {
    setEnviando(true);
    try {
      await api.delete('/api/users/me');
      toast.success('Tu cuenta se elimino.');
      logout();
      window.location.href = '/login';
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No pudimos eliminar tu cuenta.');
      setEnviando(false);
    }
  };

  return (
    <div className="hero-gradient flex min-h-screen items-center justify-center p-4">
      <div className="noise-overlay" />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="relative z-10 w-full max-w-lg"
      >
        <div
          className="rounded-2xl border-2 border-[hsl(25,100%,50%,0.4)] bg-[hsl(220,28%,10%,0.9)] p-6 shadow-2xl backdrop-blur-xl md:p-8"
          style={{ boxShadow: '0 0 40px hsl(25 100% 50% / 0.2)' }}
          data-testid="reaceptacion-muro"
        >
          <div className="mb-5 flex items-center gap-3">
            <Shield
              className="h-9 w-9 shrink-0 text-[hsl(220,100%,50%)]"
              style={{ filter: 'drop-shadow(0 0 10px hsl(220 100% 50%))' }}
            />
            <h1 className="font-brand text-2xl font-extrabold text-white">
              Publicamos nuestro Aviso de privacidad y nuestros Terminos de uso
            </h1>
          </div>

          <p className="mb-6 leading-relaxed text-white/80">
            Para seguir jugando, necesitamos que los leas y los aceptes.
          </p>

          <div className="mb-6 space-y-4">
            <label className="flex cursor-pointer items-start gap-3 text-sm text-white/90">
              <input
                type="checkbox"
                checked={aceptaTerminos}
                onChange={(e) => setAceptaTerminos(e.target.checked)}
                className="mt-0.5 h-5 w-5 shrink-0 cursor-pointer rounded border-2 border-[hsl(25,100%,50%,0.6)] bg-background/50"
                data-testid="reaceptacion-terminos-checkbox"
              />
              <span>
                <strong className="font-bold">Soy mayor de 18 anos</strong> y acepto los{' '}
                <Link
                  to="/terminos"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[hsl(220,100%,70%)] underline hover:text-white"
                >
                  Terminos de uso
                </Link>{' '}
                y el{' '}
                <Link
                  to="/privacidad"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[hsl(220,100%,70%)] underline hover:text-white"
                >
                  Aviso de privacidad
                </Link>
                .
              </span>
            </label>

            <label className="flex cursor-pointer items-start gap-3 text-sm text-white/70">
              <input
                type="checkbox"
                checked={aceptaMarketing}
                onChange={(e) => setAceptaMarketing(e.target.checked)}
                className="mt-0.5 h-5 w-5 shrink-0 cursor-pointer rounded border-2 border-[hsl(220,100%,50%,0.5)] bg-background/50"
                data-testid="reaceptacion-marketing-checkbox"
              />
              <span>
                Quiero recibir novedades, torneos y promociones de Knowledge Wars por correo.{' '}
                <em className="text-white/50">(opcional)</em>
              </span>
            </label>
          </div>

          <button
            type="button"
            onClick={aceptar}
            disabled={!aceptaTerminos || enviando}
            className="btn-primary w-full py-4 text-lg disabled:cursor-not-allowed disabled:opacity-50"
            data-testid="reaceptacion-aceptar-button"
          >
            {enviando ? 'Guardando...' : 'Aceptar y continuar'}
          </button>

          {/* La salida. Esta aqui, a la vista, por diseno: el muro no puede ser
              una trampa (§5.4, numeral 2). */}
          <div className="mt-6 border-t border-white/10 pt-5">
            {!confirmandoBaja ? (
              <button
                type="button"
                onClick={() => setConfirmandoBaja(true)}
                className="text-sm text-white/50 underline transition-colors hover:text-white/80"
                data-testid="reaceptacion-eliminar-link"
              >
                No acepto: quiero eliminar mi cuenta
              </button>
            ) : (
              <div className="space-y-3" data-testid="reaceptacion-confirmar-baja">
                <p className="flex items-start gap-2 text-sm text-white/80">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[hsl(45,92%,58%)]" />
                  <span>
                    Se borran tu perfil y tu historial de partidas. Conservamos solo lo que la ley
                    nos obliga: el registro de tus compras y la constancia de que aceptaste en su
                    momento.
                  </span>
                </p>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={eliminarCuenta}
                    disabled={enviando}
                    className="flex-1 rounded-lg border-2 border-red-500/60 bg-red-600/20 py-3 text-sm font-bold text-white transition-all hover:bg-red-600/40 disabled:opacity-50"
                    data-testid="reaceptacion-eliminar-button"
                  >
                    Eliminar mi cuenta
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmandoBaja(false)}
                    className="flex-1 rounded-lg border-2 border-gray-600 bg-gray-700/70 py-3 text-sm font-bold text-white transition-all hover:bg-gray-600/70"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
