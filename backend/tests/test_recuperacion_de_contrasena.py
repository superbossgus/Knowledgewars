"""
El rescate de contrasena ya no es un take-over de cualquier cuenta (BOS-353).

Hasta este cambio, `POST /api/auth/forgot-password` devolvia en la respuesta
HTTP el codigo de 6 digitos (`_dev_code`) **y** el `reset_token`. Cualquiera que
llamara al endpoint con un correo ajeno se quedaba con la cuenta, y con el token
le bastaba: `/api/auth/reset-password` no pide el codigo, solo el token. No lo
introdujo ningun PR reciente -- estaba en `main` y aplicaba a todas las cuentas
con contrasena.

Lo que esta prueba fija, en capas:

  1. la respuesta de `forgot-password` **no lleva el codigo ni el token**, y es
     identica para un correo que existe y para uno que no (no dice quien esta
     registrado)
  2. el codigo lo genera `secrets`, no `random`. Se comprueba de dos formas: el
     AST de `server.py` no nombra `random` en ninguna parte, y una sonda sobre
     `secrets.randbelow` confirma que de ahi sale cada codigo
  3. **cinco intentos fallidos agotan la ventana**: despues ni el codigo
     correcto sirve. Cuatro fallos seguidos de un acierto si pasan. El token
     **no** se quema (ver capa 8)
  4. `forgot-password` tiene tope por correo y por IP: el cuarto intento con el
     mismo correo en 15 minutos contesta 429 con `Retry-After`, y otro correo
     sigue pasando
  5. el flujo legitimo corre de punta a punta -- pedir, recibir por correo,
     verificar, poner contrasena, entrar -- leyendo el codigo del correo que
     salio, que es el unico lugar donde existe
  6. el arranque **rechaza** `PASSWORD_RESET_LOG_CODE` encendida fuera de
     desarrollo, y la bandera esta apagada por omision
  7. el `mailer` no manda nada sin configurar, no acepta una direccion con un
     salto de linea (inyeccion de cabeceras) y lleva el codigo en el cuerpo
  8. los tres huecos de BOS-359, que el PR anterior dejo abiertos:
     - `verify-reset-code` ya **no** dice si un correo esta registrado: el
       codigo vencido y el correo que no existe contestan el mismo 400 byte por
       byte, y `expires_at` es un indice TTL
     - un tercero ya **no** puede dejar la cuenta sin rescate sabiendo solo el
       correo: la ventana de intentos se repone y el token no se quema, y
       `verify-reset-code` tiene su propio tope por IP
     - una solicitud rechazada por el tope de IP ya **no** gasta cuota del tope
       por correo
  9. las tres cosas que ese mismo PR dejo abiertas (BOS-361):
     - el salon de evento **completo** alcanza a verificar: 20 cuentas desde una
       sola IP, con dos tecleos malos cada una, y ninguna se come un 429. El tope
       de verify por IP estaba en 30, mas chico que el trafico legitimo que el
       tope de forgot (20/hora) deja generar desde esa misma IP
     - el contador que gatea los 5 intentos se escribe **atomico**: `$push` para
       agregar y `$pull` por fecha para podar, nunca un `$set` de una lista
       calculada en Python
     - el cubo de cuotas tiene **TTL** sobre `created_at`, y con la vida de la
       ventana mas larga, no con el `expireAfterSeconds=0` que sobre ese campo
       apagaria los topes

Lo que NO toca este cambio, y sigue en verde aqui: los 15 minutos de
expiracion, el uso unico del token y la respuesta igual para un correo que no
existe.

    python backend/tests/test_recuperacion_de_contrasena.py
"""
import ast
import os
import smtplib
import sys
import uuid
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(AQUI)
sys.path.insert(0, BACKEND)

# --- 1. Entorno. Los guards de arranque de BOS-136 exigen estas cinco. -------
# Ojo: NO se pone PASSWORD_RESET_LOG_CODE ni ENVIRONMENT. Asi se prueba el
# camino por omision, que es el que corre en produccion.
os.environ.update(
    {
        "JWT_SECRET": "llave-de-prueba-local-no-es-un-secreto",
        "ADMIN_SECRET": "admin-de-prueba-local-no-es-un-secreto",
        "MONGO_URL": "mongodb://localhost:27017",
        "DB_NAME": "knowledge_wars_test_recuperacion",
        "CORS_ORIGINS": "http://localhost:3000",
        "ANTHROPIC_API_KEY": "sin-uso-esta-prueba-no-genera-preguntas",
    }
)
for sobrante in ("PASSWORD_RESET_LOG_CODE", "ENVIRONMENT", "SMTP_HOST", "SMTP_FROM"):
    os.environ.pop(sobrante, None)

# --- 2. La base, antes de importar server.py -------------------------------
# Por omision, mongomock. Pero el tope de solicitudes consulta por fecha
# (`created_at: {$gte: ...}`), y eso lo resuelve el servidor de Mongo, no
# pymongo: mongomock podria contestar bien algo que el Mongo de verdad
# contestara distinto -- ya nos paso con `$expr` en la metrica 3. Con
# KW_TEST_REAL_MONGO=1 la misma prueba corre contra un Mongo local, en una base
# con nombre al azar que se borra al terminar.
import pymongo

MONGO_REAL = os.getenv("KW_TEST_REAL_MONGO", "").strip().lower() not in ("", "0", "false", "no")
if MONGO_REAL:
    os.environ["DB_NAME"] = "kw_test_recuperacion_" + uuid.uuid4().hex[:12]
else:
    import mongomock

    pymongo.MongoClient = mongomock.MongoClient

# --- 3. La app real --------------------------------------------------------
from fastapi.testclient import TestClient

import mailer
import server

client = TestClient(server.app, raise_server_exceptions=False)

CONTRASENA = "contrasena-de-prueba-local"
NUEVA = "la-que-se-pone-en-el-rescate"

CHECKS = []


def ok(label, condition, detail=""):
    CHECKS.append((bool(condition), label, detail))
    mark = "ok  " if condition else "FAIL"
    print(f"{mark} {label}" + (f" -- {detail}" if detail else ""))
    return bool(condition)


def registrar(correo):
    """Crea una cuenta por el camino normal y devuelve el cuerpo del registro."""
    res = client.post(
        "/api/auth/register",
        json={
            "email": correo,
            "password": CONTRASENA,
            "display_name": "Prueba BOS-353",
            "country_code": "MX",
            "favorite_topic": "historia",
            "language": "es",
        },
    )
    assert res.status_code == 200, res.text[:300]
    return res.json()


def limpiar_topes():
    """Vacia el contador de solicitudes.

    Cada capa estrena cuota a proposito: el tope por correo es de 3 en 15
    minutos y el de IP de 20 en una hora, asi que sin esto una capa gastaria la
    cuota de la siguiente y el 429 aparecerian donde no se esta probando.
    """
    server.password_reset_requests_col.delete_many({})


def pedir_codigo(correo, ip="10.0.0.1"):
    """Pide el rescate y devuelve (respuesta, documento del rescate en la base)."""
    res = client.post(
        "/api/auth/forgot-password",
        json={"email": correo},
        headers={"X-Forwarded-For": ip},
    )
    doc = server.password_resets_col.find_one({"email": correo, "used": False})
    return res, doc


def nodo_de_funcion(arbol, nombre):
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)) and nodo.name == nombre:
            return nodo
    return None


