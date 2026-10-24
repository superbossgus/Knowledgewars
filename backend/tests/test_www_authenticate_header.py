"""
Los 401 de recurso protegido mandan `WWW-Authenticate: Bearer` (BOS-249).

El [RFC 6750 seccion 3](https://datatracker.ietf.org/doc/html/rfc6750#section-3)
exige que un 401 a una peticion de recurso protegido traiga el reto
`WWW-Authenticate` con el esquema que el servidor acepta. `backend/server.py`
no lo mandaba en ningun sitio; el hueco es anterior a BOS-242 (el
`if not authorization` de antes del cambio de parseo tenia exactamente el
mismo). No es una vulnerabilidad: no cambia quien entra ni que se acepta, solo
la forma de la respuesta -- un cliente conforme al RFC usa esa cabecera para
saber con que esquema reintentar.

Reparto que esta prueba fija:

  * `get_current_user` y `verify_admin` son recursos protegidos por Bearer. Sus
    401 llevan el reto, pelado: sin `realm` (no hay reino que anunciar) y sin
    `error`/`error_description` (el RFC pide no mandar codigo de error cuando
    la peticion no presento credencial, y una descripcion que refleje la
    entrada seria una filtracion).
  * `/api/auth/login` **no** lo lleva, a proposito. Es un endpoint de
    intercambio de credencial, no un recurso protegido: no existe ningun token
    con el que reintentar ese POST, asi que anunciar `Bearer` mandaria al
    cliente conforme a repetir el login con un token. Decision documentada en
    el codigo junto al 401. (`/api/auth/google/session` estaba del mismo lado
    del reparto; se quito entero en BOS-350 y por eso ya no aparece en el
    inventario.)
  * El **403 no se toco**. El reparto de BOS-242 (401 = no presentaste
    credencial, 403 = credencial bien formada pero incorrecta) sigue igual, y
    el 403 no gana cabecera ni cambia de codigo.

Lo que verifica, contra el `server.py` real y una base en memoria:

  * inventario por AST de *todos* los 401 del archivo, para que un 401 nuevo
    sin decision explicita rompa la prueba en vez de pasar inadvertido
  * `verify_admin` por HTTP: los 401 traen el reto, los 403 siguen siendo 403
    y sin reto, el 200 no cambia
  * `get_current_user` por HTTP: los 401 traen el reto, incluido el del cookie
    de sesion expirado
  * los 401 del login siguen sin reto

    python backend/tests/test_www_authenticate_header.py
"""
import ast
import inspect
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ADMIN_TOKEN = "admin-de-prueba-local-no-es-un-secreto"

# --- 1. Entorno. Los guards de arranque de BOS-136 exigen estas cinco. -------
os.environ.update(
    {
        "JWT_SECRET": "llave-de-prueba-local-no-es-un-secreto",
        "ADMIN_SECRET": ADMIN_TOKEN,
        "MONGO_URL": "mongodb://localhost:27017",
        "DB_NAME": "knowledge_wars_test_www_authenticate",
        "CORS_ORIGINS": "http://localhost:3000",
        "ANTHROPIC_API_KEY": "sin-uso-esta-prueba-no-genera-preguntas",
    }
)

# --- 2. La base en memoria, antes de importar server.py ---------------------
import mongomock
import pymongo

pymongo.MongoClient = mongomock.MongoClient

# --- 3. La app real --------------------------------------------------------
from fastapi.testclient import TestClient

import server

# raise_server_exceptions=False para ver el 500 que veria el cliente si algo
# escapa sin capturar, en vez de reventar la corrida entera.
client = TestClient(server.app, raise_server_exceptions=False)

ADMIN_ENDPOINT = "/api/admin/coupons"
USER_ENDPOINT = "/api/auth/me"
LOGIN_ENDPOINT = "/api/auth/login"

RETO = "Bearer"

