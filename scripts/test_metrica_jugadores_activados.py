"""
Pruebas de la metrica 3 (jugadores activados) contra una base en memoria.

    pip install mongomock
    python scripts/test_metrica_jugadores_activados.py

Se prueba con mongomock porque la base de produccion todavia no existe: el
cluster anterior de Atlas desaparecio. Cuando exista, el mismo pipeline corre
sin cambios contra Mongo real.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mongomock
from bson import ObjectId

from metrica_jugadores_activados import activated_player_ids, activated_players


def fresh_db():
    return mongomock.MongoClient().knowledge_wars


def add_user(db, name):
    return db.users.insert_one({"display_name": name, "elo_rating": 500}).inserted_id


def add_match(db, a, b, status="finished", winner=None):
    return db.matches.insert_one(
        {
            "player_a_id": a,
            "player_b_id": b,
            "status": status,
            "winner_id": winner or a,
            "elo_delta_a": 2,
            "elo_delta_b": -1,
        }
    ).inserted_id


def test_base_vacia():
    m = activated_players(fresh_db())
    assert m["jugadores_activados"] == 0, m
    assert m["usuarios_registrados"] == 0, m
    assert m["tasa_activacion"] == 0.0, m


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
    """Tres partidas terminadas entre los mismos dos: siguen siendo 2 activados."""
    db = fresh_db()
    a, b = add_user(db, "ana"), add_user(db, "beto")
    for _ in range(3):
        add_match(db, a, b)
    m = activated_players(db)
    assert m["jugadores_activados"] == 2, m
    assert m["partidas_terminadas"] == 3, m


def test_ignora_partidas_no_terminadas():
    db = fresh_db()
    a, b = add_user(db, "ana"), add_user(db, "beto")
    c = add_user(db, "carla")
    add_match(db, a, b, status="finished")
    add_match(db, a, c, status="pending")
    add_match(db, b, c, status="active")
    add_match(db, a, c, status="cancelled")
    m = activated_players(db)
    assert m["jugadores_activados"] == 2, m
    assert m["usuarios_registrados"] == 3, m
    assert m["tasa_activacion"] == 0.6667, m


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
    """Una cuenta borrada deja su id en matches; no debe contarse."""
    db = fresh_db()
    a = add_user(db, "ana")
    fantasma = ObjectId()
    add_match(db, a, fantasma)
    m = activated_players(db)
    assert m["jugadores_activados"] == 1, m
    assert m["ids_huerfanos"] == 1, m


def test_player_id_nulo_se_ignora():
    db = fresh_db()
    a = add_user(db, "ana")
    add_match(db, a, None)
    assert activated_players(db)["jugadores_activados"] == 1


def test_pipeline_devuelve_ids_distintos():
    db = fresh_db()
    a, b = add_user(db, "ana"), add_user(db, "beto")
    add_match(db, a, b)
    add_match(db, b, a)
    assert activated_player_ids(db) == {a, b}


if __name__ == "__main__":
    passed, failed = [], []
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{name}: {type(exc).__name__}: {exc}")
        else:
            passed.append(name)

    for name in passed:
        print("ok   " + name)
    for line in failed:
        print("FAIL " + line)
    print(f"\n{len(passed)} ok, {len(failed)} fallidas")
    sys.exit(1 if failed else 0)