# ---------------------------------------------------------------------------
def capa_1_la_respuesta_no_lleva_el_codigo_ni_el_token():
    print("=" * 72)
    print("Capa 1 -- forgot-password no entrega el codigo ni el token")
    print("=" * 72)
    limpiar_topes()

    correo = "capa1-bos353@kwtest-local.com"
    registrar(correo)

    res, doc = pedir_codigo(correo, ip="10.1.0.1")
    ok("forgot-password -> 200", res.status_code == 200, res.text[:200])
    cuerpo = res.json()
    ok("el rescate SI se creo en la base", doc is not None)
    codigo = (doc or {}).get("code", "")
    token = (doc or {}).get("token", "")

    ok(
        "la respuesta no trae _dev_code",
        "_dev_code" not in cuerpo,
        repr(cuerpo),
    )
    ok(
        "la respuesta no trae reset_token (con el token solo ya se cambiaba la contrasena)",
        "reset_token" not in cuerpo,
        repr(cuerpo),
    )
    # Y no solo por el nombre del campo: que el codigo ni el token aparezcan en
    # ninguna parte del cuerpo, con cualquier nombre.
    crudo = res.text
    ok("el codigo no aparece en el cuerpo con ningun nombre", codigo not in crudo, repr(crudo))
    ok("el token no aparece en el cuerpo con ningun nombre", token not in crudo, repr(crudo))
    ok(
        "la respuesta solo trae success y message",
        set(cuerpo.keys()) == {"success", "message"},
        repr(sorted(cuerpo.keys())),
    )

    # El mismo cuerpo, byte por byte, para un correo que no existe.
    res_fantasma = client.post(
        "/api/auth/forgot-password",
        json={"email": "no-existe-bos353@kwtest-local.com"},
        headers={"X-Forwarded-For": "10.1.0.1"},
    )
    ok("un correo que no existe -> 200", res_fantasma.status_code == 200)
    ok(
        "la respuesta es identica para un correo que existe y uno que no",
        res_fantasma.text == crudo,
        f"{res_fantasma.text!r} vs {crudo!r}",
    )
    ok(
        "y a ese correo no se le creo ningun rescate",
        server.password_resets_col.find_one({"email": "no-existe-bos353@kwtest-local.com"}) is None,
    )


