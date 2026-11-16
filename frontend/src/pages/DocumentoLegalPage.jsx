import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, ArrowLeft } from 'lucide-react';
import api from '../lib/api';
import renderLegal from '../lib/legalMarkdown';

/**
 * Pantalla comun de `/privacidad` y `/terminos` (BOS-351, criterio §3.1).
 *
 * Es **publica**: no va dentro de `ProtectedRoute` y no manda credencial.
 * Quien tiene que decidir si acepta no puede necesitar una cuenta para leer lo
 * que va a aceptar, y el enlace tiene que servir pegado en un correo o en una
 * cotizacion.
 *
 * El texto no vive aqui: lo sirve el backend desde el archivo congelado de esa
 * version (`backend/legal/*.md`). Es la misma fuente cuyo hash se guarda en el
 * renglon de consentimiento, asi que la pantalla no puede mostrar algo distinto
 * de lo que se acredito.
 */
export default function DocumentoLegalPage({ recurso, titulo }) {
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let vivo = true;
    api
      .get(`/api/legal/${recurso}`)
      .then((res) => {
        if (vivo) setDoc(res.data);
      })
      .catch(() => {
        if (vivo) setError(true);
      });
    return () => {
      vivo = false;
    };
  }, [recurso]);

  return (
    <div className="min-h-screen hero-gradient">
      <div className="noise-overlay" />
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="relative z-10 mx-auto max-w-3xl px-4 py-10"
      >
        <div className="mb-6 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Shield
              className="h-8 w-8 text-[hsl(220,100%,50%)]"
              style={{ filter: 'drop-shadow(0 0 10px hsl(220 100% 50%))' }}
            />
            <span className="font-brand text-xl font-extrabold text-white">KNOWLEDGE WARS</span>
          </div>
          <Link
            to="/login"
            className="flex items-center gap-1 text-sm text-[hsl(220,100%,70%)] transition-colors hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver
          </Link>
        </div>

        <div
          className="rounded-2xl border-2 border-[hsl(220,100%,50%,0.3)] bg-[hsl(220,28%,10%,0.85)] p-6 shadow-2xl backdrop-blur-xl md:p-10"
          style={{ boxShadow: '0 0 40px hsl(220 100% 50% / 0.15)' }}
        >
          {error && (
            <p className="text-white/80" data-testid="legal-error">
              No pudimos cargar este documento. Vuelve a intentarlo en un momento.
            </p>
          )}

          {!error && !doc && (
            <p className="text-white/60" data-testid="legal-cargando">
              Cargando {titulo}...
            </p>
          )}

          {doc && (
            <article data-testid={`legal-${recurso}`}>
              {renderLegal(doc.texto)}
              {/* La version y el hash a la vista, a proposito: es lo que permite
                  comprobar que el texto que se esta leyendo es el mismo que
                  acredita el renglon de consentimiento. */}
              <p className="mt-10 border-t border-white/10 pt-4 font-mono text-xs text-white/40">
                Version {doc.version} · SHA-256 {doc.hash}
              </p>
            </article>
          )}
        </div>
      </motion.div>
    </div>
  );
}
