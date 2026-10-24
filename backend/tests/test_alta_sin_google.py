"""
El alta de usuario ya no cuelga de Emergent (BOS-350, opcion A).

Se quito el login con Google. No porque estuviera roto hoy -- la sonda del 24
de octubre de 2026 encontro el canje del `session_id` vivo -- sino porque
colgaba de dos dominios de Emergent, la plataforma que la unidad dejo en abril
de 2026: la pantalla de consentimiento (`auth.emergentagent.com`, que ya
contesta 404 en la ruta que usaba el frontend) y el canje
(`demobackend.emergentagent.com`). Quien controlara esos dominios controlaba
quien entra a Knowledge Wars. Los numeros estan en `ALTA_DE_USUARIO.md`.

Lo que esta prueba fija:

  * el endpoint `/api/auth/google/session` **no existe** y ningun codigo vivo
    de `server.py` ni de `LoginPage.jsx` nombra a `emergentagent.com` -- los
    comentarios si, y deben: son la unica forma de que dentro de dos anos se
    sepa que se quito y por que. Si alguien revive el endpoint o la URL, esto
    falla
  * el alta por correo sigue completa: registrarse devuelve JWT y 5 partidas,
    y con ese correo se puede entrar
  * **las cuentas viejas de Google no quedaron encerradas.** Son las unicas
    cuentas sin contrasena que existen. Su rescate es "olvide mi contrasena",
    y hasta BOS-350 ese camino tambien les contestaba "usa Google Sign-In" en
    vez de mandarles el codigo. El recorrido completo -- pedir codigo,
    verificarlo, poner contrasena, entrar -- se prueba de punta a punta
  * tras ponerse contrasena, `auth_provider` queda en `"email"`: ya no se
    miente sobre un proveedor que aqui no existe
  * el cookie `session_token` **sigue aceptandose a proposito**, para no
    expulsar a una sesion que siga viva en el navegador de alguien (las de
    `remember_me` duraban 100 anos). Lo que ya no pasa es que se emitan
    cookies nuevos: nada escribe en `user_sessions`

    python backend/tests/test_alta_sin_google.py
"""
import ast
import os
import re
import sys
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(AQUI)
RAIZ = os.path.dirname(BACKEND)
sys.path.insert(0, BACKEND)

# --- 1. Entorno. Los guards de arranque de BOS-136 exigen estas cinco. -------
os.environ.update(
    {
        "JWT_SECRET": "llave-de-prueba-local-no-es-un-secreto",
        "ADMIN_SECRET": "admin-de-prueba-local-no-es-un-secreto",
        "MONGO_URL": "mongodb://localhost:27017",
        "DB_NAME": "knowledge_wars_test_alta_sin_google",
        "CORS_ORIGINS": "http://localhost:3000",
        "ANTHROPIC_API_KEY": "sin-uso-esta-prueba-no-genera-preguntas",
    }
)

# --- 2. La base en memoria, antes de importar server.py ---------------------
# mongomock alcanza: esta prueba solo hace find_one/insert_one/update_one. (La
# metrica 3 si necesita Mongo real porque usa `$expr`; ver scripts/METRICA_3.md.)
import mongomock
import pymongo

pymongo.MongoClient = mongomock.MongoClient

# --- 3. La app real --------------------------------------------------------
from fastapi.testclient import TestClient

import server

client = TestClient(server.app, raise_server_exceptions=False)

CORREO = "alta-bos350@kwtest-local.com"
CONTRASENA = "contrasena-de-prueba-local"
CORREO_GOOGLE = "cuenta-vieja-de-google-bos350@kwtest-local.com"
CONTRASENA_NUEVA = "la-que-se-pone-en-el-rescate"

CHECKS = []


def ok(label, condition, detail=""):
    CHECKS.append((bool(condition), label, detail))
    mark = "ok  " if condition else "FAIL"
    print(f"{mark} {label}" + (f" -- {detail}" if detail else ""))
    return bool(condition)


def leer(ruta):
    with open(ruta, encoding="utf-8") as fh:
        return fh.read()