# ---------------------------------------------------------------------------
def capa_2_el_codigo_sale_de_secrets():
    print()
    print("=" * 72)
    print("Capa 2 -- el codigo lo genera secrets, no random")
    print("=" * 72)
    limpiar_topes()

    fuente = open(os.path.join(BACKEND, "server.py"), encoding="utf-8").read()
    arbol = ast.parse(fuente)

    nombres = {n.id for n in ast.walk(arbol) if isinstance(n, ast.Name)}
    modulos = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.update(a.name.split(".")[0] for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.add(nodo.module.split(".")[0])
    ok("server.py ya no importa random en ninguna parte", "random" not in modulos, repr(sorted(modulos & {"random", "secrets"})))
    ok("server.py no nombra random en ninguna parte", "random" not in nombres)
    ok("server.py importa secrets", "secrets" in modulos)

    funcion = nodo_de_funcion(arbol, "forgot_password")
    ok("forgot_password sigue existiendo", funcion is not None)
    cuerpo_funcion = ast.dump(funcion) if funcion else ""
    ok(
        "forgot_password usa secrets.randbelow",
        "'randbelow'" in cuerpo_funcion,
    )

    # Y la prueba de verdad: una sonda sobre `secrets.randbelow` confirma que de
    # ahi sale el codigo que se guarda. El AST dice que el codigo lo dice; esto
    # dice que el servidor lo hace.
    correo = "capa2-bos353@kwtest-local.com"
    registrar(correo)

    original = server.secrets.randbelow
    llamadas = []

    def sonda(n):
        llamadas.append(n)
        return original(n)

    server.secrets.randbelow = sonda
    try:
        _, doc = pedir_codigo(correo, ip="10.2.0.1")
    finally:
        server.secrets.randbelow = original

    ok(
        "secrets.randbelow se llamo una vez al pedir el codigo",
        len(llamadas) == 1,
        repr(llamadas),
    )
    ok(
        "y se llamo sobre el millon entero (10^6 combinaciones)",
        llamadas == [1000000],
        repr(llamadas),
    )
    codigo = (doc or {}).get("code")
    ok(
        "el codigo guardado son 6 digitos exactos",
        isinstance(codigo, str) and len(codigo) == 6 and codigo.isdigit(),
        repr(codigo),
    )

    # Que el relleno con ceros no se coma un codigo chico: 7 -> "000007".
    server.secrets.randbelow = lambda n: 7
    try:
        _, doc = pedir_codigo(correo, ip="10.2.0.1")
    finally:
        server.secrets.randbelow = original
    ok(
        "un numero chico se guarda con los ceros delante, no como '7'",
        (doc or {}).get("code") == "000007",
        repr((doc or {}).get("code")),
    )


# ---------------------------------------------------------------------------
def capa_3_los_intentos_fallidos_queman_el_token():
    print()
    print("=" * 72)
    print("Capa 3 -- cinco intentos fallidos agotan la ventana (sin quemar el token)")
    print("=" * 72)
    limpiar_topes()

    correo = "capa3-bos353@kwtest-local.com"
    registrar(correo)
    _, doc = pedir_codigo(correo, ip="10.3.0.1")
    codigo = doc["code"]
    token = doc["token"]
    malo = "000000" if codigo != "000000" else "111111"

    ok(
        "el tope es 5 intentos (si alguien lo sube, esto lo delata)",
        server.RESET_CODE_MAX_ATTEMPTS == 5,
        str(server.RESET_CODE_MAX_ATTEMPTS),
    )
    ok(
        "y se cuentan en una ventana de 5 minutos, mas corta que el token (BOS-359)",
        server.RESET_CODE_ATTEMPTS_WINDOW_MINUTES == 5,
        str(server.RESET_CODE_ATTEMPTS_WINDOW_MINUTES),
    )

    for intento in range(1, 6):
        res = client.post(f"/api/auth/verify-reset-code?email={correo}&code={malo}")
        ok(
            f"intento fallido {intento}/5 -> 400",
            res.status_code == 400,
            res.text[:150],
        )
        guardado = server.password_resets_col.find_one({"token": token})
        ok(
            f"el intento {intento} quedo contado en la base",
            guardado.get("attempts") == intento
            and len(guardado.get("failed_attempts") or []) == intento,
            repr((guardado.get("attempts"), len(guardado.get("failed_attempts") or []))),
        )

    # Con la ventana agotada, el codigo CORRECTO tampoco sirve. Esto es el punto
    # entero del tope: un codigo de 6 digitos sin tope de intentos no es un
    # secreto.
    res = client.post(f"/api/auth/verify-reset-code?email={correo}&code={codigo}")
    ok(
        "con la ventana agotada, el codigo correcto tambien da 400",
        res.status_code == 400,
        res.text[:150],
    )
    ok(
        "el 400 de la ventana agotada no dice que lo esta",
        "intent" not in res.text.lower() and "ventana" not in res.text.lower(),
        res.text[:150],
    )

    # Pero el token NO queda quemado (BOS-359): quemarlo era lo que le permitia
    # a un tercero dejar la cuenta sin rescate sabiendo solo el correo. El
    # presupuesto se repone al pasar la ventana, y la capa 8 lo prueba.
    agotado = server.password_resets_col.find_one({"token": token})
    ok(
        "el token NO queda quemado al quinto fallo (BOS-359)",
        agotado.get("used") is False,
        repr(agotado.get("used")),
    )
    # Que el token siga vivo no le sirve a quien golpeo los cinco intentos: el
    # token no sale nunca por HTTP sin el codigo correcto (capa 1), asi que el
    # atacante del caso de arriba no lo tiene. La contrasena no se movio.
    usuario = server.users_col.find_one({"email": correo})
    ok(
        "la contrasena de la cuenta no se movio con los cinco fallos",
        server.verify_password(CONTRASENA, usuario["password"]),
    )

    # Un codigo que no es ASCII tiene que dar 400, no 500. `hmac.compare_digest`
    # revienta con un TypeError si se le pasan cadenas no-ASCII, y esa es la
    # misma trampa que convirtio un 403 en un 500 en BOS-236.
    limpiar_topes()
    _, doc = pedir_codigo(correo, ip="10.3.0.9")
    for raro, etiqueta in (
        ("ñandú1", "con acentos"),
        ("000ñ00", "mezclado con un acento"),
        ("日本語です", "en otro alfabeto"),
        ("1" * 500, "de 500 caracteres"),
        ("", "vacio"),
    ):
        res = client.post(
            "/api/auth/verify-reset-code",
            params={"email": correo, "code": raro},
        )
        ok(
            f"un codigo {etiqueta} -> 400, no 500",
            res.status_code == 400,
            f"{res.status_code}: {res.text[:120]}",
        )
    guardado = server.password_resets_col.find_one({"token": doc["token"]})
    ok(
        "y esos intentos tambien se contaron (no son gratis)",
        guardado.get("attempts") == 5
        and len(guardado.get("failed_attempts") or []) == 5,
        repr((guardado.get("attempts"), len(guardado.get("failed_attempts") or []))),
    )

    # Cuatro fallos y un acierto: el tope no estorba a quien se equivoca.
    limpiar_topes()
    _, doc = pedir_codigo(correo, ip="10.3.0.2")
    codigo = doc["code"]
    malo = "000000" if codigo != "000000" else "111111"
    for _ in range(4):
        client.post(f"/api/auth/verify-reset-code?email={correo}&code={malo}")
    res = client.post(f"/api/auth/verify-reset-code?email={correo}&code={codigo}")
    ok(
        "cuatro fallos y luego el codigo correcto -> 200",
        res.status_code == 200,
        res.text[:200],
    )


# ---------------------------------------------------------------------------
def capa_4_no_se_pueden_pedir_codigos_en_bucle():
    print()
    print("=" * 72)
    print("Capa 4 -- tope de solicitudes por correo y por IP")
    print("=" * 72)
    limpiar_topes()

    correo = "capa4-bos353@kwtest-local.com"
    otro = "capa4-otro-bos353@kwtest-local.com"
    registrar(correo)
    registrar(otro)

    ok(
        "el tope por correo es 3 en 15 minutos",
        (server.RESET_REQUESTS_PER_EMAIL, server.RESET_REQUESTS_PER_EMAIL_WINDOW_MINUTES) == (3, 15),
        f"{server.RESET_REQUESTS_PER_EMAIL}/{server.RESET_REQUESTS_PER_EMAIL_WINDOW_MINUTES}",
    )

    for n in range(1, 4):
        res, _ = pedir_codigo(correo, ip="10.4.0.1")
        ok(f"solicitud {n}/3 del mismo correo -> 200", res.status_code == 200, res.text[:150])

    res, _ = pedir_codigo(correo, ip="10.4.0.1")
    ok("la cuarta solicitud del mismo correo -> 429", res.status_code == 429, res.text[:200])
    ok(
        "el 429 trae Retry-After con los segundos que faltan",
        res.headers.get("retry-after", "").isdigit() and int(res.headers["retry-after"]) > 0,
        repr(res.headers.get("retry-after")),
    )

    # Desde OTRA IP tampoco: el tope por correo no se esquiva cambiando de red.
    res, _ = pedir_codigo(correo, ip="10.4.0.99")
    ok("el tope por correo no se esquiva cambiando de IP -> 429", res.status_code == 429, res.text[:150])

    # Pero otro correo desde la misma IP sigue pasando (no es un tope global).
    res, _ = pedir_codigo(otro, ip="10.4.0.1")
    ok("otro correo desde la misma IP sigue pasando -> 200", res.status_code == 200, res.text[:150])

    # Un correo que no existe tambien se limita: si no, se podria barrer la
    # lista de correos a ritmo libre.
    limpiar_topes()
    fantasma = "fantasma-capa4-bos353@kwtest-local.com"
    for _ in range(3):
        client.post(
            "/api/auth/forgot-password",
            json={"email": fantasma},
            headers={"X-Forwarded-For": "10.4.0.2"},
        )
    res = client.post(
        "/api/auth/forgot-password",
        json={"email": fantasma},
        headers={"X-Forwarded-For": "10.4.0.2"},
    )
    ok("un correo que no existe tambien se limita -> 429", res.status_code == 429, res.text[:150])

    # El tope por IP: 20 correos distintos desde la misma IP y el 21 se corta.
    limpiar_topes()
    ok(
        "el tope por IP es 20 en una hora",
        (server.RESET_REQUESTS_PER_IP, server.RESET_REQUESTS_PER_IP_WINDOW_MINUTES) == (20, 60),
        f"{server.RESET_REQUESTS_PER_IP}/{server.RESET_REQUESTS_PER_IP_WINDOW_MINUTES}",
    )
    for n in range(20):
        client.post(
            "/api/auth/forgot-password",
            json={"email": f"barrido-{n}-bos353@kwtest-local.com"},
            headers={"X-Forwarded-For": "10.4.0.3"},
        )
    res = client.post(
        "/api/auth/forgot-password",
        json={"email": "barrido-21-bos353@kwtest-local.com"},
        headers={"X-Forwarded-For": "10.4.0.3"},
    )
    ok("la solicitud 21 desde la misma IP -> 429", res.status_code == 429, res.text[:150])
    res = client.post(
        "/api/auth/forgot-password",
        json={"email": "barrido-21-bos353@kwtest-local.com"},
        headers={"X-Forwarded-For": "10.4.9.9"},
    )
    ok("y desde otra IP el mismo correo sigue pasando -> 200", res.status_code == 200, res.text[:150])


# ---------------------------------------------------------------------------
def capa_5_el_flujo_legitimo_corre_de_punta_a_punta():
    print()
    print("=" * 72)
    print("Capa 5 -- el rescate legitimo, leyendo el codigo del correo que salio")
    print("=" * 72)
    limpiar_topes()

    correo = "capa5-bos353@kwtest-local.com"
    registrar(correo)

    # El correo que de verdad saldria. Se sustituye el envio, no la generacion:
    # lo que se comprueba es que el codigo llega por ahi y por ningun otro lado.
    enviados = []

    def envio_falso(destino, codigo):
        enviados.append((destino, codigo))
        return True

    real = server.send_password_reset_code
    server.send_password_reset_code = envio_falso
    try:
        res = client.post(
            "/api/auth/forgot-password",
            json={"email": correo},
            headers={"X-Forwarded-For": "10.5.0.1"},
        )
    finally:
        server.send_password_reset_code = real

    ok("forgot-password -> 200", res.status_code == 200, res.text[:150])
    ok("se mando exactamente un correo", len(enviados) == 1, repr(enviados))
    destino, codigo = enviados[0] if enviados else (None, None)
    ok("el correo va al dueno de la cuenta", destino == correo, repr(destino))

    guardado = server.password_resets_col.find_one({"email": correo, "used": False})
    ok(
        "el codigo que se mando es el que quedo guardado",
        codigo == (guardado or {}).get("code"),
        repr(codigo),
    )
    ok("y sigue sin aparecer en la respuesta", str(codigo) not in res.text, res.text[:200])
    ok("el rescate nace con 0 intentos", (guardado or {}).get("attempts") == 0)

    # Verificar -> token.
    res = client.post(f"/api/auth/verify-reset-code?email={correo}&code={codigo}")
    ok("verify-reset-code con el codigo del correo -> 200", res.status_code == 200, res.text[:200])
    token = res.json().get("reset_token") if res.status_code == 200 else None
    ok("verify-reset-code devuelve el token", bool(token))

    # Poner la contrasena y entrar.
    res = client.post(
        "/api/auth/reset-password", json={"token": token, "new_password": NUEVA}
    )
    ok("reset-password -> 200", res.status_code == 200, res.text[:200])
    res = client.post("/api/auth/login", json={"email": correo, "password": NUEVA})
    ok("la cuenta entra con la contrasena nueva -> 200", res.status_code == 200, res.text[:200])

    # El uso unico y la expiracion de 15 minutos: no las toco este cambio, y
    # siguen en pie.
    res = client.post(
        "/api/auth/reset-password", json={"token": token, "new_password": "otra-mas-todavia"}
    )
    ok("el token no se puede usar dos veces -> 400", res.status_code == 400, res.text[:150])
    res = client.post("/api/auth/login", json={"email": correo, "password": NUEVA})
    ok("y la contrasena sigue siendo la del rescate", res.status_code == 200, res.text[:150])

    limpiar_topes()
    _, doc = pedir_codigo(correo, ip="10.5.0.2")
    ok(
        "el rescate nuevo vence en 15 minutos",
        timedelta(minutes=14)
        < (doc["expires_at"].replace(tzinfo=timezone.utc) - doc["created_at"].replace(tzinfo=timezone.utc))
        <= timedelta(minutes=15),
        repr(doc["expires_at"] - doc["created_at"]),
    )
    server.password_resets_col.update_one(
        {"token": doc["token"]},
        {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)}},
    )
    res = client.post(f"/api/auth/verify-reset-code?email={correo}&code={doc['code']}")
    ok("un codigo vencido -> 400", res.status_code == 400, res.text[:150])


