# Caminos de alta de usuario, y de qué cuelgan

Knowledge Wars nació en Emergent, la plataforma que la unidad dejó en abril de
2026. El login con Google colgaba de dos dominios de Emergent. Este documento
dice qué se midió, qué funciona sin ellos y qué costó quitarlos.

Medido el **24 de octubre de 2026** (BOS-350). Hallazgo original en BOS-125.

## Estado: se eligió la opción A y ya está hecha

**El 24 de octubre de 2026 se decidió quitar Google y quedarse con el alta por
correo** (opción A de este documento). Está implementado:

- `POST /api/auth/google/session` **ya no existe**. En su lugar quedó una
  lápida en `backend/server.py` que dice qué había ahí y por qué se fue.
- El botón «Continuar con Google» y el procesamiento del `session_id` del
  fragmento **ya no están** en `frontend/src/pages/LoginPage.jsx`. Ningún
  código vivo del repo le habla a `emergentagent.com`.
- **Las cuentas viejas de Google no quedaron encerradas.** El login ya no les
  dice «usa Google»: las manda a «olvidé mi contraseña», y se le quitó a
  `forgot_password()` la rama que a ellas les negaba el código. Al ponerse
  contraseña, su `auth_provider` pasa de `"google"` a `"email"`.
- El cookie `session_token` **se sigue aceptando a propósito**, para no
  expulsar a una sesión que siga viva en el navegador de alguien (las de
  `remember_me` duraban 100 años). Lo que ya no ocurre es que se emitan
  cookies nuevos: nada escribe en `user_sessions`. Se puede borrar esa pieza
  cuando se confirme que la colección está vacía en producción.

Todo lo anterior está fijado por `backend/tests/test_alta_sin_google.py`
(39 verificaciones). Lo que sigue de este documento es la medición que llevó a
la decisión; se deja tal cual porque es la evidencia.

## Había dos caminos de alta, y solo uno era nuestro

Esto es lo que se encontró el 24 de octubre, antes de quitar Google:

| # | Camino | Endpoint | Depende de Emergent | ¿Servía? |
|---|--------|----------|---------------------|----------|
| 1 | Correo y contraseña | `POST /api/auth/register` | **No** | **Sí, completo** — es el que quedó |
| 2 | Google | `POST /api/auth/google/session` | **Sí, dos dominios** | Dudoso — **quitado**, ver arriba |

No hay un tercer camino: no hay Apple, ni Facebook, ni teléfono, ni invitación.
Los otros endpoints bajo `/api/auth/` (`login`, `me`, `logout`,
`forgot-password`, `verify-reset-code`, `reset-password`) son de sesión y de
recuperación, no de alta.

### El camino 1 está completo y se sostiene solo

`register()` hace todo lo que hace falta para que alguien se registre y juegue,
sin salir de nuestro backend:

- valida que el correo no exista;
- guarda la contraseña con hash;
- crea la cuenta con ELO inicial 500, rango e idioma;
- **da 5 partidas gratis** (`games_remaining: 5`), así que la cuenta nueva
  puede jugar de inmediato sin pagar nada;
- devuelve un JWT ya listo, así que el registro deja al usuario dentro, sin un
  segundo paso de login.

El frontend lo usa en `frontend/src/pages/LoginPage.jsx`, en el mismo
formulario que el login, con un interruptor «registrarse / entrar».

**Conclusión para la puerta P3: el alta de usuario no depende de Emergent.**
Alguien puede registrarse y jugar con correo y contraseña aunque los dos dominios
de Emergent desaparezcan mañana. La métrica 3 se puede medir sin tocar el login
con Google.

### El camino 2 cuelga de dos dominios ajenos

El flujo de Google tiene dos piezas de Emergent, no una:

1. **La página de consentimiento.** El frontend mandaba al usuario a
   `https://auth.emergentagent.com/?redirect=...`, que regresaba con un
   `session_id` en el fragmento de la URL.
2. **El canje del `session_id`.** El backend lo cambiaba por los datos del
   usuario contra
   `https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data`,
   mandando el `session_id` en la cabecera `X-Session-ID`.

Las dos tenían que funcionar. Si la primera fallaba, el usuario nunca llegaba
a la segunda.

## Qué contestaron los dominios