# Inventario esperado de los 401 de server.py: (funcion, lleva_reto) -> cuantos.
# Si aparece un 401 nuevo, esta prueba falla y obliga a decidir de que lado
# cae: recurso protegido (lleva reto) o intercambio de credencial (no).
INVENTARIO_401_ESPERADO = {
    # Recurso protegido: cookie de sesion expirado + el 401 final.
    ("get_current_user", True): 2,
    # Recurso protegido: no se presento credencial Bearer legible (BOS-242).
    ("verify_admin", True): 1,
    # Intercambio de credencial: usuario inexistente + contrasena incorrecta.
    ("login", False): 2,
    # `process_google_session` tenia 1 x 401 sin reto. El endpoint se quito en
    # BOS-350; si alguien lo revive, este inventario falla y obliga a volver a
    # decidir de que lado cae.
}

CHECKS = []


def ok(label, condition, detail=""):
    CHECKS.append((bool(condition), label, detail))
    mark = "ok  " if condition else "FAIL"
    print(f"{mark} {label}" + (f" -- {detail}" if detail else ""))
    return bool(condition)


def inventario_401(fuente):
    """Todos los `raise HTTPException(status_code=401, ...)` del archivo.

    Devuelve un Counter de (funcion que lo lanza, si pasa headers=BEARER_CHALLENGE).
    Se hace por AST y no por texto porque lo que importa es el argumento real
    que recibe la excepcion, no que la cadena aparezca cerca.
    """
    encontrados = Counter()
    arbol = ast.parse(fuente)

    for nodo in ast.walk(arbol):
        if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for hijo in ast.walk(nodo):
            if not isinstance(hijo, ast.Raise):
                continue
            llamada = hijo.exc
            if not isinstance(llamada, ast.Call):
                continue
            objetivo = llamada.func
            nombre = getattr(objetivo, "id", None) or getattr(objetivo, "attr", None)
            if nombre != "HTTPException":
                continue
            claves = {k.arg: k.value for k in llamada.keywords}
            codigo = claves.get("status_code")
            if not (isinstance(codigo, ast.Constant) and codigo.value == 401):
                continue
            cabeceras = claves.get("headers")
            lleva_reto = (
                isinstance(cabeceras, ast.Name)
                and cabeceras.id == "BEARER_CHALLENGE"
            )
            encontrados[(nodo.name, lleva_reto)] += 1

    return encontrados


def respuesta(endpoint, header_value=None):
    """GET con ese valor literal en Authorization (o sin cabecera si es None).

    El valor se manda como bytes: httpx se niega a codificar una cabecera
    no-ASCII desde una cadena, y en el cable una cabecera son bytes de todos
    modos. Starlette los decodifica con latin-1, igual que en produccion.
    """
    if header_value is None:
        return client.get(endpoint)
    return client.get(
        endpoint,
        headers={"Authorization": header_value.encode("utf-8")},
    )


def registrar_usuario():
    """Registrar un usuario de prueba y devolver (JWT, id del usuario)."""
    datos = client.post(
        "/api/auth/register",
        json={
            "email": "bos249@kwtest-local.com",
            "password": "contrasena-de-prueba-local",
            "display_name": "Prueba BOS-249",
            "country_code": "MX",
            "favorite_topic": "historia",
            "language": "es",
        },
    )
    if datos.status_code != 200:
        raise SystemExit(
            f"no se pudo registrar el usuario de prueba: "
            f"{datos.status_code} {datos.text}"
        )
    cuerpo = datos.json()
    usuario = cuerpo["user"]
    return cuerpo["token"], usuario.get("id") or usuario.get("user_id")


