#!/usr/bin/env python3
"""
Metrica 3 de Knowledge Wars: jugadores activados.

    Usuarios registrados que completaron al menos una partida.
    Registrarse sin jugar no cuenta.

Las decisiones de definicion (que cuenta como partida terminada, que pasa con
una partida abandonada, con una autopartida y con las cuentas internas) estan
escritas en `scripts/METRICA_3.md`, al lado de este archivo. Lee ese documento
antes de discutir el numero: aqui solo esta la implementacion.

Uso:

    MONGO_URL="mongodb+srv://..." DB_NAME="knowledge_wars" \
        python scripts/metrica_jugadores_activados.py

    # acotado a un trimestre, por fecha de fin de partida (UTC)
    ... python scripts/metrica_jugadores_activados.py --desde 2027-01-01 --hasta 2027-04-01

    # cuentas internas que no deben contar (ademas de las marcadas is_internal)
    METRICA_EXCLUIR_CORREOS="gus@grupoviter.com,qa@grupoviter.com" \
    METRICA_EXCLUIR_DOMINIOS="grupoviter.com" ... python scripts/...

Imprime:

    jugadores_activados      <- LA METRICA 3
    usuarios_registrados     <- denominador (sin cuentas internas)
    tasa_activacion          <- activados / registrados
    partidas_terminadas      <- partidas que entraron al conteo
    excluidas_autopartida    <- partidas terminadas de alguien contra si mismo
    excluidos_internos       <- cuentas internas que si no, habrian contado
    ids_huerfanos            <- ids en matches sin cuenta en users
    cuentas_internas         <- cuentas marcadas como internas
    ventana                  <- rango aplicado sobre ended_at, o "acumulado"

Colecciones y campos usados (verificados contra backend/server.py, no supuestos):

    users._id                  ObjectId
    users.email                str
    users.is_internal          bool, opcional; no lo escribe el backend todavia
    matches.status             "pending"|"active"|"finished"|"expired"
                               |"cancelled"|"rejected"
    matches.player_a_id        ObjectId
    matches.player_b_id        ObjectId
    matches.ended_at           datetime UTC
"""
import argparse
import os
import re
import sys
from datetime import datetime, timezone

# Los dos jugadores de una partida. Si algun dia hay modo torneo con mas
# participantes por documento, se agregan aqui y el resto sigue igual.
PLAYER_FIELDS = ("player_a_id", "player_b_id")

# Unico marcador de partida terminada. Lo escriben exactamente dos lugares del
# backend: `finish_match()` y `surrender_match()`. Ver METRICA_3.md, decision 1.
FINISHED_STATUS = "finished"

# Campo opcional en `users` para marcar cuentas del equipo. Ver decision 4.
INTERNAL_FLAG = "is_internal"


# ---------------------------------------------------------------- utilidades


def _parse_fecha(texto, nombre):
    """YYYY-MM-DD o ISO 8601 -> datetime con tz UTC."""
    if texto is None:
        return None
    try:
        fecha = datetime.fromisoformat(texto)
    except ValueError:
        raise SystemExit(f"--{nombre} debe ser YYYY-MM-DD o ISO 8601, no {texto!r}")
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)


def _lista_env(nombre):
    return tuple(
        pieza.strip().lower()
        for pieza in os.environ.get(nombre, "").split(",")
        if pieza.strip()
    )


def finished_filter(desde=None, hasta=None, incluir_autopartidas=False):
    """Filtro de partidas que cuentan. `hasta` es exclusivo."""
    filtro = {"status": FINISHED_STATUS}

    rango = {}
    if desde is not None:
        rango["$gte"] = desde
    if hasta is not None:
        rango["$lt"] = hasta
    if rango:
        filtro["ended_at"] = rango

    if not incluir_autopartidas:
        # Comparacion campo-contra-campo: no se puede expresar sin $expr.
        filtro["$expr"] = {"$ne": ["$player_a_id", "$player_b_id"]}

    return filtro


# ------------------------------------------------------------------ consulta


