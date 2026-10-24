"""
Pruebas de la metrica 3 (jugadores activados) contra un MongoDB local real.

    # Windows, con MongoDB Community instalado
    mongod --dbpath C:\\tmp\\kw-metrica --port 27117
    MONGO_TEST_URL=mongodb://127.0.0.1:27117 python scripts/test_metrica_jugadores_activados.py

    # Linux/macOS, contenedor
    docker run --rm -p 27117:27017 mongo:8
    MONGO_TEST_URL=mongodb://127.0.0.1:27117 python scripts/test_metrica_jugadores_activados.py

Se prueba contra Mongo real, no contra mongomock, a proposito: la consulta usa
`$expr` y un arreglo literal con rutas de campo dentro de `$project`, y
mongomock no resuelve ninguno de los dos (devuelve la cadena "$player_a_id"
tal cual). Una prueba que pasa con un doble que no entiende la consulta no
prueba nada. Cada prueba siembra su propia base y la borra al terminar.

La ultima prueba compara el resultado del script contra el pipeline de una sola
consulta documentado en METRICA_3.md: si alguien cambia uno y no el otro, falla.
"""
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from metrica_jugadores_activados import (
    FINISHED_STATUS,
    activated_players,
    finished_filter,
    internal_user_ids,
    jugadores_con_partida_terminada,
)

MONGO_TEST_URL = os.environ.get("MONGO_TEST_URL", "mongodb://127.0.0.1:27017")

_client = None
_bases_creadas = []


def cliente():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_TEST_URL, serverSelectionTimeoutMS=5000)
        _client.admin.command("ping")
    return _client


def fresh_db():
    """Base nueva y vacia para una prueba. Se borra en `limpiar()`."""
    nombre = f"kw_metrica_test_{uuid.uuid4().hex[:12]}"
    _bases_creadas.append(nombre)
    return cliente()[nombre]


def limpiar():
    for nombre in _bases_creadas:
        cliente().drop_database(nombre)


def add_user(db, name, email=None, internal=None, created_at=None):
    doc = {
        "email": email or f"{name}@ejemplo.com",
        "display_name": name,
        "elo_rating": 500,
        "auth_provider": "email",
        "created_at": created_at or datetime(2026, 12, 1, tzinfo=timezone.utc),
        "total_duels": 0,
    }
    if internal is not None:
        doc["is_internal"] = internal
    return db.users.insert_one(doc).inserted_id


def add_match(db, a, b, status=FINISHED_STATUS, ended_at=None, winner=None):
    """Partida con la forma que de verdad escribe el backend."""
    return db.matches.insert_one(
        {
            "player_a_id": a,
            "player_b_id": b,
            "topic": "Historia",
            "language": "es",
            "score_a": 3,
            "score_b": 1,
            "status": status,
            "created_at": datetime(2027, 1, 10, tzinfo=timezone.utc),
            "ended_at": ended_at
            or (datetime(2027, 1, 10, 12, tzinfo=timezone.utc) if status == FINISHED_STATUS else None),
            "winner_id": winner or a,
            "elo_delta_a": 2,
            "elo_delta_b": -1,
        }
    ).inserted_id


# ------------------------------------------------------------------ pruebas


def test_base_vacia():
    m = activated_players(fresh_db())
    assert m["jugadores_activados"] == 0, m
    assert m["usuarios_registrados"] == 0, m
    assert m["tasa_activacion"] == 0.0, m
    assert m["ventana"] == "acumulado", m


def test_registrados_sin_partidas():
    db = fresh_db()
    add_user(db, "ana")
    add_user(db, "beto")
    m = activated_players(db)
    assert m["jugadores_activados"] == 0, m
    assert m["usuarios_registrados"] == 2, m


def test_una_partida_terminada_cuenta_dos():
    db = fresh_db()
    a, b = add_user(db, "ana"), add_user(db, "beto")
    add_match(db, a, b)
    m = activated_players(db)
    assert m["jugadores_activados"] == 2, m
    assert m["partidas_terminadas"] == 1, m
    assert m["tasa_activacion"] == 1.0, m


