/**
 * Criterios A1-A4 de §5 de `spec-h1` (BOS-582), para el arreglo de H1 (BOS-596).
 *
 * **Por que este archivo existe y no un arnes de React:** el frontend de
 * Knowledge Wars no tiene infraestructura de pruebas -- `package.json` no trae
 * `@testing-library/*` ni configuracion de Jest, y no hay un solo archivo de
 * prueba de frontend en el repo. Montar ese arnes **no estaba autorizado** en
 * esta tarjeta. La ruta que si lo estaba: extraer la decision de hidratacion a
 * funciones puras (`src/lib/authHydration.mjs`) y ejercitarlas desde aqui con
 * `node --test` y un doble del cliente HTTP.
 *
 * Correr:  node --test frontend/tests/
 *
 * **Lo que esto NO cubre, dicho explicitamente** (va al gate corto del CEO):
 *
 * - No monta React. No se renderiza `ProtectedRoute` ni `AppContent`, asi que
 *   el *cableado* queda sin asercion automatica: que `ProtectedRoute` llame a
 *   `decidirRutaProtegida` y que el efecto de arranque llame a
 *   `hidratarSesion` esta verificado por lectura del diff, no por prueba.
 * - No hay `localStorage` ni DOM. La siembra de la sesion vieja se modela con
 *   el objeto `user` que el store habria hidratado, que es el valor con el que
 *   se decidia el muro; no se ejercita el `JSON.parse` de `store.js`.
 * - A5 (recorrido de navegador grabado) queda fuera por alcance: es el
 *   renglon B1 del alcance de Q1 y no esta financiado.
 */

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ACCION_ME,
  DESTINO_PROTEGIDO,
  ESTADO_AUTH,
  clasificarRespuestaMe,
  decidirRutaProtegida,
  esRutaPublica,
  hidratarSesion,
  normalizarResultadoMe,
} from '../src/lib/authHydration.mjs';

const TOKEN = 'token-de-sesion-vieja';

/** Un error de axios: resuelve solo en 2xx, y deja la respuesta en `.response`. */
function errorHttp(status, data) {
  const e = new Error(`HTTP ${status}`);
  e.response = { status, data };
  return e;
}

/** Un fallo de red: axios rechaza **sin** `.response`. */
function errorDeRed() {
  return new Error('Network Error');
}

/** Doble del cliente HTTP. Registra las rutas pedidas. */
function clienteFalso({ respuesta, error }) {
  const pedidos = [];
  return {
    pedidos,
    async get(ruta) {
      pedidos.push(ruta);
      if (error) throw error;
      return respuesta;
    },
  };
}

/**
 * Doble del store de zustand: el estado minimo con el que `ProtectedRoute`
 * decide, mas los dos efectos que `hidratarSesion` puede disparar. Replica a
 * proposito lo que hace `store/store.js` con `estadoAuth`.
 */
function storeFalso({ user, token = TOKEN }) {
  const store = {
    user,
    token,
    estadoAuth: token ? ESTADO_AUTH.HIDRATANDO : ESTADO_AUTH.SIN_SESION,
    llamadas: [],
  };
  store.setAuth = (u, t) => {
    store.llamadas.push('setAuth');
    store.user = u;
    store.token = t;
    store.estadoAuth = ESTADO_AUTH.VERIFICADA;
  };
  store.logout = () => {
    store.llamadas.push('logout');
    store.user = null;
    store.token = null;
    store.estadoAuth = ESTADO_AUTH.SIN_SESION;
  };
  /** Lo que `ProtectedRoute` renderizaria con el estado actual. */
  store.destino = () =>
    decidirRutaProtegida({ token: store.token, estadoAuth: store.estadoAuth, user: store.user });
  return store;
}

/** Corre la hidratacion y aplica el tercer caso como lo hace `useHidratacionDeSesion`. */
async function hidratar(store, cliente) {
  const decision = await hidratarSesion({
    token: store.token,
    cliente,
    setAuth: store.setAuth,
    logout: store.logout,
  });
  if (decision.accion === ACCION_ME.MARCAR_NO_VERIFICADA) {
    store.estadoAuth = decision.estadoAuth;
  }
  return decision;
}