def main():
    print("=" * 72)
    print("Capa 1 -- la constante del reto")
    print("=" * 72)

    ok(
        "server.BEARER_CHALLENGE existe",
        hasattr(server, "BEARER_CHALLENGE"),
    )
    ok(
        'BEARER_CHALLENGE == {"WWW-Authenticate": "Bearer"}',
        getattr(server, "BEARER_CHALLENGE", None) == {"WWW-Authenticate": RETO},
        repr(getattr(server, "BEARER_CHALLENGE", None)),
    )
    # Pelado a proposito: sin realm, sin error, sin error_description. Un
    # error_description es el sitio por donde se filtraria el token recibido.
    valor = getattr(server, "BEARER_CHALLENGE", {}).get("WWW-Authenticate", "")
    ok(
        "el reto va pelado (sin realm/error/error_description)",
        valor == RETO,
        repr(valor),
    )

    print()
    print("=" * 72)
    print("Capa 2 -- inventario por AST de todos los 401 de server.py")
    print("=" * 72)

    encontrado = inventario_401(inspect.getsource(server))
    esperado = Counter(INVENTARIO_401_ESPERADO)

    for (funcion, lleva_reto), cuantos in sorted(esperado.items()):
        etiqueta = "con reto" if lleva_reto else "SIN reto (a proposito)"
        ok(
            f"{funcion}: {cuantos} x 401 {etiqueta}",
            encontrado.get((funcion, lleva_reto), 0) == cuantos,
            f"encontre {encontrado.get((funcion, lleva_reto), 0)}",
        )

    sobrantes = {clave: n for clave, n in encontrado.items() if esperado.get(clave, 0) != n}
    ok(
        "no hay ningun 401 fuera del inventario",
        not sobrantes,
        f"sin decision explicita: {sorted(sobrantes.items())}"
        if sobrantes
        else "",
    )

    print()
    print("=" * 72)
    print("Capa 3 -- verify_admin por HTTP")
    print("=" * 72)

    # Los 401 de "no presentaste credencial Bearer legible" (BOS-242).
    casos_401 = [
        ("sin Authorization", None),
        ("secreto correcto SIN esquema", ADMIN_TOKEN),
        ("esquema equivocado (Basic)", f"Basic {ADMIN_TOKEN}"),
        ("esquema equivocado (Token)", f"Token {ADMIN_TOKEN}"),
        ("Bearer sin token", "Bearer"),
        ("Bearer con espacio y nada mas", "Bearer "),
    ]
    for etiqueta, header in casos_401:
        res = respuesta(ADMIN_ENDPOINT, header)
        ok(f"verify_admin {etiqueta} -> 401", res.status_code == 401, str(res.status_code))
        ok(
            f"verify_admin {etiqueta} -> WWW-Authenticate: {RETO}",
            res.headers.get("WWW-Authenticate") == RETO,
            repr(res.headers.get("WWW-Authenticate")),
        )

    # El 403 no cambio: ni de codigo, ni gana cabecera. El reparto de BOS-242
    # (403 = credencial bien formada pero incorrecta) se queda como estaba.
    casos_403 = [
        ("token ASCII incorrecto", "Bearer " + "x" * len(ADMIN_TOKEN)),
        ("token no-ASCII incorrecto", "Bearer tóken-inválido-ñ"),
        ("Bearer duplicado", f"Bearer Bearer {ADMIN_TOKEN}"),
    ]
    for etiqueta, header in casos_403:
        res = respuesta(ADMIN_ENDPOINT, header)
        ok(
            f"verify_admin {etiqueta} -> sigue 403 (no se movio a 401)",
            res.status_code == 403,
            str(res.status_code),
        )
        ok(
            f"verify_admin {etiqueta} -> 403 sin WWW-Authenticate",
            "WWW-Authenticate" not in res.headers,
            repr(res.headers.get("WWW-Authenticate")),
        )

    # El camino feliz no se toco.
    res = respuesta(ADMIN_ENDPOINT, f"Bearer {ADMIN_TOKEN}")
    ok("verify_admin token correcto -> 200", res.status_code == 200, str(res.status_code))
    ok(
        "verify_admin 200 sin WWW-Authenticate",
        "WWW-Authenticate" not in res.headers,
        repr(res.headers.get("WWW-Authenticate")),
    )

    print()
    print("=" * 72)
    print("Capa 4 -- get_current_user por HTTP, con un JWT de verdad")
    print("=" * 72)

    jwt_token, user_id = registrar_usuario()
    ok("el registro devolvio un JWT", bool(jwt_token))

    casos_usuario = [
        ("sin Authorization", None),
        ("JWT SIN esquema", jwt_token),
        ("Bearer duplicado", f"Bearer Bearer {jwt_token}"),
        ("esquema equivocado (Basic)", f"Basic {jwt_token}"),
        ("Bearer sin token", "Bearer"),
        ("JWT invalido con Bearer", "Bearer no-es-un-jwt"),
    ]
    for etiqueta, header in casos_usuario:
        res = respuesta(USER_ENDPOINT, header)
        ok(
            f"get_current_user {etiqueta} -> 401",
            res.status_code == 401,
            str(res.status_code),
        )
        ok(
            f"get_current_user {etiqueta} -> WWW-Authenticate: {RETO}",
            res.headers.get("WWW-Authenticate") == RETO,
            repr(res.headers.get("WWW-Authenticate")),
        )

    res = respuesta(USER_ENDPOINT, f"Bearer {jwt_token}")
    ok("get_current_user JWT con Bearer -> 200", res.status_code == 200, str(res.status_code))
    ok(
        "get_current_user 200 sin WWW-Authenticate",
        "WWW-Authenticate" not in res.headers,
        repr(res.headers.get("WWW-Authenticate")),
    )

    print()
    print("=" * 72)
    print("Capa 5 -- el 401 del cookie de sesion expirado")
    print("=" * 72)

    # Es el otro 401 de get_current_user y no lo cubre ninguna prueba previa:
    # hay que sembrar la sesion vencida a mano. Se manda el cookie en la
    # cabecera cruda para no depender del manejo de cookies del TestClient.
    server.user_sessions_col.insert_one(
        {
            "session_token": "sesion-vencida-bos249",
            "user_id": user_id,
            "expires_at": datetime.now(timezone.utc) - timedelta(hours=1),
        }
    )
    res = client.get(
        USER_ENDPOINT,
        headers={"Cookie": "session_token=sesion-vencida-bos249"},
    )
    ok("cookie de sesion expirado -> 401", res.status_code == 401, str(res.status_code))
    ok(
        "detail sigue siendo 'Session expired'",
        res.json().get("detail") == "Session expired",
        repr(res.json()),
    )
    ok(
        f"cookie expirado -> WWW-Authenticate: {RETO}",
        res.headers.get("WWW-Authenticate") == RETO,
        repr(res.headers.get("WWW-Authenticate")),
    )

    print()
    print("=" * 72)
    print("Capa 6 -- los 401 de intercambio de credencial siguen sin reto")
    print("=" * 72)

    # Decision de BOS-249: el login no es un recurso protegido por Bearer, asi
    # que no anuncia el esquema. Si alguien se lo agrega, esta prueba falla y
    # obliga a justificarlo.
    res = client.post(
        LOGIN_ENDPOINT,
        json={"email": "bos249@kwtest-local.com", "password": "contrasena-equivocada"},
    )
    ok("login con contrasena incorrecta -> 401", res.status_code == 401, str(res.status_code))
    ok(
        "login 401 SIN WWW-Authenticate (a proposito)",
        "WWW-Authenticate" not in res.headers,
        repr(res.headers.get("WWW-Authenticate")),
    )

    res = client.post(
        LOGIN_ENDPOINT,
        json={"email": "no-existe@kwtest-local.com", "password": "lo-que-sea"},
    )
    ok("login con usuario inexistente -> 401", res.status_code == 401, str(res.status_code))
    ok(
        "login 401 (usuario inexistente) SIN WWW-Authenticate",
        "WWW-Authenticate" not in res.headers,
        repr(res.headers.get("WWW-Authenticate")),
    )

    return finish()


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


if __name__ == "__main__":
    sys.exit(main())
