import React from 'react';
import DocumentoLegalPage from './DocumentoLegalPage';

// `/terminos` -- publica y sin credencial (BOS-351, §3.1).
export default function TerminosPage() {
  return <DocumentoLegalPage recurso="terminos" titulo="los terminos de uso" />;
}