// ---------------------------------------------------------------------------
// A1 -- sesion vieja sin la clave `legal`, el servidor dice que si requiere
//       reaceptacion: cae al muro en el primer render de una ruta protegida.
// ---------------------------------------------------------------------------

test('A1: sesion sin la clave `legal` cae al muro cuando el servidor dice que si', async () => {
  // Exactamente la sesion del defecto: guardada antes del despliegue, sin
  // `legal`. Con el codigo viejo `user?.legal?.requiere_reaceptacion` daba
  // `undefined` y el usuario entraba de largo.
  const store = storeFalso({ user: { id: 'u1', display_name: 'Ana' } });

  // Primero, el regresion-guard del defecto: antes de hablar con el servidor
  // NO se renderiza el contenido. Esto es lo que fallaba.
  assert.equal(store.destino(), DESTINO_PROTEGIDO.CARGANDO);
  assert.notEqual(store.destino(), DESTINO_PROTEGIDO.CONTENIDO);

  const cliente = clienteFalso({
    respuesta: {
      status: 200,
      data: { id: 'u1', display_name: 'Ana', legal: { requiere_reaceptacion: true } },
    },
  });

  const decision = await hidratar(store, cliente);

  assert.deepEqual(cliente.pedidos, ['/api/auth/me']);
  assert.equal(decision.accion, ACCION_ME.GUARDAR_SESION);
  assert.deepEqual(store.llamadas, ['setAuth']);
  assert.equal(store.estadoAuth, ESTADO_AUTH.VERIFICADA);
  assert.equal(store.destino(), DESTINO_PROTEGIDO.REACEPTACION);
});

// ---------------------------------------------------------------------------
// A2 -- la sesion local dice `false`, el servidor dice `true` (subio la version
//       del aviso): cae al muro.
// ---------------------------------------------------------------------------

test('A2: `requiere_reaceptacion: false` local pero `true` en el servidor cae al muro', async () => {
  const store = storeFalso({
    user: { id: 'u2', legal: { requiere_reaceptacion: false, version_aviso: '1.0' } },
  });

  // Control negativo del propio criterio: con el valor local, y solo con el
  // valor local, el muro no subiria. Es el defecto que A2 persigue.
  assert.equal(
    decidirRutaProtegida({
      token: TOKEN,
      estadoAuth: ESTADO_AUTH.VERIFICADA,
      user: store.user,
    }),
    DESTINO_PROTEGIDO.CONTENIDO,
  );

  const cliente = clienteFalso({
    respuesta: {
      status: 200,
      data: { id: 'u2', legal: { requiere_reaceptacion: true, version_aviso: '1.1' } },
    },
  });

  await hidratar(store, cliente);

  assert.equal(store.user.legal.version_aviso, '1.1');
  assert.equal(store.destino(), DESTINO_PROTEGIDO.REACEPTACION);
});

// ---------------------------------------------------------------------------
// A3 -- 401: cierra sesion, manda a `/login`, no renderiza nada protegido.
// ---------------------------------------------------------------------------

test('A3: un 401 cierra la sesion y manda a `/login`', async () => {
  const store = storeFalso({ user: { id: 'u3', legal: { requiere_reaceptacion: false } } });
  const cliente = clienteFalso({ error: errorHttp(401, { detail: 'Token expirado' }) });

  const decision = await hidratar(store, cliente);

  assert.equal(decision.accion, ACCION_ME.CERRAR_SESION);
  assert.equal(decision.redirigirALogin, true);
  assert.deepEqual(store.llamadas, ['logout']);
  assert.equal(store.user, null);
  assert.equal(store.token, null);
  assert.equal(store.estadoAuth, ESTADO_AUTH.SIN_SESION);
  assert.equal(store.destino(), DESTINO_PROTEGIDO.LOGIN);
});

// ---------------------------------------------------------------------------
// A4 -- sin respuesta del servidor: no se renderiza ninguna ruta protegida.
//       El muro se levanta, no se baja (§4.2).
// ---------------------------------------------------------------------------