# ---------------------------------------------------------------------------
def capa_6_el_camino_de_desarrollo_no_arranca_en_produccion():
    print()
    print("=" * 72)
    print("Capa 6 -- PASSWORD_RESET_LOG_CODE no puede estar encendida en produccion")
    print("=" * 72)

    ok(
        "apagada por omision (ni bandera ni ENVIRONMENT)",
        mailer.resolve_log_code_flag(None, None) is False,
    )
    ok(
        "apagada si la bandera viene vacia",
        mailer.resolve_log_code_flag("", "development") is False,
    )
    ok(
        "encendida solo con ENVIRONMENT=development",
        mailer.resolve_log_code_flag("1", "development") is True,
    )

    for entorno in (None, "", "production", "staging", "PRODUCTION", "prod"):
        try:
            mailer.resolve_log_code_flag("1", entorno)
            ok(f"encendida con ENVIRONMENT={entorno!r} -> el arranque falla", False, "no fallo")
        except ValueError as exc:
            ok(
                f"encendida con ENVIRONMENT={entorno!r} -> el arranque falla",
                "ENVIRONMENT=development" in str(exc),
                str(exc)[:120],
            )

    ok(
        "y la app que corre esta prueba la tiene apagada",
        server.PASSWORD_RESET_LOG_CODE is False,
        repr(server.PASSWORD_RESET_LOG_CODE),
    )


# ---------------------------------------------------------------------------
def capa_7_el_mailer():
    print()
    print("=" * 72)
    print("Capa 7 -- el mailer: sin configurar no manda, y no acepta cabeceras partidas")
    print("=" * 72)

    for sobrante in ("SMTP_HOST", "SMTP_FROM", "SMTP_USER", "SMTP_PASSWORD", "SMTP_PORT"):
        os.environ.pop(sobrante, None)
    ok("sin SMTP_HOST/SMTP_FROM no esta configurado", mailer.is_configured() is False)
    ok(
        "y send_password_reset_code devuelve False sin intentar nada",
        mailer.send_password_reset_code("alguien@kwtest-local.com", "123456") is False,
    )

    os.environ["SMTP_HOST"] = "smtp.kwtest-local"
    os.environ["SMTP_FROM"] = "Knowledge Wars <no-reply@kwtest-local>"
    os.environ["SMTP_USER"] = "usuario"
    os.environ["SMTP_PASSWORD"] = "no-es-un-secreto-de-verdad"
    try:
        ok("con host y remitente ya esta configurado", mailer.is_configured() is True)

        # Una direccion con un salto de linea es inyeccion de cabeceras.
        ok(
            "una direccion con un salto de linea se rechaza",
            mailer.send_password_reset_code("victima@x\nBcc: otro@y", "123456") is False,
        )
        ok(
            "una direccion con un espacio se rechaza",
            mailer.send_password_reset_code("victima@x otro@y", "123456") is False,
        )

        # Y el camino bueno, con un SMTP de mentira en lugar del de verdad.
        mandados = []

        class SMTPFalso:
            def __init__(self, host, port, timeout=None):
                mandados.append(("conexion", host, port))

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def starttls(self, context=None):
                mandados.append(("starttls", bool(context)))

            def login(self, usuario, contrasena):
                mandados.append(("login", usuario))

            def send_message(self, mensaje):
                mandados.append(("mensaje", mensaje))

        real = smtplib.SMTP
        smtplib.SMTP = SMTPFalso
        try:
            salio = mailer.send_password_reset_code("destino@kwtest-local.com", "424242")
        finally:
            smtplib.SMTP = real

        ok("el envio devuelve True", salio is True)
        ok(
            "se abrio la conexion al host configurado en el 587",
            ("conexion", "smtp.kwtest-local", 587) in mandados,
            repr([m for m in mandados if m[0] == "conexion"]),
        )
        ok("se negocio STARTTLS con contexto", ("starttls", True) in mandados)
        ok("se autentico con el usuario configurado", ("login", "usuario") in mandados)

        mensaje = next((m[1] for m in mandados if m[0] == "mensaje"), None)
        ok("se mando un mensaje", mensaje is not None)
        if mensaje is not None:
            ok("va al destinatario correcto", mensaje["To"] == "destino@kwtest-local.com", repr(mensaje["To"]))
            ok(
                "sale del remitente configurado",
                mensaje["From"] == "Knowledge Wars <no-reply@kwtest-local>",
                repr(mensaje["From"]),
            )
            ok("el codigo va en el cuerpo", "424242" in mensaje.get_content(), repr(mensaje.get_content()[:80]))

        # Si el proveedor falla, no se cae el endpoint: devuelve False.
        def explota(*_a, **_k):
            raise smtplib.SMTPException("el proveedor dijo no")

        smtplib.SMTP = explota
        try:
            ok(
                "si el proveedor falla, devuelve False en vez de reventar",
                mailer.send_password_reset_code("destino@kwtest-local.com", "424242") is False,
            )
        finally:
            smtplib.SMTP = real
    finally:
        for sobrante in ("SMTP_HOST", "SMTP_FROM", "SMTP_USER", "SMTP_PASSWORD"):
            os.environ.pop(sobrante, None)

    # Y con el mailer apagado, el endpoint sigue contestando 200 y lo mismo: que
    # no haya correo configurado no se le cuenta al cliente.
    limpiar_topes()
    correo = "capa7-bos353@kwtest-local.com"
    registrar(correo)
    res, doc = pedir_codigo(correo, ip="10.7.0.1")
    ok("sin SMTP configurado el endpoint sigue dando 200", res.status_code == 200, res.text[:150])
    ok("el rescate se creo igual", doc is not None)
    ok(
        "y el codigo sigue sin viajar en la respuesta",
        (doc or {}).get("code", "???") not in res.text,
        res.text[:200],
    )


