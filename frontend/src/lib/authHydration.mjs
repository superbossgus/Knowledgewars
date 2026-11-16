/**
 * La decision de hidratar la sesion contra el servidor.
 *
 * Arreglo de H1 (BOS-596), implementando §4 de `spec-h1` (BOS-582).
 *
 * **El defecto que esto corrige:** `store/store.js` hidrataba `user` una sola
 * vez desde `localStorage`, al importar el modulo, y nada lo refrescaba contra
 * el servidor en el arranque. Para una sesion guardada antes del despliegue el
 * objeto no traia la clave `legal`, asi que
 * `user?.legal?.requiere_reaceptacion` daba `undefined` -- falso -- y el muro
 * de reaceptacion **no se levantaba justamente para la poblacion a la que esta
 * dirigido**: los usuarios que ya existian. Lo mismo pasaba en cada subida de
 * version del aviso: quien tuviera sesion abierta conservaba el
 * `requiere_reaceptacion: false` de su ultimo ingreso.
 *
 * **Por que vive fuera de React y sin un solo `import`:** el frontend de
 * Knowledge Wars no tiene infraestructura de pruebas -- no hay
 * `@testing-library/*` ni configuracion de Jest en `package.json`, y montar ese
 * arnes no estaba autorizado en esta tarjeta. Al dejar la *decision* en
 * funciones puras, los criterios A1-A4 de la especificacion se ejercitan desde
 * `tests/auth-hydration.test.mjs` con `node --test` y un doble del cliente
 * HTTP, sin React, sin DOM y sin navegador.
 */

/** En que punto esta la sesion respecto del servidor. */
export const ESTADO_AUTH = Object.freeze({
  /** Hay token, pero todavia no lo hemos confrontado con el servidor. */
  HIDRATANDO: 'hidratando',
  /** El servidor contesto 200: `user` viene de el, no de `localStorage`. */
  VERIFICADA: 'verificada',
  /** El servidor no contesto. Eso no es evidencia de nada (§4.2). */
  NO_VERIFICADA: 'no_verificada',
  /** No hay token, o el servidor contesto 401. */
  SIN_SESION: 'sin_sesion',
});

/** Que hacer con el resultado de `GET /api/auth/me`. */
export const ACCION_ME = Object.freeze({
  GUARDAR_SESION: 'guardar_sesion',
  CERRAR_SESION: 'cerrar_sesion',
  MARCAR_NO_VERIFICADA: 'marcar_no_verificada',
});

/** Que renderiza una ruta protegida. */
export const DESTINO_PROTEGIDO = Object.freeze({
  LOGIN: 'login',
  CARGANDO: 'cargando',
  NO_VERIFICADA: 'no_verificada',
  REACEPTACION: 'reaceptacion',
  CONTENIDO: 'contenido',
});

/**
 * §4.4 -- las rutas que **no** esperan a la hidratacion y de las que tampoco
 * se echa al usuario por un token caducado. Las tres primeras estan nombradas
 * en la especificacion: el usuario tiene que poder leer lo que se le pide
 * aceptar, y poder salirse. `/forgot-password` entra por la misma razon --
 * se llega ahi precisamente porque no se puede entrar.
 */
export const RUTAS_PUBLICAS = Object.freeze([
  '/login',
  '/privacidad',
  '/terminos',
  '/forgot-password',
]);

export function esRutaPublica(pathname) {
  if (typeof pathname !== 'string') return false;
  const limpia = pathname.replace(/\/+$/, '') || '/';
  return RUTAS_PUBLICAS.includes(limpia);
}

/**
 * Clasifica el resultado de `GET /api/auth/me` ya normalizado.
 *
 * `status` es `null` cuando no hubo respuesta del servidor (fallo de red).
 */
