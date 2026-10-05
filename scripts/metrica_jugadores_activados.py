#!/usr/bin/env python3
"""
Metrica 3 de Knowledge Wars: jugadores activados.

Definicion: usuarios registrados que completaron al menos una partida, es decir,
usuarios distintos que aparecen como player_a_id o player_b_id en algun
documento de `matches` con status "finished".

Uso:

    MONGO_URL="..." DB_NAME="..." python scripts/metrica_jugadores_activados.py

Imprime, para el reporte semanal:

    jugadores_activados   <- la metrica 3
    usuarios_registrados  <- denominador
    tasa_activacion       <- activados / registrados
    partidas_terminadas   <- contexto
    ids_huerfanos         <- ids en matches sin cuenta en users (deberia ser 0)

Equivalente en una sola consulta, para pegar en mongosh:

    db.matches.aggregate([
      { $match: { status: "finished" } },
      { $project: { players: ["$player_a_id", "$player_b_id"] } },
      { $unwind: "$players" },
      { $match: { players: { $ne: null } } },
      { $group:  { _id: "$players" } },
      { $lookup: { from: "users", localField: "_id",
                   foreignField: "_id", as: "cuenta" } },
      { $match:  { "cuenta.0": { $exists: true } } },
      { $count:  "jugadores_activados" }
    ])

Ese pipeline y el codigo de abajo calculan lo mismo. El codigo usa dos
`distinct` en lugar del pipeline a proposito: la version con `$project` y un
array literal no se puede probar con mongomock (no resuelve rutas de campo
dentro de un array, devuelve la cadena "$player_a_id" tal cual), y preferimos
que el camino que de verdad se ejecuta sea el que esta cubierto por pruebas.
Para una base semanal de este tamano los dos viajes a la base no importan.
"""
import os
import sys

# Los dos jugadores de una partida. Si algun dia existe modo torneo con mas
# participantes por documento, se agregan aqui y las pruebas lo cubren solo.
PLAYER_FIELDS = ("player_a_id", "player_b_id")

FINISHED = {"status": "finished"}


def activated_player_ids(db):
    """Ids de jugadores con al menos una partida en status 'finished'."""
    ids = set()
    for field in PLAYER_FIELDS:
        ids.update(db.matches.distinct(field, FINISHED))
    ids.discard(None)
    return ids


def activated_players(db):
    """
    La metrica 3 y su contexto.

    El cruce contra `users` no es decorativo: si una cuenta se borra, su id
    sigue en los documentos de `matches` y contarlo infla la metrica.
    """
    candidate_ids = activated_player_ids(db)

    activated = (
        db.users.count_documents({"_id": {"$in": list(candidate_ids)}})
        if candidate_ids
        else 0
    )
    registered = db.users.count_documents({})

    return {
        "jugadores_activados": activated,
        "usuarios_registrados": registered,
        "tasa_activacion": round(activated / registered, 4) if registered else 0.0,
        "partidas_terminadas": db.matches.count_documents(FINISHED),
        "ids_huerfanos": len(candidate_ids) - activated,
    }


def main():
    from pymongo import MongoClient

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        sys.exit("Faltan MONGO_URL y/o DB_NAME en el entorno.")

    client = MongoClient(mongo_url, serverSelectionTimeoutMS=10000)
    metrics = activated_players(client[db_name])

    width = max(len(key) for key in metrics)
    for key, value in metrics.items():
        print(f"{key.ljust(width)}  {value}")


if __name__ == "__main__":
    main()