# ---------------------------------------------------------------------------
def capa_8_los_tres_huecos_de_bos_359():
    """Los tres huecos que dejo abierto el PR del rescate (BOS-359).

    Ninguno era un take-over -- el PR cerro ese --, pero los tres tenian que
    estar cerrados antes de dar de alta al primer usuario real.
    """
    print()
    print("=" * 72)
    print("Capa 8 -- BOS-359: oraculo de existencia, bloqueo del rescate, cuota cruzada")
    print("=" * 72)

    # --- 8a. `verify-reset-code` ya no dice si un correo esta registrado -----
    #
    # La consulta busca por `{email, used: False}`, sin el codigo, asi que con el
    # correo y cualquier codigo se llega a la rama de expiracion. Esa rama
    # contestaba "El código ha expirado" -- un texto distinto del 400 generico --
    # y el documento vencido se queda en la base, asi que el oraculo quedaba fijo
    # para cualquier cuenta que pidiera un codigo y lo dejara vencer.
    limpiar_topes()
    registrado = "capa8-registrado-bos359@kwtest-local.com"
    fantasma = "capa8-fantasma-bos359@kwtest-local.com"
    registrar(registrado)
    _, doc = pedir_codigo(registrado, ip="10.8.0.1")
    server.password_resets_col.update_one(
        {"token": doc["token"]},
        {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)}},
    )

    res_registrado = client.post(
        "/api/auth/verify-reset-code", params={"email": registrado, "code": "000000"}
    )
    res_fantasma = client.post(
        "/api/auth/verify-reset-code", params={"email": fantasma, "code": "000000"}
    )
    ok(
        "un codigo vencido y un correo que no existe dan el mismo status",
        res_registrado.status_code == res_fantasma.status_code == 400,
        f"{res_registrado.status_code} vs {res_fantasma.status_code}",
    )
    ok(
        "y el MISMO cuerpo, byte por byte (ya no hay oraculo de existencia)",
        res_registrado.content == res_fantasma.content,
        f"{res_registrado.text[:90]} vs {res_fantasma.text[:90]}",
    )
    ok(
        "el 400 del vencido no dice 'expirado' por su cuenta",
        "ha expirado" not in res_registrado.text,
        res_registrado.text[:120],
    )
    # Ojo con lo que prueba cada modo. Contra Mongo real el documento vencido
    # TODAVIA esta en la base cuando se sondea (el TTL barre cada ~60 s), asi que
    # ese run es el que demuestra el arreglo del endpoint. mongomock aplica el
    # TTL al leer, asi que ahi el documento ya no esta y las dos respuestas
    # coinciden por el otro camino. Las dos cosas son lo que se quiere.
    vencido = server.password_resets_col.find_one({"token": doc["token"]})
    ok(
        "sondear un vencido no le gasta intentos a nadie "
        "(o el TTL ya se lo llevo, o sigue intacto)",
        vencido is None or (vencido.get("failed_attempts") or []) == [],
        repr(vencido and vencido.get("failed_attempts")),
    )
    ok(
        "pero si queda anotado en el cubo por IP de verify (ya cuesta algo)",
        server.password_reset_requests_col.count_documents(
            {"key": "verify_ip:testclient"}
        )
        >= 2,
        str(
            server.password_reset_requests_col.count_documents(
                {"key": "verify_ip:testclient"}
            )
        ),
    )

    # El TTL es la otra mitad: el documento vencido no se queda para siempre.
    # Antes `expires_at` era un indice normal y solo lo borraba la siguiente
    # solicitud del mismo correo.
    indices = server.password_resets_col.index_information()
    ok(
        "expires_at es un indice TTL (expireAfterSeconds=0)",
        indices.get("expires_at_1", {}).get("expireAfterSeconds") == 0,
        repr(indices.get("expires_at_1")),
    )
    ok(
        "y server.py lo reporta activo",
        server.PASSWORD_RESETS_TTL_ACTIVO is True,
        repr(server.PASSWORD_RESETS_TTL_ACTIVO),
    )

    # --- 8b. un tercero ya no puede dejar la cuenta sin rescate -------------
    #
    # El tope de 5 intentos es por token. Mientras el quinto fallo quemaba el
    # token, quemar el rescate de alguien costaba cinco llamadas y cero espera,
    # y se repetia con cada token nuevo que la victima pidiera hasta agotarle su
    # cuota de 3 solicitudes por 15 minutos. Ahora: (1) la ventana se repone, y
    # (2) quemar cuesta cuota del tope por IP.
    limpiar_topes()
    victima = "capa8-victima-bos359@kwtest-local.com"
    registrar(victima)
    _, doc = pedir_codigo(victima, ip="10.8.0.2")
    codigo = doc["code"]
    token = doc["token"]
    malo = "000000" if codigo != "000000" else "111111"

    for _ in range(server.RESET_CODE_MAX_ATTEMPTS):
        client.post("/api/auth/verify-reset-code", params={"email": victima, "code": malo})

    res = client.post(
        "/api/auth/verify-reset-code", params={"email": victima, "code": codigo}
    )
    ok(
        "recien agotada la ventana, el codigo correcto de la victima da 400",
        res.status_code == 400,
        res.text[:150],
    )
    quemado = server.password_resets_col.find_one({"token": token})
    ok(
        "pero el token sigue vivo: used sigue en False",
        quemado.get("used") is False,
        repr(quemado.get("used")),
    )

    # Pasada la ventana, la victima recupera intentos. Se simula moviendo las
    # fechas de los fallos al pasado, que es lo mismo que esperar.
    atras = datetime.now(timezone.utc) - timedelta(
        minutes=server.RESET_CODE_ATTEMPTS_WINDOW_MINUTES + 1
    )
    server.password_resets_col.update_one(
        {"token": token},
        {"$set": {"failed_attempts": [atras] * server.RESET_CODE_MAX_ATTEMPTS}},
    )
    res = client.post(
        "/api/auth/verify-reset-code", params={"email": victima, "code": codigo}
    )
    ok(
        "pasada la ventana, el codigo correcto de la victima SI pasa -> 200",
        res.status_code == 200,
        res.text[:200],
    )
    ok(
        "y devuelve el token, asi que el rescate se completa",
        res.status_code == 200 and bool(res.json().get("reset_token")),
        res.text[:200],
    )
    ok(
        "el acierto limpio la ventana de fallos",
        (server.password_resets_col.find_one({"token": token}).get("failed_attempts") or [])
        == [],
    )

    # Y el tope por IP: quemar tokens ajenos ya no es gratis.
    limpiar_topes()
    ok(
        "el tope de verify es 90 por IP cada hora (subido de 30 en BOS-361)",
        (server.RESET_VERIFY_PER_IP, server.RESET_VERIFY_PER_IP_WINDOW_MINUTES)
        == (90, 60),
        f"{server.RESET_VERIFY_PER_IP}/{server.RESET_VERIFY_PER_IP_WINDOW_MINUTES}",
    )
    for n in range(server.RESET_VERIFY_PER_IP):
        res = client.post(
            "/api/auth/verify-reset-code",
            params={"email": fantasma, "code": "000000"},
            headers={"X-Forwarded-For": "10.8.9.9"},
        )
        if res.status_code != 400:
            ok(f"la llamada {n + 1} deberia ser 400, no {res.status_code}", False, res.text[:120])
            break
    res = client.post(
        "/api/auth/verify-reset-code",
        params={"email": fantasma, "code": "000000"},
        headers={"X-Forwarded-For": "10.8.9.9"},
    )
    ok(
        f"la llamada {server.RESET_VERIFY_PER_IP + 1} desde la misma IP -> 429",
        res.status_code == 429,
        f"{res.status_code}: {res.text[:120]}",
    )
    ok(
        "el 429 de verify trae Retry-After",
        res.headers.get("retry-after", "").isdigit()
        and int(res.headers["retry-after"]) > 0,
        repr(res.headers.get("retry-after")),
    )
    # El tope es por IP, no global: desde otra red el rescate legitimo pasa.
    res = client.post(
        "/api/auth/verify-reset-code",
        params={"email": fantasma, "code": "000000"},
        headers={"X-Forwarded-For": "10.8.9.10"},
    )
    ok(
        "desde otra IP sigue pasando (es por IP, no un tope global) -> 400",
        res.status_code == 400,
        f"{res.status_code}: {res.text[:120]}",
    )
    # Y el 429 por IP no depende de que el correo exista: se mira antes de tocar
    # la base, asi que no filtra nada.
    res_fantasma_429 = client.post(
        "/api/auth/verify-reset-code",
        params={"email": fantasma, "code": "000000"},
        headers={"X-Forwarded-For": "10.8.9.9"},
    )
    res_real_429 = client.post(
        "/api/auth/verify-reset-code",
        params={"email": victima, "code": "000000"},
        headers={"X-Forwarded-For": "10.8.9.9"},
    )
    ok(
        "el 429 de verify es igual para un correo que existe y uno que no",
        res_fantasma_429.content == res_real_429.content,
        f"{res_fantasma_429.text[:90]} vs {res_real_429.text[:90]}",
    )

    # --- 8c. una solicitud rechazada por IP no gasta cuota del correo -------
    #
    # `consume_reset_quota` registraba el renglon del cubo del correo antes de
    # mirar el de IP. Con el cubo de IP lleno, una solicitud que contestaba 429
    # dejaba 1 renglon en el cubo del correo: en el salon de evento, cada
    # reintento de un usuario legitimo le comia una de sus 3 solicitudes.
    limpiar_topes()
    salon = "10.8.0.77"
    afectado = "capa8-salon-bos359@kwtest-local.com"
    registrar(afectado)
    clave_correo = f"email:{afectado}"

    # Se llena el cubo de IP con OTROS correos, para que el 429 venga del cubo
    # de IP y no del suyo.
    for n in range(server.RESET_REQUESTS_PER_IP):
        client.post(
            "/api/auth/forgot-password",
            json={"email": f"capa8-relleno-{n}-bos359@kwtest-local.com"},
            headers={"X-Forwarded-For": salon},
        )
    ok(
        "el cubo de IP quedo lleno",
        server.password_reset_requests_col.count_documents({"key": f"ip:{salon}"})
        == server.RESET_REQUESTS_PER_IP,
        str(server.password_reset_requests_col.count_documents({"key": f"ip:{salon}"})),
    )
    ok(
        "y el usuario del salon todavia no gasto nada de su cuota",
        server.password_reset_requests_col.count_documents({"key": clave_correo}) == 0,
    )

    for n in range(1, 4):
        res = client.post(
            "/api/auth/forgot-password",
            json={"email": afectado},
            headers={"X-Forwarded-For": salon},
        )
        ok(
            f"su reintento {n} se rechaza por el cubo de IP -> 429",
            res.status_code == 429,
            f"{res.status_code}: {res.text[:120]}",
        )
    ok(
        "y NINGUNO le gasto cuota de su cubo por correo (BOS-359)",
        server.password_reset_requests_col.count_documents({"key": clave_correo}) == 0,
        str(server.password_reset_requests_col.count_documents({"key": clave_correo})),
    )

    # Liberada la ventana de IP, le quedan sus 3 solicitudes enteras.
    server.password_reset_requests_col.delete_many({"key": f"ip:{salon}"})
    for n in range(1, 4):
        res = client.post(
            "/api/auth/forgot-password",
            json={"email": afectado},
            headers={"X-Forwarded-For": salon},
        )
        ok(
            f"liberada la ventana de IP, su solicitud {n}/3 -> 200",
            res.status_code == 200,
            f"{res.status_code}: {res.text[:120]}",
        )
    res = client.post(
        "/api/auth/forgot-password",
        json={"email": afectado},
        headers={"X-Forwarded-For": salon},
    )
    ok(
        "la cuarta si se corta: el tope por correo sigue en pie",
        res.status_code == 429,
        f"{res.status_code}: {res.text[:120]}",
    )

    # El rechazo por su propio cubo tampoco alarga la ventana ni gasta cuota de
    # IP: lo que ya decia el docstring, ahora cierto para los dos cubos.
    antes_correo = server.password_reset_requests_col.count_documents({"key": clave_correo})
    antes_ip = server.password_reset_requests_col.count_documents({"key": f"ip:{salon}"})
    client.post(
        "/api/auth/forgot-password",
        json={"email": afectado},
        headers={"X-Forwarded-For": salon},
    )
    ok(
        "un 429 por el cubo del correo no registra nada en ningun cubo",
        server.password_reset_requests_col.count_documents({"key": clave_correo})
        == antes_correo
        and server.password_reset_requests_col.count_documents({"key": f"ip:{salon}"})
        == antes_ip,
        f"correo {antes_correo}->{server.password_reset_requests_col.count_documents({'key': clave_correo})}, "
        f"ip {antes_ip}->{server.password_reset_requests_col.count_documents({'key': f'ip:{salon}'})}",
    )


