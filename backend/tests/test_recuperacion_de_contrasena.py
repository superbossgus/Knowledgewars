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
  3. **cinco intentos fallidos queman el token**: despues ni el codigo correcto
     sirve, y `reset-password` tampoco acepta ese token. Cuatro fallos seguidos
     de un acierto si pasan
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
    print("Capa 3 -- cinco intentos fallidos queman el token")
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
            guardado.get("attempts") == intento,
            repr(guardado.get("attempts")),
        )

    quemado = server.password_resets_col.find_one({"token": token})
    ok(
        "al quinto fallo el token queda marcado como usado (quemado)",
        quemado.get("used") is True,
        repr(quemado.get("used")),
    )

    # Y ahora el codigo CORRECTO tampoco sirve. Esto es el punto entero: un
    # codigo de 6 digitos sin tope de intentos no es un secreto.
    res = client.post(f"/api/auth/verify-reset-code?email={correo}&code={codigo}")
    ok(
        "despues de quemarlo, el codigo correcto tambien da 400",
        res.status_code == 400,
        res.text[:150],
    )
    ok(
        "el 400 del token quemado no dice que esta quemado",
        "intent" not in res.text.lower() and "quemad" not in res.text.lower(),
        res.text[:150],
    )

    # Ni el token sirve para cambiar la contrasena por su cuenta.
    res = client.post(
        "/api/auth/reset-password", json={"token": token, "new_password": NUEVA}
    )
    ok(
        "reset-password rechaza el token quemado -> 400",
        res.status_code == 400,
        res.text[:150],
    )
    usuario = server.users_col.find_one({"email": correo})
    ok(
        "y la contrasena de la cuenta no se movio",
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
        guardado.get("attempts") == 5 and guardado.get("used") is True,
        repr({"attempts": guardado.get("attempts"), "used": guardado.get("used")}),
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
    return finish()


if __name__ == "__main__":
    sys.exit(main())
