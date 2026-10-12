"""
Regresion de `verify_admin`: un token no-ASCII debe dar 403, no 500 (BOS-236).

El PR #1 (BOS-136) cambio la comparacion del token de admin de `==` a
`hmac.compare_digest`, que es lo correcto para no filtrar el secreto por tiempo.
El detalle es que `compare_digest` sobre *cadenas* solo acepta ASCII:

    >>> hmac.compare_digest("token-con-n", "y" * 40)   # con enie de verdad
    TypeError: comparing strings with non-ASCII characters is not supported

Asi que `Authorization: Bearer <token con cualquier caracter no-ASCII>` levantaba
un TypeError sin capturar dentro del dependency y FastAPI respondia 500 en lugar
de 403. No era un bypass -- ningun token incorrecto quedaba aceptado -- pero un
500 es una senal distinguible de un 403 para quien sondea `/api/admin/*`.

Lo que verifica esta prueba, contra el `server.py` real y una base en memoria:

  * sin cabecera -> 401
  * token correcto -> 200
  * token ASCII incorrecto -> 403
  * token no-ASCII incorrecto -> 403 (esto era el 500)
  * la comparacion sigue siendo en tiempo constante y sobre bytes

    python backend/tests/test_verify_admin_token.py
"""
import hmac
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ADMIN_TOKEN = "admin-de-prueba-local-no-es-un-secreto"

# --- 1. Entorno. Los guards de arranque de BOS-136 exigen estas cinco. -------
os.environ.update(
    {
        "JWT_SECRET": "llave-de-prueba-local-no-es-un-secreto",
        "ADMIN_SECRET": ADMIN_TOKEN,
        "MONGO_URL": "mongodb://localhost:27017",
        "DB_NAME": "knowledge_wars_test_admin",
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

# raise_server_exceptions=False para que una excepcion sin capturar se vea como
# el 500 que veria el cliente, en vez de reventar la corrida entera. Es justo la
# diferencia que esta prueba vigila.
client = TestClient(server.app, raise_server_exceptions=False)

# `GET /api/admin/coupons` es el endpoint admin mas barato: solo lee la coleccion.
ADMIN_ENDPOINT = "/api/admin/coupons"

CHECKS = []


def ok(label, condition, detail=""):
    CHECKS.append((bool(condition), label, detail))
    mark = "ok  " if condition else "FAIL"
    print(f"{mark} {label}" + (f" -- {detail}" if detail else ""))
    return bool(condition)


def status_con(token):
    """Status de un GET al endpoint admin con ese token en el Bearer.

    La cabecera se manda como bytes a proposito. httpx se niega a codificar un
    valor de cabecera no-ASCII desde una cadena, pero en el cable una cabecera
    son bytes y cualquiera puede mandar los que quiera; Starlette los decodifica
    con latin-1, asi que a `verify_admin` le llega una cadena con caracteres
    no-ASCII igual que en produccion. Mandar bytes es lo que reproduce el caso
    real, no un atajo de la prueba.
    """
    return client.get(
        ADMIN_ENDPOINT,
        headers={"Authorization": f"Bearer {token}".encode("utf-8")},
    ).status_code


def main():
    print("=" * 72)
    print("Capa 1 -- la trampa de compare_digest sobre cadenas sigue ahi")
    print("=" * 72)
    # Si CPython alguna vez acepta cadenas no-ASCII aqui, esta prueba deja de
    # tener motivo; mientras falle, la comparacion en bytes es obligatoria.
    try:
        hmac.compare_digest("token-con-ñ", "y" * 40)
        ok("compare_digest(str no-ASCII) levanta TypeError", False, "no levanto nada")
    except TypeError as error:
        ok("compare_digest(str no-ASCII) levanta TypeError", True, str(error))

    print()
    print("=" * 72)
    print("Capa 2 -- verify_admin por HTTP")
    print("=" * 72)

    sin_cabecera = client.get(ADMIN_ENDPOINT).status_code
    ok("sin Authorization -> 401", sin_cabecera == 401, str(sin_cabecera))

    correcto = status_con(ADMIN_TOKEN)
    ok("token correcto -> 200", correcto == 200, str(correcto))

    malo_ascii = status_con("x" * len(ADMIN_TOKEN))
    ok("token ASCII incorrecto -> 403", malo_ascii == 403, str(malo_ascii))

    # BOS-242 endurecio el parseo del esquema: `Bearer` sin token ya no es un
    # credencial incorrecto (403) sino la ausencia de credencial (401), igual
    # que el header ausente. Los casos de esquema estan en
    # test_authorization_header_parsing.py.
    vacio = status_con("")
    ok("token vacio -> 401", vacio == 401, str(vacio))

    # El caso de BOS-236. Cada uno de estos devolvia 500 antes del arreglo.
    no_ascii = {
        "enie": "contrasena-con-ñ",
        "acentos": "tóken-inválido",
        "cirilico": "токен",
        "emoji": "token-\U0001f511",
        "correcto-mas-sufijo-no-ascii": ADMIN_TOKEN + "ñ",
    }
    for etiqueta, token in no_ascii.items():
        codigo = status_con(token)
        ok(f"token no-ASCII ({etiqueta}) -> 403", codigo == 403, str(codigo))

    print()
    print("=" * 72)
    print("Capa 3 -- la comparacion sigue en tiempo constante y sobre bytes")
    print("=" * 72)
    fuente = inspect.getsource(server.verify_admin)
    ok("verify_admin usa hmac.compare_digest (no ==)", "hmac.compare_digest" in fuente)
    ok("compara bytes, no cadenas", 'encode("utf-8")' in fuente)

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
