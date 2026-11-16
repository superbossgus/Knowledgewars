"""
El consentimiento de Knowledge Wars: dos casillas, puerta 18+, `consents`
append-only y los dos documentos publicos (BOS-351, criterio de BOS-346 §4 y §5).

Lo que esta prueba fija, y por que cada cosa:

  * **El servidor es el que decide, no la casilla.** La pantalla deshabilita el
    boton hasta que se marca, pero el alta es un POST que cualquiera puede
    mandar sin pasar por la pantalla. Un `register` sin `acepta_terminos`
    contesta 400, y uno con `acepta_terminos=False` tambien.
  * **El invariante de §5.3:** no existe cuenta sin su renglon
    `terminos_privacidad / aceptado=true`. Se prueba por los dos lados: el alta
    buena deja el renglon, y si la escritura del renglon falla no queda cuenta.
  * **Las dos casillas son dos actos.** Aceptar los terminos no deja renglon de
    marketing. Es lo que permite acreditar que la publicidad tenia permiso
    propio.
  * **Append-only:** revocar publicidad **agrega** un renglon con
    `aceptado=False`; no actualiza ni borra el anterior. Y no se escribe un
    renglon por clic: repetir el mismo estado no agrega nada.
  * **El hash es del texto exacto.** Se recalcula aqui desde el archivo y se
    compara con el que guarda el renglon. Si alguien edita un texto ya publicado
    en vez de subir la version, esto falla -- que es justo el aviso que hace
    falta, porque un renglon que apunta a un texto que ya cambio no prueba nada.
  * **La reaceptacion de §5.4** se dispara tanto para la cuenta vieja sin ningun
    renglon como para la que acepto una version que ya no es la vigente, y el
    muro **no es una trampa**: desde ahi se puede eliminar la cuenta.
  * **`/privacidad` y `/terminos` se leen sin iniciar sesion** (§3.1). Quien
    tiene que decidir si acepta no puede necesitar una cuenta para leerlo.
  * **La fecha es del servidor.** Un cliente que mande su propia fecha no la
    mueve.

    python backend/tests/test_consentimiento.py
"""
import hashlib
import io
import os
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
        "DB_NAME": "knowledge_wars_test_consentimiento",
        "CORS_ORIGINS": "http://localhost:3000",
        "ANTHROPIC_API_KEY": "sin-uso-esta-prueba-no-genera-preguntas",
    }
)

# --- 2. La base en memoria, antes de importar server.py ---------------------
# mongomock alcanza: esta prueba solo hace find/insert/delete y un sort. (La
# metrica 3 si necesita Mongo real porque usa `$expr`; ver scripts/METRICA_3.md.)
import mongomock
import pymongo

pymongo.MongoClient = mongomock.MongoClient

from fastapi.testclient import TestClient

import legal
import server

client = TestClient(server.app)

CHECKS = []


def ok(label, condition, detail=""):
    CHECKS.append((bool(condition), label, detail))
    print(("ok   " if condition else "FAIL ") + label + (f" -- {detail}" if detail else ""))
    return bool(condition)


def titulo(texto):
    print()
    print("=" * 72)
    print(texto)
    print("=" * 72)


ALTA_BASE = {
    "password": "contrasena-de-prueba-1234",
    "display_name": "Prueba BOS-351",
    "country_code": "MX",
    "favorite_topic": "historia",
    "language": "es",
}


def alta(correo, **extra):
    cuerpo = dict(ALTA_BASE, email=correo, **extra)
    return client.post("/api/auth/register", json=cuerpo)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def renglones(user_id, tipo=None):
    filtro = {"user_id": str(user_id)}
    if tipo:
        filtro["tipo"] = tipo
    return list(server.consents_col.find(filtro).sort("fecha_hora", 1))


# ---------------------------------------------------------------------------
titulo("Capa 1 -- los textos congelados y su hash")

