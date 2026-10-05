"""
Partida PvP de punta a punta, local y sin infraestructura (BOS-162).

Esto es lo que BOS-125 no pudo correr porque no habia contra que correrlo: el
backend desplegado no responde y el cluster de Atlas ya no existe. Aqui la base
es mongomock (en memoria) y la API de Anthropic es un doble, asi que la prueba
corre sin MongoDB, sin Render, sin API key y sin gastar un peso.

Lo que SI se ejercita de verdad:

  * El codigo real de `server.py`, `utils.py` y `models.py`.
  * El parseo y la validacion reales de `QuestionGenerator.generate_questions`.
    El doble de Anthropic devuelve un objeto `Message` autentico del SDK, con un
    bloque de pensamiento primero y el JSON envuelto en un fence de markdown, que
    es exactamente lo que rompia el codigo anterior.
  * Registro de dos jugadores, creacion de la partida, aceptacion, las dos
    conexiones websocket, las 10 preguntas, y `finish_match` persistiendo
    `status: "finished"` con `winner_id` y los dos `elo_delta`.
  * La consulta de la metrica 3 contra la base que dejo la partida.

Lo que NO se ejercita: la llamada HTTP real a Anthropic, Render, Atlas, y el
frontend. Eso solo se puede verificar contra produccion desplegada.

    python backend/tests/test_e2e_match_local.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "scripts",
    ),
)

# --- 1. Entorno. Los guards de arranque de BOS-136 exigen estas cinco. -------
os.environ.update(
    {
        "JWT_SECRET": "llave-de-prueba-local-no-es-un-secreto",
        "ADMIN_SECRET": "admin-de-prueba-local-no-es-un-secreto",
        "MONGO_URL": "mongodb://localhost:27017",
        "DB_NAME": "knowledge_wars_test",
        "CORS_ORIGINS": "http://localhost:3000",
        "ANTHROPIC_API_KEY": "sin-uso-el-cliente-esta-doblado",
    }
)

# --- 2. La base en memoria, antes de importar server.py ---------------------
import mongomock
import pymongo

pymongo.MongoClient = mongomock.MongoClient

# --- 3. El doble de Anthropic, tambien antes de importar -------------------
import anthropic
from anthropic.types import Message, TextBlock, ThinkingBlock, Usage

TOPIC = "historia de mexico"
LANGUAGE = "es"
CORRECT_LETTERS = ["A", "B", "C", "D", "E", "F", "A", "B", "C", "D"]

generated_payloads = []
recorded_requests = []


def _question_set():
    return {
        "topic": TOPIC,
        "language": LANGUAGE,
        "questions": [
            {
                "id": str(index + 1),
                "question": f"Pregunta {index + 1} sobre {TOPIC}?",
                "options": {letter: f"Opcion {letter}" for letter in "ABCDEF"},
                "correct_letter": letter,
                "hint": f"Pista {index + 1}",
                "explanation_short": f"Explicacion {index + 1}",
            }
            for index, letter in enumerate(CORRECT_LETTERS)
        ],
    }


class _FakeMessages:
    def create(self, **kwargs):
        recorded_requests.append(kwargs)
        payload = json.dumps(_question_set(), ensure_ascii=False)
        generated_payloads.append(payload)
        return Message(
            id="msg_doble",
            model=kwargs.get("model", "desconocido"),
            role="assistant",
            type="message",
            stop_reason="end_turn",
            stop_sequence=None,
            usage=Usage(input_tokens=1200, output_tokens=2600),
            content=[
                # Igual que un modelo actual con pensamiento: primer bloque sin
                # texto. `content[0].text` reventaba justo aqui.
                ThinkingBlock(type="thinking", thinking="", signature="sig"),
                TextBlock(
                    type="text",
                    text="```json\n" + payload + "\n```",
                    citations=None,
                ),
            ],
        )


class _FakeAnthropic:
    def __init__(self, *args, **kwargs):
        self.messages = _FakeMessages()


anthropic.Anthropic = _FakeAnthropic

# --- 4. Ahora si, la app real ---------------------------------------------
from fastapi.testclient import TestClient

import server

try:
    # Vive en otro PR de BOS-162. Mientras no este en main, la capa 6 se salta
    # en lugar de tumbar toda la prueba.
    from metrica_jugadores_activados import activated_players
except ImportError:
    activated_players = None

client = TestClient(server.app)

CHECKS = []


def ok(label, condition, detail=""):
    CHECKS.append((bool(condition), label, detail))
    mark = "ok  " if condition else "FAIL"
    print(f"{mark} {label}" + (f" -- {detail}" if detail else ""))
    return bool(condition)


def register(email, name):
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "contrasena-de-prueba-1234",
            "display_name": name,
            "country_code": "mx",
            "favorite_topic": TOPIC,
            "language": LANGUAGE,
        },
    )
    assert response.status_code == 200, (response.status_code, response.text[:400])
    body = response.json()
    return body["token"], body["user"]["id"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def main():
    print("=" * 72)
    print("Capa 1 -- registro")
    print("=" * 72)
    token_a, id_a = register("jugadora.a@kwtest-local.com", "Jugadora A")
    token_b, id_b = register("jugador.b@kwtest-local.com", "Jugador B")
    ok("dos jugadores registrados", id_a and id_b and id_a != id_b, f"{id_a} vs {id_b}")
    ok("usuarios en la base", server.users_col.count_documents({}) == 2)

    print()
    print("=" * 72)
    print("Capa 2 -- generacion de preguntas y creacion de la partida")
    print("=" * 72)
    response = client.post(
        "/api/matches/create",
        headers=auth(token_a),
        json={"opponent_id": id_b, "topic": TOPIC, "language": LANGUAGE},
    )
    created = ok(
        "POST /api/matches/create devuelve 200",
        response.status_code == 200,
        f"HTTP {response.status_code}: {response.text[:300]}",
    )
    if not created:
        return finish()

    match_id = response.json()["match"]["id"]
    ok("el modelo pedido es el vigente",
       recorded_requests and recorded_requests[0].get("model") == "claude-sonnet-5",
       str(recorded_requests[0].get("model") if recorded_requests else None))
    ok("el pensamiento va apagado de forma explicita",
       recorded_requests and recorded_requests[0].get("thinking") == {"type": "disabled"},
       str(recorded_requests[0].get("thinking") if recorded_requests else None))
    ok("max_tokens deja espacio para el set completo",
       recorded_requests and recorded_requests[0].get("max_tokens", 0) >= 8192,
       str(recorded_requests[0].get("max_tokens") if recorded_requests else None))

    match = server.matches_col.find_one({"_id": server.ObjectId(match_id)})
    ok("la partida guarda 10 preguntas", len(match["questions"]) == 10, str(len(match["questions"])))
    ok("el set quedo en cache", server.question_sets_col.count_documents({}) == 1)

    # Segunda partida con el mismo tema: debe salir del cache, sin nueva llamada.
    llamadas_antes = len(recorded_requests)
    response2 = client.post(
        "/api/matches/create",
        headers=auth(token_a),
        json={"opponent_id": id_b, "topic": TOPIC, "language": LANGUAGE},
    )
    ok("segunda partida con el mismo tema no vuelve a llamar al modelo",
       response2.status_code == 200 and len(recorded_requests) == llamadas_antes,
       f"HTTP {response2.status_code}, llamadas {llamadas_antes} -> {len(recorded_requests)}")
    if response2.status_code == 200:
        server.matches_col.delete_one({"_id": server.ObjectId(response2.json()["match"]["id"])})

    print()
    print("=" * 72)
    print("Capa 3 -- aceptacion")
    print("=" * 72)
    response = client.post(f"/api/matches/{match_id}/accept", headers=auth(token_b))
    accepted = ok(
        "POST /api/matches/{id}/accept devuelve 200",
        response.status_code == 200,
        f"HTTP {response.status_code}: {response.text[:300]}",
    )
    if not accepted:
        return finish()

    match = server.matches_col.find_one({"_id": server.ObjectId(match_id)})
    ok("la partida quedo activa", match["status"] == "active", match["status"])

    print()
    print("=" * 72)
    print("Capa 4 -- websocket: 10 preguntas")
    print("=" * 72)
    with client.websocket_connect(f"/ws/match/{match_id}?token={token_a}") as ws_a, \
            client.websocket_connect(f"/ws/match/{match_id}?token={token_b}") as ws_b:

        state_a = ws_a.receive_json()
        state_b = ws_b.receive_json()
        ok("ambos reciben match_state",
           state_a["type"] == "match_state" and state_b["type"] == "match_state")
        ok("match_state no filtra la respuesta correcta",
           all("correct_letter" not in q for q in state_a["match"]["questions"]))
        ok("match_state no filtra la explicacion",
           all("explanation_short" not in q for q in state_a["match"]["questions"]))

        ws_a.send_json({"type": "player_ready"})
        ws_b.send_json({"type": "player_ready"})
        start_a = ws_a.receive_json()
        start_b = ws_b.receive_json()
        ok("con 2/2 listos se emite game_start",
           start_a["type"] == "game_start" and start_b["type"] == "game_start",
           f"{start_a['type']} / {start_b['type']}")

        # A contesta bien las 10. B intenta despues y debe quedar fuera.
        for index, letter in enumerate(CORRECT_LETTERS):
            ws_a.send_json({"type": "submit_answer", "question_index": index, "answer": letter})
            result_a = ws_a.receive_json()
            result_b = ws_b.receive_json()
            if result_a["type"] != "answer_result" or result_a["result"] != "correct":
                ok(f"pregunta {index + 1}: respuesta correcta aceptada", False, str(result_a))
                break
            if index == 0:
                ok("la respuesta correcta se difunde a los dos",
                   result_b["type"] == "answer_result" and result_b["result"] == "correct")
                # B llega tarde a la misma pregunta.
                ws_b.send_json({"type": "submit_answer", "question_index": 0, "answer": letter})
                late = ws_b.receive_json()
                ok("el segundo en contestar recibe already_answered",
                   late.get("result") == "already_answered", str(late))
        else:
            ok("las 10 preguntas se contestaron correctamente", True)

    print()
    print("=" * 72)
    print("Capa 5 -- finish_match persistido")
    print("=" * 72)
    match = server.matches_col.find_one({"_id": server.ObjectId(match_id)})
    ok("status == finished", match.get("status") == "finished", str(match.get("status")))
    ok("winner_id persistido", match.get("winner_id") is not None, str(match.get("winner_id")))
    ok("el ganador es quien contesto", str(match.get("winner_id")) == id_a,
       f"{match.get('winner_id')} vs {id_a}")
    ok("elo_delta_a persistido", match.get("elo_delta_a") is not None, str(match.get("elo_delta_a")))
    ok("elo_delta_b persistido", match.get("elo_delta_b") is not None, str(match.get("elo_delta_b")))
    ok("score 20 a 0", (match.get("score_a"), match.get("score_b")) == (20, 0),
       f"{match.get('score_a')} - {match.get('score_b')}")

    user_a = server.users_col.find_one({"_id": server.ObjectId(id_a)})
    user_b = server.users_col.find_one({"_id": server.ObjectId(id_b)})
    ok("el ganador gano +2 de ELO", user_a["elo_rating"] == 502, str(user_a["elo_rating"]))
    ok("el perdedor perdio 1 de ELO", user_b["elo_rating"] == 499, str(user_b["elo_rating"]))
    ok("victoria y derrota contabilizadas",
       user_a["wins"] == 1 and user_b["losses"] == 1,
       f"wins={user_a['wins']} losses={user_b['losses']}")

    print()
    print("=" * 72)
    print("Capa 6 -- metrica 3 sobre la base que dejo la partida")
    print("=" * 72)
    if activated_players is None:
        print("     SALTADA: falta scripts/metrica_jugadores_activados.py")
        return finish()

    metrics = activated_players(server.db)
    for key, value in metrics.items():
        print(f"     {key}: {value}")
    ok("jugadores_activados == 2", metrics["jugadores_activados"] == 2, str(metrics["jugadores_activados"]))
    ok("usuarios_registrados == 2", metrics["usuarios_registrados"] == 2)
    ok("tasa_activacion == 1.0", metrics["tasa_activacion"] == 1.0)
    ok("partidas_terminadas == 1", metrics["partidas_terminadas"] == 1)
    ok("sin ids huerfanos", metrics["ids_huerfanos"] == 0)

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