def test_no_cuenta_dos_veces_al_mismo_jugador():
    """Tres partidas terminadas entre los mismos dos: siguen siendo 2."""
    db = fresh_db()
    a, b = add_user(db, "ana"), add_user(db, "beto")
    for _ in range(3):
        add_match(db, a, b)
    m = activated_players(db)
    assert m["jugadores_activados"] == 2, m
    assert m["partidas_terminadas"] == 3, m


def test_ignora_partidas_no_terminadas():
    """Decision 2: abandonada, cancelada, expirada y rechazada no cuentan."""
    db = fresh_db()
    a, b = add_user(db, "ana"), add_user(db, "beto")
    c = add_user(db, "carla")
    add_match(db, a, b, status=FINISHED_STATUS)
    add_match(db, a, c, status="pending")
    add_match(db, b, c, status="active")  # abandonada a medias
    add_match(db, a, c, status="cancelled")
    add_match(db, c, a, status="expired")
    add_match(db, c, b, status="rejected")
    m = activated_players(db)
    assert m["jugadores_activados"] == 2, m
    assert m["usuarios_registrados"] == 3, m
    assert m["tasa_activacion"] == 0.6667, m


def test_rendicion_si_cuenta():
    """Decision 2: rendirse deja la partida en 'finished'; el jugador jugo."""
    db = fresh_db()
    a, b = add_user(db, "ana"), add_user(db, "beto")
    mid = add_match(db, a, b)
    db.matches.update_one({"_id": mid}, {"$set": {"win_reason": "surrender"}})
    assert activated_players(db)["jugadores_activados"] == 2


def test_parcial():
    db = fresh_db()
    users = [add_user(db, f"u{i}") for i in range(10)]
    add_match(db, users[0], users[1])
    add_match(db, users[2], users[3])
    m = activated_players(db)
    assert m["jugadores_activados"] == 4, m
    assert m["usuarios_registrados"] == 10, m
    assert m["tasa_activacion"] == 0.4, m


def test_id_huerfano_no_infla_la_metrica():
    """Decision 5: una cuenta borrada deja su id en matches; no debe contar."""
    from bson import ObjectId

    db = fresh_db()
    a = add_user(db, "ana")
    add_match(db, a, ObjectId())
    m = activated_players(db)
    assert m["jugadores_activados"] == 1, m
    assert m["ids_huerfanos"] == 1, m


def test_player_id_nulo_se_ignora():
    db = fresh_db()
    a = add_user(db, "ana")
    add_match(db, a, None)
    assert activated_players(db)["jugadores_activados"] == 1


def test_autopartida_no_cuenta():
    """Decision 3: ana contra ana no activa a ana."""
    db = fresh_db()
    a, b = add_user(db, "ana"), add_user(db, "beto")
    add_match(db, a, a)
    m = activated_players(db)
    assert m["jugadores_activados"] == 0, m
    assert m["partidas_terminadas"] == 0, m
    assert m["excluidas_autopartida"] == 1, m
    assert m["usuarios_registrados"] == 2, m


def test_autopartida_cuenta_con_la_bandera():
    db = fresh_db()
    a = add_user(db, "ana")
    add_match(db, a, a)
    m = activated_players(db, incluir_autopartidas=True)
    assert m["jugadores_activados"] == 1, m
    assert m["partidas_terminadas"] == 1, m
    assert m["excluidas_autopartida"] == 0, m


def test_autopartida_no_borra_una_partida_real():
    """Quien jugo contra si mismo Y contra alguien mas, si esta activado."""
    db = fresh_db()
    a, b = add_user(db, "ana"), add_user(db, "beto")
    add_match(db, a, a)
    add_match(db, a, b)
    m = activated_players(db)
    assert m["jugadores_activados"] == 2, m
    assert m["excluidas_autopartida"] == 1, m