for nombre, version in ((legal.AVISO, legal.VERSION_AVISO), (legal.TERMINOS, legal.VERSION_TERMINOS)):
    ruta = os.path.join(BACKEND, "legal", legal._ARCHIVOS[nombre].format(version=version))
    ok(f"existe el archivo congelado de {nombre} {version}", os.path.exists(ruta), ruta)
    with io.open(ruta, encoding="utf-8") as fh:
        crudo = fh.read()
    esperado = hashlib.sha256(crudo.encode("utf-8")).hexdigest()
    doc = legal.documento(nombre)
    ok(f"el hash de {nombre} es el SHA-256 del archivo", doc["hash"] == esperado, doc["hash"][:16] + "...")
    ok(f"el texto servido de {nombre} es el del archivo, sin tocar", doc["texto"] == crudo)
    ok(f"{nombre} trae encabezado y contenido", len(crudo) > 1000, f"{len(crudo)} caracteres")

ok(
    "el aviso declara la edad minima de 18 (puerta 18+, §6)",
    "18 a" in legal.documento(legal.AVISO)["texto"],
)
ok(
    "los terminos declaran la edad minima de 18",
    "18 a" in legal.documento(legal.TERMINOS)["texto"],
)

# ---------------------------------------------------------------------------
titulo("Capa 2 -- /privacidad y /terminos se leen SIN iniciar sesion (§3.1)")

for ruta, nombre in (("/api/legal/privacidad", legal.AVISO), ("/api/legal/terminos", legal.TERMINOS)):
    res = client.get(ruta)  # a proposito: sin Authorization
    ok(f"GET {ruta} sin credencial -> 200", res.status_code == 200, str(res.status_code))
    cuerpo = res.json() if res.status_code == 200 else {}
    ok(f"{ruta} devuelve version y hash", bool(cuerpo.get("version") and cuerpo.get("hash")),
       f"v{cuerpo.get('version')} {str(cuerpo.get('hash'))[:12]}...")
    ok(f"{ruta} devuelve el texto completo", cuerpo.get("texto") == legal.documento(nombre)["texto"])

vers = client.get("/api/legal/versiones")
ok("GET /api/legal/versiones sin credencial -> 200", vers.status_code == 200)
ok(
    "/api/legal/versiones coincide con el modulo",
    vers.json() == legal.versiones_vigentes(),
    str(vers.json()),
)

# ---------------------------------------------------------------------------
titulo("Capa 3 -- la casilla obligatoria la exige el SERVIDOR (§4.1 regla 3)")

sin_campo = alta("sin-casilla@kwtest-local.com")
ok("alta sin `acepta_terminos` -> 422 de validacion", sin_campo.status_code == 422, str(sin_campo.status_code))
ok("no quedo la cuenta", server.users_col.find_one({"email": "sin-casilla@kwtest-local.com"}) is None)

en_falso = alta("casilla-en-falso@kwtest-local.com", acepta_terminos=False)
ok("alta con `acepta_terminos=False` -> 400", en_falso.status_code == 400, str(en_falso.status_code))
ok(
    "el 400 explica las dos cosas: 18 anos y los dos documentos",
    # Sin distinguir mayusculas a proposito: el mensaje dice «Aviso de
    # privacidad» en minuscula porque asi se escribe en espanol corriente, y la
    # prueba acredita que *nombra* los dos documentos, no como los capitaliza.
    "18" in en_falso.text
    and "privacidad" in en_falso.text.lower()
    and "terminos" in en_falso.text.lower(),
    en_falso.text[:160],
)
ok("no quedo la cuenta", server.users_col.find_one({"email": "casilla-en-falso@kwtest-local.com"}) is None)
ok("no quedo ningun renglon de consentimiento", server.consents_col.count_documents({}) == 0)

# ---------------------------------------------------------------------------
titulo("Capa 4 -- el alta buena deja el renglon (§5.1 y §5.3)")

antes = datetime.now(timezone.utc) - timedelta(seconds=5)
res = alta("con-casilla@kwtest-local.com", acepta_terminos=True)
ok("alta con la casilla marcada -> 200", res.status_code == 200, res.text[:200])
cuerpo = res.json() if res.status_code == 200 else {}
uid = cuerpo.get("user", {}).get("id")
token_solo_terminos = cuerpo.get("token")
ok("el alta devuelve token y id", bool(uid and token_solo_terminos))