# ---------------------------------------------------------------------------
def operadores_mongo_sobre(nodo, campo):
    """Operadores de Mongo ($set/$push/$pull/...) aplicados a `campo` dentro de `nodo`.

    Se lee del AST y no del comportamiento a proposito: el punto 2 de BOS-361 es
    una carrera entre workers, y `TestClient` no tiene concurrencia real con la
    que provocarla. Lo que se puede exigir es la forma de la escritura.
    """
    usados = []
    for sub in ast.walk(nodo):
        if not isinstance(sub, ast.Dict):
            continue
        for llave, valor in zip(sub.keys, sub.values):
            if not (isinstance(llave, ast.Constant) and isinstance(llave.value, str)):
                continue
            if not llave.value.startswith("$") or not isinstance(valor, ast.Dict):
                continue
            for k2, v2 in zip(valor.keys, valor.values):
                if isinstance(k2, ast.Constant) and k2.value == campo:
                    usados.append((llave.value, v2))
    return usados


def capa_9_lo_que_dejo_abierto_bos_359():
    print()
    print("=" * 72)
    print("Capa 9 -- las tres cosas que dejo abiertas el PR de BOS-359 (BOS-361)")
    print("=" * 72)

    # --- 9a. el salon de evento completo alcanza a verificar -----------------
    #
    # `RESET_REQUESTS_PER_IP = 20` deja que 20 personas detras de un NAT pidan su
    # codigo, y cada una necesita 1 a 3 llamadas de verify. El tope de verify
    # estaba en 30, mas chico que ese trafico legitimo: medido con 20 cuentas y
    # dos tecleos malos cada una, solo 10 personas completaban el rescate y la 11
    # se comia un 429 con Retry-After de casi una hora, con un codigo en la mano
    # que vive 15 minutos.
    #
    # Esta prueba es la sonda: se llena el cubo de forgot de una sola IP con
    # cuentas distintas y se exige que TODAS alcancen a verificar.
    limpiar_topes()
    salon = "10.9.0.77"
    completaron = 0
    primer_429 = None
    llamadas_verify = 0

    for n in range(server.RESET_REQUESTS_PER_IP):
        correo = f"capa9-salon-{n}-bos361@kwtest-local.com"
        registrar(correo)
        res, doc = pedir_codigo(correo, ip=salon)
        if res.status_code != 200:
            ok(f"la persona {n + 1} deberia poder pedir su codigo", False, res.text[:120])
            break
        codigo = doc["code"]
        malo = "000000" if codigo != "000000" else "111111"

        # Dos tecleos malos y el bueno: el peor caso legitimo, 3 llamadas.
        for intento in (malo, malo, codigo):
            res = client.post(
                "/api/auth/verify-reset-code",
                params={"email": correo, "code": intento},
                headers={"X-Forwarded-For": salon},
            )
            llamadas_verify += 1
            if res.status_code == 429 and primer_429 is None:
                primer_429 = (n + 1, llamadas_verify, res.headers.get("retry-after"))
        if res.status_code == 200:
            completaron += 1

    ok(
        f"las {server.RESET_REQUESTS_PER_IP} personas del salon completaron su rescate "
        "desde una sola IP",
        completaron == server.RESET_REQUESTS_PER_IP,
        f"{completaron} de {server.RESET_REQUESTS_PER_IP}"
        + (
            f"; primer 429 en la persona {primer_429[0]}, llamada {primer_429[1]} "
            f"de verify, Retry-After={primer_429[2]}"
            if primer_429
            else ""
        ),
    )
    ok(
        "y ninguna llamada de verify del salon se contesto con 429",
        primer_429 is None,
        repr(primer_429),
    )
    ok(
        "el tope de verify cubre el techo del trafico legitimo (3 x el de forgot)",
        server.RESET_VERIFY_PER_IP >= 3 * server.RESET_REQUESTS_PER_IP,
        f"verify {server.RESET_VERIFY_PER_IP} vs 3 x forgot "
        f"{3 * server.RESET_REQUESTS_PER_IP}",
    )
    # Y el tope sigue existiendo: subirlo no es quitarlo. La capa 8 ya comprueba
    # el 429 en la llamada RESET_VERIFY_PER_IP + 1.
    ok(
        "el tope de verify sigue siendo finito y por hora",
        server.RESET_VERIFY_PER_IP < 1000
        and server.RESET_VERIFY_PER_IP_WINDOW_MINUTES == 60,
        f"{server.RESET_VERIFY_PER_IP}/{server.RESET_VERIFY_PER_IP_WINDOW_MINUTES}",
    )
    # El presupuesto por token no se movio: ese es el que acota la fuerza bruta
    # contra UNA cuenta, y es lo que hace que subir el tope por IP no la debilite.
    ok(
        "el presupuesto por token no se movio (5 intentos en 5 minutos)",
        (server.RESET_CODE_MAX_ATTEMPTS, server.RESET_CODE_ATTEMPTS_WINDOW_MINUTES)
        == (5, 5),
        f"{server.RESET_CODE_MAX_ATTEMPTS}/{server.RESET_CODE_ATTEMPTS_WINDOW_MINUTES}",
    )

    # --- 9b. el contador de intentos se escribe atomico ---------------------
    #
    # El gate de los 5 intentos leia el documento, podaba la ventana en memoria y
    # reescribia la lista entera con `$set`: un read-modify-write. Dos peticiones
    # que leyeran antes de que la otra escribiera se pisaban el renglon, asi que
    # el contador que de verdad gatea podia contar de menos. No era explotable
    # con un solo worker -- entre la lectura y la escritura no hay ni un `await`,
    # asi que el event loop no intercala --, pero se volvia real con mas de un
    # worker o mas de una instancia, que es justo lo que pasa al escalar.
    fuente = open(os.path.join(BACKEND, "server.py"), encoding="utf-8").read()
    arbol = ast.parse(fuente)
    verify = nodo_de_funcion(arbol, "verify_reset_code")
    ok("se encontro verify_reset_code en el AST", verify is not None)

    operadores = operadores_mongo_sobre(verify, "failed_attempts")
    nombres = [op for op, _ in operadores]
    ok(
        "el fallo se agrega con $push (no reescribiendo la lista)",
        "$push" in nombres,
        repr(nombres),
    )
    ok(
        "y la ventana se poda con $pull por fecha",
        "$pull" in nombres,
        repr(nombres),
    )
    # El unico `$set` que queda permitido sobre `failed_attempts` es el que la
    # limpia con una lista vacia literal tras el acierto: ese no depende de nada
    # que se haya leido. Un `$set` de una lista calculada en Python es el
    # read-modify-write de vuelta.
    sets_calculados = [
        ast.dump(valor)
        for op, valor in operadores
        if op == "$set"
        and not (isinstance(valor, ast.List) and not valor.elts)
    ]
    ok(
        "no queda ningun $set de una lista calculada en Python",
        sets_calculados == [],
        repr(sets_calculados)[:200],
    )
    ok(
        "el contador de por vida sigue yendo con $inc",
        "$inc" in [op for op, _ in operadores_mongo_sobre(verify, "attempts")],
        repr([op for op, _ in operadores_mongo_sobre(verify, "attempts")]),
    )
    # Y el comportamiento visible no cambio: la capa 3 ya exige que cada fallo
    # quede contado y que el quinto agote la ventana. Aqui solo se vuelve a mirar
    # que el acierto limpie la ventana, que es el otro camino de escritura.
    limpiar_topes()
    correo = "capa9-atomico-bos361@kwtest-local.com"
    registrar(correo)
    _, doc = pedir_codigo(correo, ip="10.9.1.1")
    codigo = doc["code"]
    malo = "000000" if codigo != "000000" else "111111"
    for _ in range(2):
        client.post(
            "/api/auth/verify-reset-code", params={"email": correo, "code": malo}
        )
    guardado = server.password_resets_col.find_one({"token": doc["token"]})
    ok(
        "dos fallos siguen quedando contados con la escritura nueva",
        guardado.get("attempts") == 2
        and len(guardado.get("failed_attempts") or []) == 2,
        repr((guardado.get("attempts"), len(guardado.get("failed_attempts") or []))),
    )
    res = client.post(
        "/api/auth/verify-reset-code", params={"email": correo, "code": codigo}
    )
    guardado = server.password_resets_col.find_one({"token": doc["token"]})
    ok(
        "y el acierto sigue limpiando la ventana",
        res.status_code == 200
        and (guardado.get("failed_attempts") or []) == [],
        f"{res.status_code}; {guardado.get('failed_attempts')!r}",
    )
    # El `$pull` por fecha tiene que quitar de verdad los fallos de antes de la
    # ventana, no solo estar escrito. Se simula moviendo el fallo al pasado y se
    # provoca otro: el viejo se va y queda solo el nuevo.
    limpiar_topes()
    _, doc = pedir_codigo(correo, ip="10.9.1.2")
    codigo = doc["code"]
    malo = "000000" if codigo != "000000" else "111111"
    atras = datetime.now(timezone.utc) - timedelta(
        minutes=server.RESET_CODE_ATTEMPTS_WINDOW_MINUTES + 1
    )
    server.password_resets_col.update_one(
        {"token": doc["token"]}, {"$set": {"failed_attempts": [atras, atras]}}
    )
    client.post("/api/auth/verify-reset-code", params={"email": correo, "code": malo})
    guardado = server.password_resets_col.find_one({"token": doc["token"]})
    ok(
        "el $pull se llevo los fallos de antes de la ventana (queda solo el nuevo)",
        len(guardado.get("failed_attempts") or []) == 1,
        repr(len(guardado.get("failed_attempts") or [])),
    )

    # --- 9c. el cubo de cuotas ya no es basura perpetua ---------------------
    #
    # `reset_quota_retry_after` poda SOLO la llave que se esta consultando, asi
    # que los renglones de una llave que no se vuelve a consultar nunca -- la IP
    # de paso, el correo que pidio una vez -- se quedaban para siempre. Y el PR de
    # BOS-359 lo acelero sin querer: `verify-reset-code` escribe un renglon por
    # llamada, y antes la coleccion solo crecia con `forgot-password`.
    indices = server.password_reset_requests_col.index_information()
    ok(
        "password_reset_requests tiene TTL sobre created_at",
        indices.get("created_at_1", {}).get("expireAfterSeconds")
        == server.RESET_REQUESTS_TTL_SEGUNDOS,
        repr(indices.get("created_at_1")),
    )
    ok(
        "y server.py lo reporta activo",
        server.PASSWORD_RESET_REQUESTS_TTL_ACTIVO is True,
        repr(server.PASSWORD_RESET_REQUESTS_TTL_ACTIVO),
    )
    # El indice compuesto que resuelve la consulta de cuota sigue en pie: el TTL
    # es otro indice, no lo reemplaza.
    ok(
        "el indice compuesto (key, created_at) de la consulta de cuota sigue ahi",
        any(
            [c for c, _ in info["key"]] == ["key", "created_at"]
            for nombre, info in indices.items()
            if nombre != "_id_"
        ),
        repr(sorted(indices)),
    )
    # La vida del renglon tiene que cubrir la ventana mas larga de TODOS los
    # cubos, o el TTL borraria renglones que todavia cuentan para un tope -- y
    # eso seria aflojar los topes por la puerta de atras. Esto es lo que amarra
    # las dos constantes, que viven en dos partes distintas del archivo.
    ventana_mas_larga = 60 * max(
        server.RESET_REQUESTS_PER_EMAIL_WINDOW_MINUTES,
        server.RESET_REQUESTS_PER_IP_WINDOW_MINUTES,
        server.RESET_VERIFY_PER_IP_WINDOW_MINUTES,
    )
    ok(
        "el TTL cubre la ventana mas larga de los cubos",
        server.RESET_REQUESTS_TTL_SEGUNDOS >= ventana_mas_larga,
        f"TTL {server.RESET_REQUESTS_TTL_SEGUNDOS} s vs ventana {ventana_mas_larga} s",
    )
    # Y el TTL NO es `expireAfterSeconds=0`. Sobre un campo que es la fecha de
    # creacion, 0 significa "borra el renglon recien escrito": apagaria los dos
    # topes de forgot y el de verify de una sola vez. Por eso
    # `asegurar_indice_ttl` dejo de tener el 0 clavado.
    ok(
        "el TTL no es 0 (sobre created_at eso apagaria los topes)",
        server.RESET_REQUESTS_TTL_SEGUNDOS > 0,
        str(server.RESET_REQUESTS_TTL_SEGUNDOS),
    )
    limpiar_topes()
    client.post(
        "/api/auth/forgot-password",
        json={"email": "capa9-ttl-bos361@kwtest-local.com"},
        headers={"X-Forwarded-For": "10.9.2.1"},
    )
    ok(
        "un renglon recien escrito sigue contando para el tope (el TTL no lo barre)",
        server.password_reset_requests_col.count_documents({"key": "ip:10.9.2.1"}) == 1,
        str(server.password_reset_requests_col.count_documents({"key": "ip:10.9.2.1"})),
    )
    # El renglon viejo si desaparece. mongomock aplica el TTL al leer, asi que ahi
    # se va en el acto; contra Mongo real el barrido tarda hasta ~60 s, asi que lo
    # que se puede exigir en los dos modos es que ya no cuente para el tope -- por
    # el TTL o por la ventana de la consulta.
    server.password_reset_requests_col.insert_one(
        {
            "key": "ip:10.9.2.2",
            "created_at": datetime.now(timezone.utc)
            - timedelta(seconds=server.RESET_REQUESTS_TTL_SEGUNDOS + 600),
        }
    )
    ok(
        "un renglon mas viejo que el TTL ya no cuenta para ningun tope",
        server.reset_quota_retry_after("ip:10.9.2.2", 1, 60) is None,
        repr(server.reset_quota_retry_after("ip:10.9.2.2", 1, 60)),
    )


