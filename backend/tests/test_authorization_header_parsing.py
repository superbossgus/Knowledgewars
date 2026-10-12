"""
Regresion del parseo del header Authorization en los dos dependencies (BOS-242).

`backend/server.py` sacaba el token del header con `str.replace`, en
`get_current_user` (JWT) y en `verify_admin` (admin):

    token = authorization.replace("Bearer ", "")

`replace` no es un strip de prefijo. Sustituye todas las ocurrencias en
cualquier posicion y no exige que el esquema este presente, asi que:

  * `Authorization: <secreto>` sin el `Bearer ` -> `replace` no encuentra nada,
    el token queda igual al secreto completo y se aceptaba. El esquema era de
    facto opcional, una desviacion del RFC 6750 seccion 2.1.
  * `Authorization: Bearer Bearer <secreto>` -> se borraban las dos ocurrencias
    y tambien se aceptaba.
  * un secreto que contuviera la subcadena `Bearer ` quedaba mutilado y la
    autenticacion fallaba con el header correcto.

No era un bypass: en ningun caso se aceptaba un token distinto del correcto --
habia que conocerlo igual. Era laxitud de parseo.

El arreglo: `utils.extract_bearer_token` parsea el esquema explicitamente y los
dos dependencies lo usan.

Codigo de respuesta elegido a proposito (ver el comentario en `verify_admin`):
un header sin credencial Bearer legible -- ausente, con otro esquema, o
`Bearer` sin token -- da **401**, igual que el header ausente de siempre. El
**403** queda reservado al token bien formado pero incorrecto, que es el
contrato que ya consumian los clientes. En `get_current_user` no cambia nada
observable: el header ilegible se ignora, cae al cookie de sesion y termina en
el 401 del final.

Compatibilidad verificada antes de endurecer: los 10 sitios que mandan el
header en el repo (`frontend/src/lib/api.js`, `frontend/src/pages/AdminPage.jsx`
y las pruebas) usan `Bearer ${token}`. No hay `fetch` crudo en el frontend que
se salte el interceptor.

Lo que verifica esta prueba, contra el `server.py` real y una base en memoria:

  * `extract_bearer_token` como unidad, incluidos los casos raros
  * `verify_admin` por HTTP: con Bearer, sin esquema, esquema equivocado,
    espacios extra, `Bearer` duplicado, sin token
  * `get_current_user` por HTTP: los mismos casos con un JWT de verdad
  * que no quedo ningun `replace("Bearer "` en server.py
  * que `verify_admin` sigue comparando bytes con hmac.compare_digest (BOS-236)

    python backend/tests/test_authorization_header_parsing.py
"""
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
        "DB_NAME": "knowledge_wars_test_auth_header",
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
from utils import extract_bearer_token

# raise_server_exceptions=False para ver el 500 que veria el cliente si algo
# escapa sin capturar, en vez de reventar la corrida entera.
client = TestClient(server.app, raise_server_exceptions=False)

# El endpoint admin mas barato (solo lee la coleccion) y el de usuario mas
# barato (solo devuelve el documento del current_user).
ADMIN_ENDPOINT = "/api/admin/coupons"
USER_ENDPOINT = "/api/auth/me"

CHECKS = []


def ok(label, condition, detail=""):
    CHECKS.append((bool(condition), label, detail))
    mark = "ok  " if condition else "FAIL"
    print(f"{mark} {label}" + (f" -- {detail}" if detail else ""))
    return bool(condition)


def status(endpoint, header_value):
    """Status de un GET con ese valor literal en Authorization.

    El valor se manda como bytes: httpx se niega a codificar una cabecera
    no-ASCII desde una cadena, y en el cable una cabecera son bytes de todos
    modos. Starlette los decodifica con latin-1, que es lo que pasa en
    produccion.
    """
    return client.get(
        endpoint,
        headers={"Authorization": header_value.encode("utf-8")},
    ).status_code


def registrar_usuario():
    """Registrar un usuario de prueba y devolver su JWT."""
    respuesta = client.post(
        "/api/auth/register",
        json={
            "email": "bos242@kwtest-local.com",
            "password": "contrasena-de-prueba-local",
            "display_name": "Prueba BOS-242",
            "country_code": "MX",
            "favorite_topic": "historia",
            "language": "es",
        },
    )
    if respuesta.status_code != 200:
        raise SystemExit(
            f"no se pudo registrar el usuario de prueba: "
            f"{respuesta.status_code} {respuesta.text}"
        )
    return respuesta.json()["token"]