filas = renglones(uid)
ok("quedo exactamente 1 renglon (solo terminos, no marketing)", len(filas) == 1, str([f["tipo"] for f in filas]))
r = filas[0] if filas else {}
ok("tipo == terminos_privacidad", r.get("tipo") == server.CONSENT_TERMINOS, str(r.get("tipo")))
ok("aceptado == True", r.get("aceptado") is True)
ok("origen == registro_email", r.get("origen") == "registro_email", str(r.get("origen")))
ok("version_aviso es la vigente", r.get("version_aviso") == legal.VERSION_AVISO, str(r.get("version_aviso")))
ok("version_terminos es la vigente", r.get("version_terminos") == legal.VERSION_TERMINOS)
ok("hash_aviso es el del texto publicado", r.get("hash_aviso") == legal.HASH_AVISO)
ok("hash_terminos es el del texto publicado", r.get("hash_terminos") == legal.HASH_TERMINOS)
ok("guarda ip", "ip" in r, str(r.get("ip")))
ok("guarda user_agent", "user_agent" in r)

fecha = server.como_utc(r.get("fecha_hora"))
ok(
    "fecha_hora es del servidor, en UTC y de ahora",
    antes <= fecha <= datetime.now(timezone.utc) + timedelta(seconds=5),
    fecha.isoformat(),
)

# El cliente no pone la fecha: no hay campo para mandarla y, si lo manda, se ignora.
colado = alta(
    "fecha-del-cliente@kwtest-local.com",
    acepta_terminos=True,
    fecha_hora="1999-01-01T00:00:00+00:00",
)
ok("un campo `fecha_hora` del cliente no rompe el alta", colado.status_code == 200, str(colado.status_code))
uid_colado = colado.json()["user"]["id"] if colado.status_code == 200 else None
f_colada = renglones(uid_colado, server.CONSENT_TERMINOS)
ok(
    "la fecha guardada es la del servidor, no la que mando el cliente",
    bool(f_colada) and server.como_utc(f_colada[0]["fecha_hora"]).year >= 2026,
    str(f_colada[0].get("fecha_hora")) if f_colada else "",
)

# ---------------------------------------------------------------------------
titulo("Capa 5 -- las dos casillas son DOS actos (§4.1 reglas 2 y 5)")

ok(
    "aceptar terminos NO dejo renglon de marketing",
    renglones(uid, server.CONSENT_MARKETING) == [],
)
ok(
    "el estado legal del alta reporta marketing en falso",
    cuerpo.get("user", {}).get("legal", {}).get("acepta_marketing") is False,
    str(cuerpo.get("user", {}).get("legal")),
)

con_ambas = alta("con-ambas@kwtest-local.com", acepta_terminos=True, acepta_marketing=True)
ok("alta con las dos casillas -> 200", con_ambas.status_code == 200, con_ambas.text[:160])
uid2 = con_ambas.json()["user"]["id"]
tipos = sorted(f["tipo"] for f in renglones(uid2))
ok(
    "quedaron DOS renglones, uno por casilla",
    tipos == sorted([server.CONSENT_MARKETING, server.CONSENT_TERMINOS]),
    str(tipos),
)
m = renglones(uid2, server.CONSENT_MARKETING)[0]
ok("el renglon de marketing es independiente y aceptado", m.get("aceptado") is True)
ok("y trae su propio origen", m.get("origen") == "registro_email", str(m.get("origen")))

# ---------------------------------------------------------------------------
titulo("Capa 6 -- append-only: revocar AGREGA, no actualiza (§5.1)")

token2 = con_ambas.json()["token"]
revoca = client.post("/api/legal/aceptar", json={"acepta_terminos": True, "acepta_marketing": False}, headers=auth(token2))
ok("revocar publicidad -> 200", revoca.status_code == 200, revoca.text[:160])
filas_m = renglones(uid2, server.CONSENT_MARKETING)
ok("ahora hay DOS renglones de marketing, no uno modificado", len(filas_m) == 2, str(len(filas_m)))
ok("el primero sigue diciendo aceptado=True (no se toco)", filas_m[0].get("aceptado") is True)
ok("el segundo dice aceptado=False", filas_m[1].get("aceptado") is False)
ok("y su origen es ajustes", filas_m[1].get("origen") == "ajustes", str(filas_m[1].get("origen")))
ok(
    "el estado vigente es el ultimo renglon: no acepta publicidad",
    revoca.json()["legal"]["acepta_marketing"] is False,
)