Sondas HTTPS sin ninguna credencial nuestra: solo se midió si el servicio
responde. DNS y TLS resolvieron bien en los dos casos.

### `demobackend.emergentagent.com` — vivo

| Petición | Código | Tiempo | Cuerpo |
|---|---|---|---|
| `GET /auth/v1/env/oauth/session-data` con `X-Session-ID` inventado | **404** | 126 ms | `{"detail":{"error":"user_data_not_found","error_description":"User data not found or expired"}}` |
| El mismo, sin la cabecera | **422** | 108 ms | `{"detail":[{"type":"missing","loc":["header","X-Session-ID"],"msg":"Field required"}]}` |
| `GET /` (control) | 404 | 105 ms | `{"error":"Route not found"}` |

Esto es un servicio **funcionando**, no un dominio apagado. El 404 es la
respuesta correcta a una sesión que no existe, y el 422 prueba que la ruta existe
y valida la cabecera (es un FastAPI contestando). `Server: Google Frontend`,
detrás de un IP de Google Cloud (34.102.203.0). El certificado TLS se renovó el
**11 de septiembre de 2026** y vence el 10 de diciembre de 2026: alguien sigue
manteniendo esto seis meses después de que nosotros nos fuimos.

### `auth.emergentagent.com` — degradado, y ya se mudó

| Petición | Código | Tiempo | Qué llegó |
|---|---|---|---|
| `GET /` (redirige a `/oauth/`) | **404** | 474 ms | HTML de una SPA, 26 919 bytes, `Server: AmazonS3`, `X-Cache: Error from cloudfront` |
| `GET /?redirect=https://ejemplo.test/login` | **404** | 459 ms | el mismo HTML |
| `GET https://emergentagent.com/` (control) | 200 | 310 ms | redirige a `https://app.emergent.sh/landing/` |

Tres cosas:

1. La URL que usa nuestro frontend **contesta 404**, y CloudFront lo reporta como
   error de origen. Lo que llega es el cascarón de una SPA fechado el 9 de julio
   de 2026, así que *puede* que la aplicación arranque de todos modos y enrute
   del lado del cliente — con 404 y todo. No lo puedo afirmar: verificarlo
   necesita un navegador de verdad y una cuenta de Emergent, y ninguna de las dos
   cosas está en esta tarea.
2. **Emergent movió su auth.** El dominio raíz ahora manda a `app.emergent.sh`, y
   las respuestas traen `X-Auth-Proxy-Cohort: treatment` y una cookie
   `auth-host-cohort` en `.emergent.sh`. Están repartiendo tráfico entre un host
   de auth nuevo y el viejo. El viejo es el nuestro.
3. El cascarón busca en `localStorage` llaves `sb-*-auth-token`, o sea
   **Supabase**: la página de consentimiento es una pantalla de la plataforma
   Emergent, no una pantalla de Google. Nuestros usuarios estarían pasando por el
   login de un producto ajeno para entrar al nuestro.

### Lo que esto significa

El login con Google **no está muerto hoy**, pero tampoco está vivo de una forma
que se pueda defender:

- funciona (si funciona) porque un tercero que no nos debe nada sigue pagando la
  cuenta de AWS y de Google Cloud;
- el `session_id` lo emite ese tercero y nosotros lo creemos sin verificar nada:
  quien controle ese dominio controla quién entra a Knowledge Wars;
- ya hay señal de migración (el `X-Auth-Proxy-Cohort`), y el día que apaguen el
  host viejo nadie nos va a avisar;
- `auth.emergentagent.com` ya contesta 404 en la ruta que usamos.

Y hay un detalle de operación que no se ve en el código: el `session_id` dura
poco ("not found **or expired**"). Un login con Google que falle en producción se
va a ver como un error intermitente imposible de reproducir.

## Propuesta de reemplazo — sin implementar, con costo primero

No toqué nada de esto. El flujo de sesión es donde vive el `JWT_SECRET` que sigue
expuesto en el repo público, y eso es de BOS-136 con un permiso aparte de
Gustavo. Dos cambios encimados en la misma pieza es exactamente lo que no
queremos. Aquí están las tres opciones con alcance y estimación para que se
elija.

### Opción A — quitar Google, quedarse con correo ✅ ELEGIDA E IMPLEMENTADA

Borrar el botón de Google y el endpoint `/api/auth/google/session`, y dejar el
alta con correo que ya funciona.