def test_cuenta_interna_marcada_no_cuenta():
    """Decision 4: is_internal: true sale del numerador y del denominador."""
    db = fresh_db()
    a = add_user(db, "ana")
    qa = add_user(db, "qa", internal=True)
    add_match(db, a, qa)
    m = activated_players(db)
    assert m["jugadores_activados"] == 1, m
    assert m["excluidos_internos"] == 1, m
    assert m["usuarios_registrados"] == 1, m
    assert m["cuentas_internas"] == 1, m


def test_cuenta_interna_por_correo_y_por_dominio():
    db = fresh_db()
    a = add_user(db, "ana")
    gus = add_user(db, "gus", email="gus@grupoviter.com")
    qa = add_user(db, "qa", email="QA@Interno.Test")
    add_match(db, a, gus)
    add_match(db, a, qa)

    m = activated_players(
        db,
        correos_internos=("qa@interno.test",),
        dominios_internos=("grupoviter.com",),
    )
    assert m["jugadores_activados"] == 1, m
    assert m["excluidos_internos"] == 2, m
    assert m["usuarios_registrados"] == 1, m
    # Sin listas y sin `is_internal` en la base, nadie es interno.
    assert internal_user_ids(db, (), ()) == set()
    # El dominio se acepta con y sin arroba.
    assert internal_user_ids(db, (), ("@grupoviter.com",)) == {gus}
    assert internal_user_ids(db, (), ("grupoviter.com",)) == {gus}


def test_ventana_por_ended_at():
    """Decision 7: --hasta es exclusivo; el corte usa ended_at en UTC."""
    db = fresh_db()
    a, b = add_user(db, "ana"), add_user(db, "beto")
    c, d = add_user(db, "carla"), add_user(db, "dani")
    add_match(db, a, b, ended_at=datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc))
    add_match(db, c, d, ended_at=datetime(2027, 2, 1, 10, 0, tzinfo=timezone.utc))

    q1 = activated_players(
        db,
        desde=datetime(2027, 1, 1, tzinfo=timezone.utc),
        hasta=datetime(2027, 4, 1, tzinfo=timezone.utc),
    )
    assert q1["jugadores_activados"] == 2, q1
    assert q1["partidas_terminadas"] == 1, q1
    assert "ended_at" in q1["ventana"], q1

    acumulado = activated_players(db)
    assert acumulado["jugadores_activados"] == 4, acumulado


def test_escenario_del_corte():
    """
    El ensayo del dia del corte: una base sembrada a mano con de todo, y los
    nueve renglones de la salida verificados uno por uno. Si esta prueba pasa,
    el numero que se reporta el dia del corte es el que esta aqui.

    8 cuentas, de las cuales 1 es interna  -> denominador 7
    Activados: ana, beto, carla, dani      -> 4
      - elena  se registro y no jugo
      - fito   solo tiene una partida en curso
      - gaby   solo jugo contra si misma
      - qa     es interna
    """
    from bson import ObjectId

    db = fresh_db()
    ana, beto = add_user(db, "ana"), add_user(db, "beto")
    carla, dani = add_user(db, "carla"), add_user(db, "dani")
    add_user(db, "elena")                        # registrada, nunca jugo
    fito = add_user(db, "fito")
    gaby = add_user(db, "gaby")
    qa = add_user(db, "qa", internal=True)

    en_q1 = datetime(2027, 2, 14, 18, 30, tzinfo=timezone.utc)
    add_match(db, ana, beto, ended_at=en_q1)
    add_match(db, beto, ana, ended_at=en_q1)     # repetida: no cuenta doble
    add_match(db, carla, dani, ended_at=en_q1)
    add_match(db, gaby, gaby, ended_at=en_q1)    # autopartida
    add_match(db, ana, qa, ended_at=en_q1)       # contra cuenta interna
    add_match(db, ana, ObjectId(), ended_at=en_q1)  # rival con cuenta borrada
    add_match(db, beto, fito, status="active")   # en curso / abandonada
    add_match(db, carla, fito, status="expired")
    add_match(db, dani, fito, status="rejected")

    m = activated_players(
        db,
        desde=datetime(2027, 1, 1, tzinfo=timezone.utc),
        hasta=datetime(2027, 4, 1, tzinfo=timezone.utc),
    )
    assert m["jugadores_activados"] == 4, m
    assert m["usuarios_registrados"] == 7, m
    assert m["tasa_activacion"] == 0.5714, m
    assert m["partidas_terminadas"] == 5, m
    assert m["excluidas_autopartida"] == 1, m
    assert m["excluidos_internos"] == 1, m
    assert m["ids_huerfanos"] == 1, m
    assert m["cuentas_internas"] == 1, m
    assert m["ventana"].startswith("ended_at >="), m

    # Y fuera del trimestre no hay nada: las partidas terminadas son de febrero.
    fuera = activated_players(
        db,
        desde=datetime(2027, 4, 1, tzinfo=timezone.utc),
        hasta=datetime(2027, 7, 1, tzinfo=timezone.utc),
    )
    assert fuera["jugadores_activados"] == 0, fuera
    assert fuera["usuarios_registrados"] == 7, fuera