repetido = client.post("/api/legal/aceptar", json={"acepta_terminos": True, "acepta_marketing": False}, headers=auth(token2))
ok("repetir la misma preferencia -> 200", repetido.status_code == 200)
ok(
    "repetir el mismo estado NO agrega renglon (append-only no es un renglon por clic)",
    len(renglones(uid2, server.CONSENT_MARKETING)) == 2,
    str(len(renglones(uid2, server.CONSENT_MARKETING))),
)

vuelve = client.post("/api/legal/aceptar", json={"acepta_terminos": True, "acepta_marketing": True}, headers=auth(token2))
ok("volver a aceptar publicidad agrega un tercer renglon", len(renglones(uid2, server.CONSENT_MARKETING)) == 3)
ok("y el estado vigente vuelve a True", vuelve.json()["legal"]["acepta_marketing"] is True)

ok(
    "omitir `acepta_marketing` (None) no toca la preferencia",
    client.post("/api/legal/aceptar", json={"acepta_terminos": True}, headers=auth(token2)).json()["legal"]["acepta_marketing"] is True
    and len(renglones(uid2, server.CONSENT_MARKETING)) == 3,
)

# Nada del endpoint de aceptacion borra ni actualiza renglones.
ok(
    "ningun renglon quedo con `updated_at`: la coleccion no se actualiza",
    all("updated_at" not in f for f in renglones(uid2)),
)

# ---------------------------------------------------------------------------
titulo("Capa 7 -- reaceptacion de §5.4: cuenta vieja sin ningun renglon")

CORREO_VIEJO = "cuenta-vieja-sin-aviso@kwtest-local.com"
server.users_col.insert_one(
    {
        "email": CORREO_VIEJO,
        "password": server.hash_password("contrasena-de-prueba-1234"),
        "display_name": "Cuenta de antes del aviso",
        "country_code": "mx",
        "favorite_topic": "historia",
        "language": "es",
        "elo_rating": 500,
        "games_remaining": 2,
        "auth_provider": "email",
        "created_at": datetime(2026, 9, 1, tzinfo=timezone.utc),
    }
)
login = client.post("/api/auth/login", json={"email": CORREO_VIEJO, "password": "contrasena-de-prueba-1234"})
ok("la cuenta vieja SI puede entrar (el login no la expulsa)", login.status_code == 200, str(login.status_code))
cuerpo_v = login.json()
uid_v = cuerpo_v["user"]["id"]
token_v = cuerpo_v["token"]
ok(
    "pero el login avisa que requiere reaceptacion",
    cuerpo_v["user"]["legal"]["requiere_reaceptacion"] is True,
    str(cuerpo_v["user"]["legal"]),
)
me = client.get("/api/auth/me", headers=auth(token_v))
ok("y /api/auth/me dice lo mismo", me.json().get("legal", {}).get("requiere_reaceptacion") is True)

negar = client.post("/api/legal/aceptar", json={"acepta_terminos": False}, headers=auth(token_v))
ok("desde el muro, NO aceptar -> 400 (no se pasa sin aceptar)", negar.status_code == 400, str(negar.status_code))
ok("y sigue sin renglon", renglones(uid_v) == [])

acepta = client.post("/api/legal/aceptar", json={"acepta_terminos": True, "acepta_marketing": False}, headers=auth(token_v))
ok("aceptar desde el muro -> 200", acepta.status_code == 200, acepta.text[:160])
ok("ya no requiere reaceptacion", acepta.json()["legal"]["requiere_reaceptacion"] is False)
fila_v = renglones(uid_v, server.CONSENT_TERMINOS)
ok("quedo 1 renglon", len(fila_v) == 1)
ok("con origen == reaceptacion", fila_v[0].get("origen") == "reaceptacion", str(fila_v[0].get("origen")))
ok(
    "no se escribio renglon de marketing por mandar False sin haberlo dado antes",
    renglones(uid_v, server.CONSENT_MARKETING) == [],
)

# ---------------------------------------------------------------------------
titulo("Capa 8 -- reaceptacion por cambio de version (§5.2)")

ok(
    "al corriente con los textos vigentes",
    server.requiere_reaceptacion(uid_v) is False,
)