test('A4: sin respuesta del servidor no se renderiza ninguna ruta protegida', async () => {
  // La sesion local dice que esta al corriente. Es precisamente el valor en el
  // que no se puede confiar: dice que lo estaba la ultima vez que entro.
  const store = storeFalso({ user: { id: 'u4', legal: { requiere_reaceptacion: false } } });
  const cliente = clienteFalso({ error: errorDeRed() });

  const decision = await hidratar(store, cliente);

  assert.equal(decision.accion, ACCION_ME.MARCAR_NO_VERIFICADA);
  // Un fallo de red no cierra la sesion -- el token puede seguir siendo bueno.
  assert.deepEqual(store.llamadas, []);
  assert.equal(store.estadoAuth, ESTADO_AUTH.NO_VERIFICADA);
  assert.equal(store.destino(), DESTINO_PROTEGIDO.NO_VERIFICADA);
  // La puerta trasera que §4.2 cierra: ni contenido, ni un `false` asumido.
  assert.notEqual(store.destino(), DESTINO_PROTEGIDO.CONTENIDO);
});

test('A4bis: un 500 o un 200 con cuerpo inservible tampoco bajan el muro', async () => {
  for (const cliente of [
    clienteFalso({ error: errorHttp(500, 'boom') }),
    clienteFalso({ error: errorHttp(503, null) }),
    clienteFalso({ respuesta: { status: 200, data: null } }),
    clienteFalso({ respuesta: { status: 200, data: 'ok' } }),
  ]) {
    const store = storeFalso({ user: { id: 'u5', legal: { requiere_reaceptacion: false } } });
    await hidratar(store, cliente);
    assert.equal(store.estadoAuth, ESTADO_AUTH.NO_VERIFICADA);
    assert.equal(store.destino(), DESTINO_PROTEGIDO.NO_VERIFICADA);
  }
});

// ---------------------------------------------------------------------------
// §4.4 y bordes
// ---------------------------------------------------------------------------

test('§4.4: `/privacidad`, `/terminos` y `/login` quedan fuera de la hidratacion', () => {
  for (const ruta of ['/privacidad', '/terminos', '/login', '/privacidad/', '/forgot-password']) {
    assert.equal(esRutaPublica(ruta), true, ruta);
  }
  for (const ruta of ['/home', '/lobby', '/store', '/match/abc', '/', '/privacidad/extra']) {
    assert.equal(esRutaPublica(ruta), false, ruta);
  }
  assert.equal(esRutaPublica(undefined), false);
});

test('sin token no se llama al servidor y la ruta protegida manda a `/login`', async () => {
  const cliente = clienteFalso({ respuesta: { status: 200, data: { id: 'x' } } });
  const decision = await hidratarSesion({ token: null, cliente, setAuth: () => {}, logout: () => {} });

  assert.deepEqual(cliente.pedidos, []);
  assert.equal(decision.estadoAuth, ESTADO_AUTH.SIN_SESION);
  assert.equal(decidirRutaProtegida({ token: null }), DESTINO_PROTEGIDO.LOGIN);
});

test('un `estadoAuth` desconocido cae en CARGANDO, no en CONTENIDO', () => {
  // El default seguro: cualquier estado que no sea VERIFICADA explicitamente no
  // renderiza nada protegido. Es lo que evita que un estado nuevo reintroduzca
  // H1 por omision.
  assert.equal(
    decidirRutaProtegida({ token: TOKEN, estadoAuth: 'algo_nuevo', user: {} }),
    DESTINO_PROTEGIDO.CARGANDO,
  );
  assert.equal(
    decidirRutaProtegida({ token: TOKEN, estadoAuth: undefined, user: {} }),
    DESTINO_PROTEGIDO.CARGANDO,
  );
});

test('normalizarResultadoMe representa «sin respuesta» como `status: null`', () => {
  assert.deepEqual(normalizarResultadoMe({ error: errorDeRed() }), { status: null, data: undefined });
  assert.deepEqual(normalizarResultadoMe({ error: errorHttp(401, { d: 1 }) }), {
    status: 401,
    data: { d: 1 },
  });
  assert.equal(normalizarResultadoMe({ respuesta: { status: 200, data: { a: 1 } } }).status, 200);
  assert.equal(clasificarRespuestaMe({ status: null }).estadoAuth, ESTADO_AUTH.NO_VERIFICADA);
  assert.equal(clasificarRespuestaMe().estadoAuth, ESTADO_AUTH.NO_VERIFICADA);
});