def test_pipeline_devuelve_ids_distintos():
    db = fresh_db()
    a, b = add_user(db, "ana"), add_user(db, "beto")
    add_match(db, a, b)
    add_match(db, b, a)
    assert jugadores_con_partida_terminada(db, finished_filter()) == {a, b}


def test_equivale_al_pipeline_de_una_sola_consulta():
    """
    El pipeline de METRICA_3.md (el que se pega en mongosh el dia del corte)
    tiene que dar el mismo numero que este script. Si alguien cambia uno y no
    el otro, esta prueba falla.
    """
    db = fresh_db()
    from bson import ObjectId

    a, b = add_user(db, "ana"), add_user(db, "beto")
    c = add_user(db, "carla")
    qa = add_user(db, "qa", internal=True)
    add_match(db, a, b)
    add_match(db, b, c)
    add_match(db, a, a)                      # autopartida
    add_match(db, a, qa)                     # cuenta interna
    add_match(db, a, ObjectId())             # id huerfano
    add_match(db, b, c, status="active")     # abandonada
    add_match(db, a, None)                   # jugador nulo

    pipeline = [
        {"$match": {"status": "finished",
                    "$expr": {"$ne": ["$player_a_id", "$player_b_id"]}}},
        {"$project": {"jugadores": ["$player_a_id", "$player_b_id"]}},
        {"$unwind": "$jugadores"},
        {"$match": {"jugadores": {"$ne": None}}},
        {"$group": {"_id": "$jugadores"}},
        {"$lookup": {"from": "users", "localField": "_id",
                     "foreignField": "_id", "as": "cuenta"}},
        {"$match": {"cuenta.0": {"$exists": True},
                    "cuenta.0.is_internal": {"$ne": True}}},
        {"$count": "jugadores_activados"},
    ]
    del_pipeline = list(db.matches.aggregate(pipeline))
    por_pipeline = del_pipeline[0]["jugadores_activados"] if del_pipeline else 0

    por_script = activated_players(db)["jugadores_activados"]
    assert por_pipeline == por_script == 3, (por_pipeline, por_script)


# ------------------------------------------------------------------- runner

if __name__ == "__main__":
    try:
        cliente()
    except PyMongoError as exc:
        print(f"SIN MONGO LOCAL en {MONGO_TEST_URL}: {type(exc).__name__}: {exc}")
        print("Levanta un mongod local y reintenta (ver el encabezado de este archivo).")
        sys.exit(2)

    print(f"Mongo real en {MONGO_TEST_URL} "
          f"(version {cliente().server_info()['version']})\n")

    passed, failed = [], []
    try:
        for name, fn in sorted(globals().items()):
            if not name.startswith("test_") or not callable(fn):
                continue
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{name}: {type(exc).__name__}: {exc}")
            else:
                passed.append(name)
    finally:
        limpiar()

    for name in passed:
        print("ok   " + name)
    for line in failed:
        print("FAIL " + line)
    print(f"\n{len(passed)} ok, {len(failed)} fallidas")
    sys.exit(1 if failed else 0)