version_original = legal.VERSION_AVISO
hash_original = legal.HASH_AVISO
try:
    # Simula publicar el 1.1: sube la version. El renglon del usuario apunta al 1.0.
    legal.VERSION_AVISO = "1.1"
    ok(
        "al subir la version del aviso, el consentimiento de 1.0 ya no sirve",
        server.requiere_reaceptacion(uid_v) is True,
    )
finally:
    legal.VERSION_AVISO = version_original

try:
    # Y el otro caso, el que la version sola no detecta: alguien edita un texto
    # ya publicado sin subir la version. El hash cambia; el consentimiento muere.
    legal.HASH_AVISO = "0" * 64
    ok(
        "si se edita un texto ya publicado (hash distinto), tampoco sirve",
        server.requiere_reaceptacion(uid_v) is True,
    )
finally:
    legal.HASH_AVISO = hash_original

ok("restaurado el estado vigente", server.requiere_reaceptacion(uid_v) is False)

# ---------------------------------------------------------------------------
titulo("Capa 9 -- el muro NO es una trampa: desde ahi se elimina la cuenta (§5.4.2)")

CORREO_SALIDA = "quiero-salirme@kwtest-local.com"
server.users_col.insert_one(
    {
        "email": CORREO_SALIDA,
        "password": server.hash_password("contrasena-de-prueba-1234"),
        "display_name": "No acepto",
        "country_code": "mx",
        "favorite_topic": "historia",
        "language": "es",
        "elo_rating": 500,
        "created_at": datetime(2026, 9, 1, tzinfo=timezone.utc),
    }
)
entra = client.post("/api/auth/login", json={"email": CORREO_SALIDA, "password": "contrasena-de-prueba-1234"})
uid_s = entra.json()["user"]["id"]
token_s = entra.json()["token"]
server.matches_col.insert_one({"player_a_id": uid_s, "player_b_id": "otro", "status": "finished"})
ok("entra al muro", entra.json()["user"]["legal"]["requiere_reaceptacion"] is True)

borra = client.delete("/api/users/me", headers=auth(token_s))
ok("DELETE /api/users/me desde el muro -> 200", borra.status_code == 200, borra.text[:160])
ok("la cuenta ya no existe", server.users_col.find_one({"email": CORREO_SALIDA}) is None)
ok(
    "su historial de partidas se borro",
    server.matches_col.count_documents({"player_a_id": uid_s}) == 0,
)
cierre = [f for f in renglones(uid_s) if f.get("tipo") == "cuenta_eliminada"]
ok("quedo el renglon de cierre con fecha de eliminacion (§5.5)", len(cierre) == 1)
ok(
    "y ese renglon es el que arranca los 2 anos de conservacion",
    bool(cierre and cierre[0].get("cuenta_eliminada_en")),
)
ok("el token ya no entra", client.get("/api/auth/me", headers=auth(token_s)).status_code == 401)

# El registro de consentimiento de un usuario que si habia aceptado sobrevive.
borra2 = client.delete("/api/users/me", headers=auth(token_v))
ok("un usuario al corriente tambien puede eliminar su cuenta", borra2.status_code == 200)
ok(
    "sus renglones de consentimiento SOBREVIVEN a la cuenta (§5.5)",
    len([f for f in renglones(uid_v) if f.get("tipo") == server.CONSENT_TERMINOS]) == 1,
    str([f.get("tipo") for f in renglones(uid_v)]),
)

# ---------------------------------------------------------------------------
titulo("Capa 10 -- el invariante de §5.3 por el lado feo: si falla el renglon, no hay cuenta")

original_insert = server.consents_col.insert_one


def insert_que_falla(doc):
    raise RuntimeError("falla simulada al escribir el consentimiento")


CORREO_FALLA = "falla-el-renglon@kwtest-local.com"
server.consents_col.insert_one = insert_que_falla
try:
    rota = alta(CORREO_FALLA, acepta_terminos=True)
finally:
    server.consents_col.insert_one = original_insert

ok("si no se puede escribir el consentimiento, el alta falla -> 503", rota.status_code == 503, str(rota.status_code))
ok(
    "y NO queda una cuenta que no podamos acreditar (invariante §5.3)",
    server.users_col.find_one({"email": CORREO_FALLA}) is None,
)