def internal_user_ids(db, correos=(), dominios=()):
    """
    Ids de cuentas internas: marcadas con `is_internal: true`, o cuyo correo
    esta en `correos`, o cuyo dominio esta en `dominios`.
    """
    condiciones = [{INTERNAL_FLAG: True}]

    if correos:
        # Insensible a mayusculas a proposito: el backend guarda el correo tal
        # como lo escribio quien se registro (`register()` no lo normaliza), asi
        # que quien escribe la lista de exclusion no puede adivinar si quedo
        # "QA@x.com" o "qa@x.com". Ver METRICA_3.md, decision 4.
        exactos = "|".join(re.escape(c.strip().lower()) for c in correos)
        condiciones.append({"email": {"$regex": f"^({exactos})$", "$options": "i"}})
    if dominios:
        sufijos = "|".join(re.escape(d.lower().lstrip("@")) for d in dominios)
        condiciones.append({"email": {"$regex": f"@({sufijos})$", "$options": "i"}})

    return {doc["_id"] for doc in db.users.find({"$or": condiciones}, {"_id": 1})}


def jugadores_con_partida_terminada(db, filtro):
    """
    Ids distintos que aparecen como jugador en alguna partida de `filtro`.

    Son *candidatos*: pueden no tener cuenta viva en `users` (id huerfano) o
    ser una cuenta interna. Eso se resuelve en `activated_players`.
    """
    pipeline = [
        {"$match": filtro},
        {"$project": {"jugadores": [f"${campo}" for campo in PLAYER_FIELDS]}},
        {"$unwind": "$jugadores"},
        {"$match": {"jugadores": {"$ne": None}}},
        {"$group": {"_id": "$jugadores"}},
    ]
    return {doc["_id"] for doc in db.matches.aggregate(pipeline)}


def activated_players(
    db,
    desde=None,
    hasta=None,
    incluir_autopartidas=False,
    correos_internos=(),
    dominios_internos=(),
):
    """La metrica 3 y los numeros que hacen falta para defenderla."""
    filtro = finished_filter(desde, hasta, incluir_autopartidas)
    candidatos = jugadores_con_partida_terminada(db, filtro)

    internos = internal_user_ids(db, correos_internos, dominios_internos)

    # El cruce contra `users` no es decorativo: si una cuenta se borra, su id
    # sigue en los documentos de `matches` y contarlo infla la metrica.
    con_cuenta = (
        {
            doc["_id"]
            for doc in db.users.find({"_id": {"$in": list(candidatos)}}, {"_id": 1})
        }
        if candidatos
        else set()
    )

    activados = con_cuenta - internos
    registrados = db.users.count_documents(
        {"_id": {"$nin": list(internos)}} if internos else {}
    )

    filtro_auto = dict(finished_filter(desde, hasta, incluir_autopartidas=True))
    filtro_auto["$expr"] = {"$eq": ["$player_a_id", "$player_b_id"]}

    if desde or hasta:
        ventana = f"ended_at >= {desde or '-inf'} y < {hasta or '+inf'}"
    else:
        ventana = "acumulado"

    return {
        "jugadores_activados": len(activados),
        "usuarios_registrados": registrados,
        "tasa_activacion": round(len(activados) / registrados, 4) if registrados else 0.0,
        "partidas_terminadas": db.matches.count_documents(filtro),
        "excluidas_autopartida": (
            0 if incluir_autopartidas else db.matches.count_documents(filtro_auto)
        ),
        "excluidos_internos": len(con_cuenta & internos),
        "ids_huerfanos": len(candidatos - con_cuenta),
        "cuentas_internas": len(internos),
        "ventana": ventana,
    }


# --------------------------------------------------------------------- main


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Metrica 3 de Knowledge Wars: jugadores activados."
    )
    parser.add_argument("--desde", help="inicio del rango, inclusivo (ended_at, UTC)")
    parser.add_argument("--hasta", help="fin del rango, EXCLUSIVO (ended_at, UTC)")
    parser.add_argument(
        "--incluir-autopartidas",
        action="store_true",
        help="cuenta tambien las partidas de un jugador contra si mismo",
    )
    args = parser.parse_args(argv)

    from pymongo import MongoClient

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        sys.exit("Faltan MONGO_URL y/o DB_NAME en el entorno.")

    client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
    metrics = activated_players(
        client[db_name],
        desde=_parse_fecha(args.desde, "desde"),
        hasta=_parse_fecha(args.hasta, "hasta"),
        incluir_autopartidas=args.incluir_autopartidas,
        correos_internos=_lista_env("METRICA_EXCLUIR_CORREOS"),
        dominios_internos=_lista_env("METRICA_EXCLUIR_DOMINIOS"),
    )

    width = max(len(key) for key in metrics)
    for key, value in metrics.items():
        print(f"{key.ljust(width)}  {value}")


if __name__ == "__main__":
    main()