def finish():
    passed = sum(1 for good, _, _ in CHECKS if good)
    failed = [(label, detail) for good, label, detail in CHECKS if not good]
    print()
    print("=" * 72)
    print(f"{passed} verificaciones en verde, {len(failed)} en rojo")
    for label, detail in failed:
        print(f"  FAIL {label} -- {detail}")
    print("=" * 72)
    return 1 if failed else 0


def main():
    print(f"base: {'Mongo real -> ' + os.environ['DB_NAME'] if MONGO_REAL else 'mongomock'}")
    try:
        return correr()
    finally:
        if MONGO_REAL:
            server.client.drop_database(os.environ["DB_NAME"])
            print(f"base {os.environ['DB_NAME']} borrada")


def correr():
    capa_1_la_respuesta_no_lleva_el_codigo_ni_el_token()
    capa_2_el_codigo_sale_de_secrets()
    capa_3_los_intentos_fallidos_queman_el_token()
    capa_4_no_se_pueden_pedir_codigos_en_bucle()
    capa_5_el_flujo_legitimo_corre_de_punta_a_punta()
    capa_6_el_camino_de_desarrollo_no_arranca_en_produccion()
    capa_7_el_mailer()
    capa_8_los_tres_huecos_de_bos_359()
    capa_9_lo_que_dejo_abierto_bos_359()
    return finish()


if __name__ == "__main__":
    sys.exit(main())