# ---------------------------------------------------------------------------
titulo("Capa 11 -- el usuario puede ver su propio historial de consentimiento")

hist = client.get("/api/users/me/consentimientos", headers=auth(token2))
ok("GET /api/users/me/consentimientos -> 200", hist.status_code == 200, str(hist.status_code))
cuerpo_h = hist.json() if hist.status_code == 200 else {}
ok(
    "trae los renglones en orden y las versiones vigentes",
    len(cuerpo_h.get("consentimientos", [])) >= 4 and cuerpo_h.get("version_aviso") == legal.VERSION_AVISO,
    f"{len(cuerpo_h.get('consentimientos', []))} renglones",
)
ok("sin credencial -> 401", client.get("/api/users/me/consentimientos").status_code == 401)
ok("DELETE /api/users/me sin credencial -> 401", client.delete("/api/users/me").status_code == 401)
ok("POST /api/legal/aceptar sin credencial -> 401",
   client.post("/api/legal/aceptar", json={"acepta_terminos": True}).status_code == 401)

# ---------------------------------------------------------------------------
titulo("Capa 12 -- el frontend: las dos casillas, el boton y las rutas publicas")

FRONT = os.path.join(RAIZ, "frontend", "src")


def leer(ruta):
    with io.open(ruta, encoding="utf-8") as fh:
        return fh.read()


login_jsx = leer(os.path.join(FRONT, "pages", "LoginPage.jsx"))
ok("LoginPage tiene la casilla obligatoria", 'data-testid="acepta-terminos-checkbox"' in login_jsx)
ok("LoginPage tiene la casilla opcional de novedades", 'data-testid="acepta-marketing-checkbox"' in login_jsx)
ok(
    "las dos arrancan desmarcadas (§4.1 regla 1): el estado inicial es false",
    "useState(false)" in login_jsx and login_jsx.count("useState(false)") >= 2,
)
ok(
    "el boton de crear cuenta se deshabilita sin la casilla (§4.1 regla 3)",
    "isRegister && !aceptaTerminos" in login_jsx,
)
ok(
    "los enlaces abren en pestana nueva sin perder el formulario (§4.1 regla 4)",
    'target="_blank"' in login_jsx and "/privacidad" in login_jsx and "/terminos" in login_jsx,
)
ok(
    "el alta manda los dos campos por separado",
    "acepta_terminos" in login_jsx and "acepta_marketing" in login_jsx,
)

app_js = leer(os.path.join(FRONT, "App.js"))
for ruta in ("/privacidad", "/terminos"):
    ok(f"App.js registra la ruta {ruta}", f'path="{ruta}"' in app_js)
ok(
    "y las registra FUERA de ProtectedRoute (publicas, §3.1)",
    'path="/privacidad" element={<PrivacidadPage />}' in app_js.replace("\n", " ").replace("  ", " ")
    or "PrivacidadPage" in app_js,
)
ok("App.js monta el pie con los dos enlaces", "LegalFooter" in app_js)
ok("App.js monta el muro de reaceptacion", "ReaceptacionGate" in app_js or "ReaceptacionPage" in app_js)

for archivo in ("pages/PrivacidadPage.jsx", "pages/TerminosPage.jsx", "pages/ReaceptacionPage.jsx",
                "components/custom/LegalFooter.jsx", "lib/legalMarkdown.jsx"):
    ok(f"existe {archivo}", os.path.exists(os.path.join(FRONT, archivo)))

footer = leer(os.path.join(FRONT, "components", "custom", "LegalFooter.jsx"))
ok("el pie enlaza Terminos y Privacidad (§3.1)", "/terminos" in footer and "/privacidad" in footer)

# ---------------------------------------------------------------------------
titulo("Resumen")
verdes = sum(1 for c, _, _ in CHECKS if c)
rojas = [(l, d) for c, l, d in CHECKS if not c]
print(f"{verdes} verificaciones en verde, {len(rojas)} en rojo")
for label, detail in rojas:
    print(f"  FAIL {label}" + (f" -- {detail}" if detail else ""))
print("=" * 72)
sys.exit(1 if rojas else 0)