def main():
    print("=" * 72)
    print("Capa 1 -- extract_bearer_token como unidad")
    print("=" * 72)

    casos_unidad = [
        # (etiqueta, header, token esperado)
        ("header normal", "Bearer abc123", "abc123"),
        ("esquema en minusculas", "bearer abc123", "abc123"),
        ("esquema en mayusculas", "BEARER abc123", "abc123"),
        ("espacios extra entre esquema y token", "Bearer    abc123", "abc123"),
        ("espacios al final", "Bearer abc123   ", "abc123"),
        ("header ausente", None, None),
        ("cadena vacia", "", None),
        ("token pelado, sin esquema", "abc123", None),
        ("el secreto de admin pelado", ADMIN_TOKEN, None),
        ("esquema equivocado (Basic)", "Basic abc123", None),
        ("esquema equivocado (Token)", "Token abc123", None),
        ("Bearer sin token", "Bearer", None),
        ("Bearer con espacio y nada mas", "Bearer ", None),
        ("Bearer duplicado", "Bearer Bearer abc123", "Bearer abc123"),
        # El caso 3 del reporte: con `replace` un secreto que contuviera la
        # subcadena se mutilaba; ahora el token sale intacto.
        ("token que contiene 'Bearer '", "Bearer xxBearer yy", "xxBearer yy"),
    ]
    for etiqueta, header, esperado in casos_unidad:
        obtenido = extract_bearer_token(header)
        ok(
            f"extract_bearer_token: {etiqueta}",
            obtenido == esperado,
            f"esperaba {esperado!r}, obtuve {obtenido!r}",
        )

    print()
    print("=" * 72)
    print("Capa 2 -- verify_admin por HTTP")
    print("=" * 72)

    sin_cabecera = client.get(ADMIN_ENDPOINT).status_code
    ok("sin Authorization -> 401", sin_cabecera == 401, str(sin_cabecera))

    casos_admin = [
        ("token correcto con Bearer -> 200", f"Bearer {ADMIN_TOKEN}", 200),
        ("esquema en minusculas -> 200", f"bearer {ADMIN_TOKEN}", 200),
        ("espacios extra -> 200", f"Bearer    {ADMIN_TOKEN}", 200),
        # El agujero de BOS-242: esto devolvia 200 porque `replace` no exigia
        # el esquema. Ahora es 401.
        ("secreto correcto SIN esquema -> 401", ADMIN_TOKEN, 401),
        # Esto tambien devolvia 200: `replace` borraba las dos ocurrencias.
        # Ahora es 403, no 401: sintacticamente es un Bearer valido cuyo
        # credencial es literalmente `Bearer <secreto>`, o sea un token
        # incorrecto. Lo que importa es que ya no se acepta.
        ("Bearer duplicado -> 403", f"Bearer Bearer {ADMIN_TOKEN}", 403),
        ("esquema equivocado (Basic) -> 401", f"Basic {ADMIN_TOKEN}", 401),
        ("esquema equivocado (Token) -> 401", f"Token {ADMIN_TOKEN}", 401),
        ("Bearer sin token -> 401", "Bearer", 401),
        ("Bearer con espacio y nada mas -> 401", "Bearer ", 401),
        # Token bien formado pero incorrecto: sigue siendo 403, no cambiamos
        # la politica de rechazo.
        ("token ASCII incorrecto -> 403", "Bearer " + "x" * len(ADMIN_TOKEN), 403),
        # BOS-236: no-ASCII sigue dando 403, no 500.
        ("token no-ASCII incorrecto -> 403", "Bearer tóken-inválido-ñ", 403),
    ]
    for etiqueta, header, esperado in casos_admin:
        codigo = status(ADMIN_ENDPOINT, header)
        ok(f"verify_admin: {etiqueta}", codigo == esperado, str(codigo))

    print()
    print("=" * 72)
    print("Capa 3 -- get_current_user por HTTP, con un JWT de verdad")
    print("=" * 72)

    jwt_token = registrar_usuario()
    ok("el registro devolvio un JWT", bool(jwt_token))

    casos_usuario = [
        ("JWT con Bearer -> 200", f"Bearer {jwt_token}", 200),
        ("esquema en minusculas -> 200", f"bearer {jwt_token}", 200),
        ("espacios extra -> 200", f"Bearer    {jwt_token}", 200),
        # Antes el JWT pelado se aceptaba igual; ahora el header se ignora y
        # cae al 401 del final de get_current_user.
        ("JWT SIN esquema -> 401", jwt_token, 401),
        ("Bearer duplicado -> 401", f"Bearer Bearer {jwt_token}", 401),
        ("esquema equivocado (Basic) -> 401", f"Basic {jwt_token}", 401),
        ("Bearer sin token -> 401", "Bearer", 401),
        ("JWT invalido con Bearer -> 401", "Bearer no-es-un-jwt", 401),
    ]
    for etiqueta, header, esperado in casos_usuario:
        codigo = status(USER_ENDPOINT, header)
        ok(f"get_current_user: {etiqueta}", codigo == esperado, str(codigo))

    print()
    print("=" * 72)
    print("Capa 4 -- el codigo no volvio a replace, y BOS-236 sigue en pie")
    print("=" * 72)

    fuente_server = inspect.getsource(server)
    ok(
        "no queda ningun replace(\"Bearer \" en server.py",
        'replace("Bearer ' not in fuente_server,
        "aparecio otra vez el strip con replace",
    )

    for nombre, funcion in (
        ("get_current_user", server.get_current_user),
        ("verify_admin", server.verify_admin),
    ):
        fuente = inspect.getsource(funcion)
        ok(
            f"{nombre} usa extract_bearer_token",
            "extract_bearer_token" in fuente,
        )

    # No regresar BOS-236: la comparacion del token de admin sigue en tiempo
    # constante y sobre bytes.
    fuente_admin = inspect.getsource(server.verify_admin)
    ok(
        "verify_admin usa hmac.compare_digest (no ==)",
        "hmac.compare_digest" in fuente_admin,
    )
    ok("verify_admin compara bytes, no cadenas", 'encode("utf-8")' in fuente_admin)

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