- **Qué se toca:** `LoginPage.jsx` (el botón, el manejador y el procesamiento del
  `session_id` del fragmento), `server.py` (borrar un endpoint), y una migración
  mínima para las cuentas existentes con `auth_provider: "google"` y sin
  contraseña — el login les decía «usa Google», y sin Google quedarían
  encerradas. Se resuelve mandándolas por «olvidé mi contraseña», que ya
  existe, **pero hay que quitarle una rama**: `forgot_password()` les contestaba
  «esta cuenta usa Google Sign-In» en vez de mandarles el código, así que tal
  como estaba no las rescataba. Son dos renglones.
- **Alcance:** ~1 día de trabajo, incluidas pruebas.
- **Riesgo:** bajo. No toca la emisión del JWT, solo quita un camino de entrada.
  Es la única de las tres que **no se encima con BOS-136**.
- **Costo:** $0.
- **Lo que cuesta de verdad:** fricción en el registro. Un formulario con
  contraseña convierte peor que un botón de Google. Con 100 jugadores de meta, eso
  importa menos que con 100 000, pero importa.

### Opción B — OAuth directo contra Google

Hablarle a Google nosotros, sin intermediario: `accounts.google.com` para el
consentimiento y verificación del `id_token` contra las llaves públicas de
Google.

- **Qué se toca:** una credencial OAuth nueva en Google Cloud Console (la hace
  Gustavo, es suya), `google-auth` como dependencia nueva del backend, reescribir
  `/api/auth/google/session` para recibir un `id_token` en vez de un `session_id`,
  y cambiar el redirect del frontend.
- **Alcance:** ~2 a 3 días. **Toca el flujo de sesión**, así que va después de
  BOS-136, no en paralelo.
- **Riesgo:** medio. Verificar un `id_token` mal es una vulnerabilidad de
  autenticación, no un bug. Necesita revisión de seguridad.
- **Costo:** $0 — las credenciales OAuth de Google son gratis. Requiere que
  Gustavo cree el proyecto y las llaves, y que haya un dominio de producción
  registrado como origen autorizado.
- **A favor:** elimina al tercero de la cadena y conserva el botón de Google.

### Opción C — no hacer nada todavía

Dejar el botón como está, sabiendo que cuelga de Emergent.

- **Costo:** $0 hoy. El día que Emergent apague el host viejo, el botón empieza a
  fallar en producción y el arreglo es la opción A o la B, pero con usuarios
  mirando.
- **Cuándo tiene sentido:** si Q1 arranca con el alta por correo y el botón de
  Google es un extra que se puede perder sin apagar el producto.

### Mi recomendación (la que se siguió)

**A ahora, B después, y nunca C a ciegas.** Concretamente:

1. Para abrir la puerta P3 no hace falta nada: el alta por correo ya funciona.
2. Antes de que entren usuarios de verdad, quitar el botón de Google (opción A) o
   ponerle una advertencia. Un botón que falla intermitentemente por culpa de un
   proveedor que ya no es nuestro es peor que no tener el botón.
3. Si se quiere Google de vuelta, la opción B va **después** de BOS-136, cuando
   el `JWT_SECRET` ya esté rotado y el flujo de sesión tenga un solo dueño.

Los puntos 1 y 2 están hechos. El punto 3 sigue abierto y no tiene fecha.

## Cómo reproducir las sondas

Las sondas no mandan ninguna credencial y no necesitan las de BOS-343. Son dos
peticiones HTTPS:

```bash
# el canje del session_id: debe contestar 404 user_data_not_found
curl -sS -i -H "X-Session-ID: sonda" \
  https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data

# la pagina de consentimiento: hoy contesta 404
curl -sS -i -L "https://auth.emergentagent.com/?redirect=https%3A%2F%2Fejemplo.test%2Flogin"
```

## Lo que no se verificó

- **Si el botón de Google funciona de punta a punta.** Necesita un navegador, una
  cuenta de Google y el backend desplegado con las credenciales de BOS-343. Es
  trabajo de QA con un plan de prueba, no de una sonda HTTPS.
- **Si el alta por correo funciona contra Atlas.** Las pruebas de este repo
  corren contra Mongo local; el camino completo contra el cluster se verifica
  cuando BOS-163 despierte.