export function clasificarRespuestaMe({ status, data } = {}) {
  if (status === 401) {
    return {
      accion: ACCION_ME.CERRAR_SESION,
      estadoAuth: ESTADO_AUTH.SIN_SESION,
      redirigirALogin: true,
    };
  }

  if (status === 200 && data && typeof data === 'object') {
    return {
      accion: ACCION_ME.GUARDAR_SESION,
      estadoAuth: ESTADO_AUTH.VERIFICADA,
      redirigirALogin: false,
      user: data,
    };
  }

  // Todo lo demas cae aqui: fallo de red (`status: null`), 500, 503, o un 200
  // con un cuerpo que no es un objeto. §4.2 -- sin respuesta util del servidor
  // el muro se levanta, no se baja. Lo que hay en `localStorage` no es
  // evidencia de que el usuario este al corriente; es evidencia de que lo
  // estaba la ultima vez que entro. Un fallo de red no puede ser la puerta
  // trasera que salte el muro.
  return {
    accion: ACCION_ME.MARCAR_NO_VERIFICADA,
    estadoAuth: ESTADO_AUTH.NO_VERIFICADA,
    redirigirALogin: false,
  };
}

/**
 * §4.3 -- que renderiza `ProtectedRoute`.
 *
 * Cualquier `estadoAuth` que no sea VERIFICADA explicitamente cae en CARGANDO.
 * Es a proposito: el defecto original era decidir con un valor que todavia no
 * se habia verificado, y un parpadeo que muestre la pantalla protegida medio
 * segundo antes de corregirse sigue siendo el mismo defecto, mas corto.
 */
export function decidirRutaProtegida({ token, estadoAuth, user } = {}) {
  if (!token) return DESTINO_PROTEGIDO.LOGIN;
  if (estadoAuth === ESTADO_AUTH.SIN_SESION) return DESTINO_PROTEGIDO.LOGIN;
  if (estadoAuth === ESTADO_AUTH.NO_VERIFICADA) return DESTINO_PROTEGIDO.NO_VERIFICADA;
  if (estadoAuth !== ESTADO_AUTH.VERIFICADA) return DESTINO_PROTEGIDO.CARGANDO;
  if (user?.legal?.requiere_reaceptacion) return DESTINO_PROTEGIDO.REACEPTACION;
  return DESTINO_PROTEGIDO.CONTENIDO;
}

/**
 * Normaliza lo que devuelve el cliente HTTP a `{ status, data }`.
 *
 * axios resuelve solo en 2xx y rechaza en todo lo demas, dejando la respuesta
 * en `error.response`. Si no hay `error.response` es que no hubo respuesta del
 * servidor, y eso se representa con `status: null`.
 */
export function normalizarResultadoMe({ respuesta, error } = {}) {
  if (error) {
    return {
      status: error?.response?.status ?? null,
      data: error?.response?.data,
    };
  }
  return {
    status: respuesta?.status ?? 200,
    data: respuesta?.data,
  };
}

/**
 * §4.1 -- rehidrata la sesion contra `GET /api/auth/me` y aplica el efecto.
 *
 * `cliente` es inyectable (en la app es la instancia de axios de `lib/api`);
 * en las pruebas es un doble. Devuelve el `estadoAuth` resultante y si hay que
 * mandar al usuario a `/login`; quien llama se encarga de navegar, porque la
 * navegacion es de React Router y esto tiene que poder correr sin React.
 */
export async function hidratarSesion({ token, cliente, setAuth, logout } = {}) {
  if (!token) {
    return {
      accion: null,
      estadoAuth: ESTADO_AUTH.SIN_SESION,
      redirigirALogin: false,
    };
  }

  let crudo;
  try {
    const respuesta = await cliente.get('/api/auth/me');
    crudo = normalizarResultadoMe({ respuesta });
  } catch (error) {
    crudo = normalizarResultadoMe({ error });
  }

  const decision = clasificarRespuestaMe(crudo);

  if (decision.accion === ACCION_ME.GUARDAR_SESION) {
    setAuth(decision.user, token);
  } else if (decision.accion === ACCION_ME.CERRAR_SESION) {
    logout();
  }

  return decision;
}
