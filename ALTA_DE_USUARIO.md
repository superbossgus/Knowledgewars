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

## El rescate de contraseña ya no es un take-over, y por eso necesita correo

Al quitar Google, «olvidé mi contraseña» quedó como el único rescate de las
cuentas sin contraseña, así que se revisó entero (BOS-353). Lo que se encontró
no lo había introducido ese cambio: estaba en `main` y aplicaba a todas las
cuentas.

`POST /api/auth/forgot-password` devolvía en la **respuesta HTTP** el código de
6 dígitos (`_dev_code`) y el `reset_token`. Con cualquiera de los dos, quien
llamara al endpoint con un correo ajeno se quedaba con la cuenta — y el token
solo bastaba, porque `/api/auth/reset-password` no pide el código. Ya no sale
ninguno de los dos: el código solo viaja por correo.

Lo que cambió, en dos tandas. La primera (BOS-353, PR #10) cerró el take-over:

- el código se genera con `secrets`, no con `random`;
- ni el código ni el `reset_token` salen en la respuesta HTTP: el código solo
  viaja por correo, y la respuesta es idéntica para un correo que existe y uno
  que no;
- cinco intentos fallidos en `verify-reset-code` agotaban el token;
- `forgot-password` tiene tope de solicitudes: 3 por correo cada 15 minutos y
  20 por IP cada hora, con `429` y `Retry-After`;
- el envío vive en `backend/mailer.py` y habla **SMTP**, no la API de un
  proveedor concreto, así que elegir proveedor es poner variables de entorno.

La segunda (BOS-359, PR #11) cerró tres huecos que la primera dejó abiertos:

- **`verify-reset-code` ya no dice si un correo está registrado.** El código
  vencido de una cuenta real y un correo que no existe contestan el mismo `400`
  byte por byte, y `expires_at` pasó a ser índice **TTL**, así que el documento
  vencido desaparece solo en vez de esperar la siguiente solicitud.
- **El quinto fallo ya no quema el token.** Los cinco intentos se cuentan en una
  ventana móvil de 5 minutos, más corta que los 15 de vida del token, así que el
  presupuesto se repone. Lo que se retiró era un lever de denegación: un tercero
  que solo supiera el correo podía dejar la cuenta sin rescate indefinidamente,
  a cinco llamadas y cero espera por token. El costo es que el presupuesto por
  token sube de 5 a 15 intentos — 15 en 10⁶, y 45 por correo cada cuarto de
  hora. Ese intercambio se aprobó con los números escritos en BOS-360.
- **`verify-reset-code` estrena su propio tope por IP cada hora**, mirado
  antes de tocar la base, así que el `429` es idéntico para un correo que existe
  y uno que no. No hay tope por correo a propósito: el presupuesto de intentos
  ya es por correo (solo vive un token por correo a la vez), y un cubo por
  correo sí se podría apuntar a una víctima concreta. Un tope por IP no. (Salió
  en 30 y la tercera tanda lo subió a 90; ver abajo.)
- **Una solicitud rechazada por el tope de IP ya no gasta cuota del tope por
  correo.** `forgot-password` mira los dos cubos y registra después, así que el
  usuario del salón de evento que choca con el tope de IP conserva sus tres
  solicitudes enteras.

La tercera (BOS-361, PR #13) cerró tres bordes que la segunda dejó abiertos:

- **El tope de verify por IP sube de 30 a 90 por hora.** 30 estaba **por debajo
  del tráfico legítimo que el propio tope de `forgot-password` deja generar desde
  esa misma IP**: 20 personas detrás de un NAT pueden pedir su código y cada una
  necesita 1 a 3 llamadas de verify, o sea hasta 60. Medido, solo 10 de 20
  personas de un salón de evento completaban el rescate, y la 11 se quedaba
  esperando casi una hora con un código en la mano que vive 15 minutos — se le
  vencía antes de que la ventana se liberara. `3 × 20 = 60` es el techo del
  tráfico legítimo; con margen, 90. **Sí afloja una capa — la que no estaba
  deteniendo nada.** Un tope por IP no solo acota cuántas cuentas *distintas*
  golpea una máquina: también acota los intentos contra *una* cuenta desde esa
  IP, y ese número es justo el que se triplicó. Lo que de verdad ataba una
  fuerza bruta dirigida está encima y no se movió: el presupuesto por correo son
  3 tokens cada cuarto de hora, 15 intentos cada uno, o sea **180 intentos por
  hora** contra una víctima concreta — ni 30 ni 90 eran la restricción que
  mordía ahí. Un atacante con dos IPs ya igualaba las 60 y con seis tenía las
  180 enteras, porque un tope por IP se evade con proxies y nunca fue el control
  serio contra alguien decidido. La aritmética sigue siendo mala para él: 90 en
  10⁶ es **0.009% por hora** desde una IP. O sea que el cambio afloja la capa
  que no mordía y a cambio arregla un daño medido y seguro.
- **La ventana de intentos se escribe atómica.** Era un read-modify-write: se
  leía el documento, se podaba en Python y se reescribía la lista entera. No era
  explotable por arquitectura y no por diseño — el handler no tiene un solo
  `await` entre la lectura y la escritura, así que con un worker corría atómico
  —, pero se volvía real con más de un worker de uvicorn o más de una instancia.
  Ahora el fallo se agrega con `$push` y la ventana se poda con `$pull` por
  fecha, así que la escritura no depende de lo que se leyó.
- **`password_reset_requests` estrena índice TTL sobre `created_at`**, con la
  vida de la ventana más larga de los cubos (3600 s). La poda era por llave y
  perezosa, así que los renglones de una llave que no se vuelve a consultar
  nunca se quedaban para siempre, y el PR #11 lo aceleró: `verify-reset-code`
  escribe un renglón por llamada. El cluster es un M0 de 512 MB. El TTL tiene
  que ser **≥ la ventana más larga** o borraría renglones que todavía cuentan
  para un tope, y hay una prueba que amarra las dos constantes para que nunca se
  separen.

Fijado por `backend/tests/test_recuperacion_de_contrasena.py`
(**143 verificaciones**, en verde con mongomock y contra Mongo real, reproducidas
contra `main` ya mergeado).

**Esto es lo que falta para poder abrir el alta:** sin `SMTP_HOST` y `SMTP_FROM`
configurados no sale ningún correo, y entonces el rescate no funciona — el
endpoint contesta lo mismo, pero el usuario no recibe nada. Es a propósito:
entre «no se puede recuperar» y «cualquiera se toma la cuenta», se elige lo
primero. **Mientras no haya cuenta de envío, no se da de alta al primer usuario
real**, porque una cuenta cuya contraseña se olvide queda perdida.

### Lo que sigue del rescate, y por qué el siguiente paso no es otro tope

Queda una cosa abierta. No bloquea el alta por sí sola; la cuenta de envío de
arriba sigue siendo la única condición dura.

- **BOS-362 — el rescate por enlace con token de 128 bits.** Es el arreglo de
  fondo: un token de 128 bits no se adivina, así que no necesita tope de
  intentos, y sin tope de intentos no hay nada que un tercero pueda quemar. Eso
  borra de raíz el oráculo de existencia, el bloqueo del rescate y el
  dimensionamiento de los dos topes. Cambia la **pantalla de recuperación**, así
  que la decisión va con un plan de prueba de navegador (como BOS-355) y no de
  corrido. **Mientras eso no se decida, no se agregan más topes sobre el código
  de 6 dígitos:** el secreto tiene 10⁶ combinaciones y el siguiente movimiento
  en ese camino es cambiar el secreto, no el tope. (El PR #13 no agregó ninguno:
  subió uno que estaba mal dimensionado y dejó el resto igual.)

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