def rutas_registradas():
    return {getattr(r, "path", None) for r in server.app.routes}


def cadenas_del_codigo(fuente_python):
    """Todas las cadenas literales del archivo, por AST.

    Se mira el codigo, no el texto: un comentario que explique que se quito y
    por que **debe** poder nombrar a Emergent -- es la unica forma de que esto
    se entienda dentro de dos anos. Lo que no puede existir es una cadena con
    ese dominio, porque una cadena es algo a lo que el servidor le puede
    hablar. Los docstrings se excluyen por lo mismo que los comentarios.
    """
    arbol = ast.parse(fuente_python)
    docstrings = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(nodo, clean=False)
            if doc is not None:
                docstrings.add(doc)
    return [
        n.value
        for n in ast.walk(arbol)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and n.value not in docstrings
    ]


def sin_comentarios_js(fuente_js):
    """El mismo reparto para el JSX: fuera `//...` y `/* ... */`."""
    sin_bloque = re.sub(r"/\*.*?\*/", " ", fuente_js, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", sin_bloque, flags=re.M)


# ---------------------------------------------------------------------------
def capa_1_no_queda_rastro_de_emergent():
    print("=" * 72)
    print("Capa 1 -- no queda rastro de Emergent en el camino de alta")
    print("=" * 72)

    rutas = rutas_registradas()
    ok(
        "/api/auth/google/session ya no es una ruta de la app",
        "/api/auth/google/session" not in rutas,
        "sigue registrada" if "/api/auth/google/session" in rutas else "",
    )
    # Las que si tienen que seguir ahi. Si esta prueba pasara porque se cayo la
    # app entera, estas lo delatan.
    for ruta in ("/api/auth/register", "/api/auth/login", "/api/auth/me",
                 "/api/auth/forgot-password", "/api/auth/reset-password"):
        ok(f"{ruta} sigue registrada", ruta in rutas)

    fuente_servidor = leer(os.path.join(BACKEND, "server.py"))
    cadenas = cadenas_del_codigo(fuente_servidor)
    sucias = [c for c in cadenas if "emergentagent.com" in c]
    ok(
        "ninguna cadena de server.py nombra emergentagent.com",
        not sucias,
        f"encontre {sucias}" if sucias else "",
    )
    rutas_google = [c for c in cadenas if "auth/google" in c]
    ok(
        "ninguna cadena de server.py declara una ruta de Google",
        not rutas_google,
        f"encontre {rutas_google}" if rutas_google else "",
    )
    ok(
        "server.py no importa httpx (solo lo usaba el canje de Google)",
        not re.search(r"^import httpx\b", fuente_servidor, re.M),
    )

    login_jsx = sin_comentarios_js(
        leer(os.path.join(RAIZ, "frontend", "src", "pages", "LoginPage.jsx"))
    )
    ok(
        "LoginPage.jsx no manda a ningun dominio de emergentagent.com",
        "emergentagent.com" not in login_jsx,
    )
    ok(
        "LoginPage.jsx ya no llama a /api/auth/google/session",
        "auth/google" not in login_jsx,
    )
    ok(
        "LoginPage.jsx ya no pinta el boton de Google",
        "google-login-button" not in login_jsx,
    )
    ok(
        "LoginPage.jsx conserva el enlace a /forgot-password (el rescate)",
        "/forgot-password" in login_jsx,
    )


# ---------------------------------------------------------------------------
def capa_2_el_alta_por_correo_esta_completa():
    print()
    print("=" * 72)
    print("Capa 2 -- el alta por correo: registrarse y jugar sin segundo paso")
    print("=" * 72)

    res = client.post(
        "/api/auth/register",
        json={
            "email": CORREO,
            "password": CONTRASENA,
            "display_name": "Prueba BOS-350",
            "country_code": "MX",
            "favorite_topic": "historia",
            "language": "es",
        },
    )
    ok("registro -> 200", res.status_code == 200, res.text[:200])
    cuerpo = res.json() if res.status_code == 200 else {}
    token = cuerpo.get("token")
    usuario = cuerpo.get("user", {})

    ok("el registro devuelve un JWT (no hace falta un segundo login)", bool(token))
    ok(
        "la cuenta nueva trae 5 partidas gratis",
        usuario.get("games_remaining") == 5,
        repr(usuario.get("games_remaining")),
    )
    ok(
        'auth_provider == "email"',
        usuario.get("auth_provider") == "email",
        repr(usuario.get("auth_provider")),
    )

    # El JWT del registro sirve de inmediato.
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    ok("el JWT del registro entra a /api/auth/me -> 200", res.status_code == 200, str(res.status_code))

    # Y el correo tambien entra por el login normal.
    res = client.post("/api/auth/login", json={"email": CORREO, "password": CONTRASENA})
    ok("login con ese correo -> 200", res.status_code == 200, res.text[:200])

    # Nada de esto emite un cookie de sesion: el unico que lo hacia era Google.
    ok(
        "el registro/login no emite cookie session_token",
        "session_token" not in res.headers.get("set-cookie", ""),
        repr(res.headers.get("set-cookie")),
    )
    ok(
        "user_sessions sigue vacia (ya nada la escribe)",
        server.user_sessions_col.count_documents({}) == 0,
        str(server.user_sessions_col.count_documents({})),
    )


# ---------------------------------------------------------------------------
def capa_3_la_cuenta_vieja_de_google_no_queda_encerrada():
    print()
    print("=" * 72)
    print("Capa 3 -- rescate de una cuenta vieja de Google, de punta a punta")
    print("=" * 72)

    # Una cuenta como las que dejo el flujo de Google: sin campo `password`.
    server.users_col.insert_one(
        {
            "email": CORREO_GOOGLE,
            "display_name": "Cuenta vieja",
            "google_picture": "https://ejemplo.test/foto.png",
            "country_code": "us",
            "favorite_topic": "General Knowledge",
            "language": "es",
            "elo_rating": 500,
            "wins": 3,
            "losses": 1,
            "total_duels": 4,
            "auth_provider": "google",
            "games_remaining": 2,
            "created_at": datetime.now(timezone.utc),
        }
    )

    # 1. Intentar entrar: 400, pero el mensaje ya no la manda a Google.
    res = client.post("/api/auth/login", json={"email": CORREO_GOOGLE, "password": "lo-que-sea"})
    ok("login de cuenta sin contrasena -> 400", res.status_code == 400, str(res.status_code))
    mensaje = str(res.json().get("detail", ""))
    ok(
        "el mensaje la manda a 'Olvide mi contrasena', no a Google",
        "lvide" in mensaje and "contrasena" in mensaje.lower(),
        repr(mensaje),
    )
    ok(
        "el mensaje no le pide iniciar sesion con Google",
        "sign-in" not in mensaje.lower() or "ya no esta disponible" in mensaje.lower(),
        repr(mensaje),
    )

    # 2. Pedir el codigo. Este es el renglon que se quito: antes contestaba
    #    "esta cuenta usa Google Sign-In" y no mandaba nada.
    res = client.post("/api/auth/forgot-password", json={"email": CORREO_GOOGLE})
    ok("forgot-password -> 200", res.status_code == 200, str(res.status_code))
    cuerpo = res.json()
    ok(
        "el mensaje ya no dice 'usa Google Sign-In'",
        "Google" not in str(cuerpo.get("message", "")),
        repr(cuerpo.get("message")),
    )
    # BOS-353: el codigo y el token ya NO viajan en la respuesta. Lo que hay
    # que comprobar aqui es que a una cuenta de Google SI se le genera el
    # rescate, y eso se ve en la base. Que la respuesta siga limpia lo fija
    # `test_recuperacion_de_contrasena.py`.
    reset_doc = server.password_resets_col.find_one({"email": CORREO_GOOGLE, "used": False})
    ok(
        "forgot-password SI crea el rescate de una cuenta de Google",
        reset_doc is not None,
        repr(cuerpo),
    )
    codigo = (reset_doc or {}).get("code")
    ok("el codigo guardado es de 6 digitos", bool(codigo) and len(str(codigo)) == 6, repr(codigo))

    # 3. Verificar el codigo.
    res = client.post(f"/api/auth/verify-reset-code?email={CORREO_GOOGLE}&code={codigo}")
    ok("verify-reset-code -> 200", res.status_code == 200, res.text[:200])
    reset_token = res.json().get("reset_token") if res.status_code == 200 else None
    ok("verify-reset-code devuelve el token", bool(reset_token))

    # 4. Poner la contrasena.
    res = client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": CONTRASENA_NUEVA},
    )
    ok("reset-password -> 200", res.status_code == 200, res.text[:200])

    # 5. Entrar. Esto es lo que la opcion A tenia que no romper.
    res = client.post(
        "/api/auth/login", json={"email": CORREO_GOOGLE, "password": CONTRASENA_NUEVA}
    )
    ok(
        "la cuenta vieja de Google ya entra con correo y contrasena -> 200",
        res.status_code == 200,
        res.text[:200],
    )

    usuario = server.users_col.find_one({"email": CORREO_GOOGLE})
    ok(
        'auth_provider paso de "google" a "email"',
        usuario.get("auth_provider") == "email",
        repr(usuario.get("auth_provider")),
    )
    ok(
        "no se perdio nada de la cuenta (ELO, partidas, historial)",
        usuario.get("elo_rating") == 500
        and usuario.get("games_remaining") == 2
        and usuario.get("total_duels") == 4,
        repr({k: usuario.get(k) for k in ("elo_rating", "games_remaining", "total_duels")}),
    )

    # Y la contrasena vieja (que nunca existio) sigue sin servir.
    res = client.post("/api/auth/login", json={"email": CORREO_GOOGLE, "password": "lo-que-sea"})
    ok("una contrasena equivocada sigue dando 401", res.status_code == 401, str(res.status_code))


