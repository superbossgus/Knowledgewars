import React from 'react';
import { Link, useLocation } from 'react-router-dom';

/**
 * `Terminos · Privacidad` en el pie de **todas** las pantallas (BOS-351, §3.1).
 *
 * El criterio legal pide que los dos documentos sean alcanzables desde
 * cualquier pantalla, no solo desde el registro: el usuario que quiere revisar
 * a que dijo si no deberia tener que cerrar la sesion para encontrarlo.
 *
 * Se esconde en la partida (`/match/...`) porque ahi la pantalla esta
 * cronometrada y a pantalla completa; el pie reaparece en cuanto termina. Y se
 * esconde en las propias paginas legales, que ya traen su enlace de vuelta.
 */
export default function LegalFooter() {
  const { pathname } = useLocation();
  const oculto =
    pathname.startsWith('/match/') || pathname === '/privacidad' || pathname === '/terminos';
  if (oculto) return null;

  return (
    <footer
      className="relative z-10 flex items-center justify-center gap-2 py-6 text-xs text-white/40"
      data-testid="legal-footer"
    >
      <Link to="/terminos" className="transition-colors hover:text-white/80">
        Terminos
      </Link>
      <span aria-hidden="true">·</span>
      <Link to="/privacidad" className="transition-colors hover:text-white/80">
        Privacidad
      </Link>
    </footer>
  );
}
