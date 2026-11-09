import React from 'react';
import DocumentoLegalPage from './DocumentoLegalPage';

// `/privacidad` -- publica y sin credencial (BOS-351, §3.1).
export default function PrivacidadPage() {
  return <DocumentoLegalPage recurso="privacidad" titulo="el aviso de privacidad" />;
}