# ---------------------------------------------------------------------------
def capa_4_una_sesion_viva_no_se_expulsa():
    print()
    print("=" * 72)
    print("Capa 4 -- un cookie de sesion ya emitido sigue sirviendo (decidido)")
    print("=" * 72)

    # Decision de BOS-350: se quito quien *emite* el cookie, no quien lo
    # acepta. Si alguien quita tambien la aceptacion, esta prueba falla y
    # obliga a comprobar antes que `user_sessions` este vacia en produccion.
    server.users_col.insert_one(
        {
            "user_id": "sesion-viva-bos350",
            "email": "sesion-viva-bos350@kwtest-local.com",
            "display_name": "Sesion viva",
            "elo_rating": 500,
            "auth_provider": "google",
        }
    )
    server.user_sessions_col.insert_one(
        {
            "user_id": "sesion-viva-bos350",
            "session_token": "kw_sesion_viva_bos350",
            "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        }
    )

    res = client.get(
        "/api/auth/me", headers={"Cookie": "session_token=kw_sesion_viva_bos350"}
    )
    ok("cookie de sesion vigente -> 200", res.status_code == 200, str(res.status_code))

    # El logout sigue limpiandolo.
    res = client.post(
        "/api/auth/logout", headers={"Cookie": "session_token=kw_sesion_viva_bos350"}
    )
    ok("logout -> 200", res.status_code == 200, str(res.status_code))
    ok(
        "logout borro la sesion de la base",
        server.user_sessions_col.find_one({"session_token": "kw_sesion_viva_bos350"}) is None,
    )
    res = client.get(
        "/api/auth/me", headers={"Cookie": "session_token=kw_sesion_viva_bos350"}
    )
    ok("despues del logout el cookie ya no entra -> 401", res.status_code == 401, str(res.status_code))


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
    capa_1_no_queda_rastro_de_emergent()
    capa_2_el_alta_por_correo_esta_completa()
    capa_3_la_cuenta_vieja_de_google_no_queda_encerrada()
    capa_4_una_sesion_viva_no_se_expulsa()
    return finish()


if __name__ == "__main__":
    sys.exit(main())
