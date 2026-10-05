"""
Pruebas de regresion del generador de preguntas (BOS-162).

Corren sin API key y sin MongoDB: construyen objetos Message reales del SDK de
Anthropic y los pasan por el parseo y la validacion de QuestionGenerator.

    python backend/tests/test_question_generator.py
    # o
    pytest backend/tests/test_question_generator.py

Lo que estas pruebas cuidan:
  1. El primer bloque de la respuesta puede ser de pensamiento, no de texto.
     `message.content[0].text` reventaba con AttributeError.
  2. El JSON puede venir envuelto en fences de markdown, con prosa alrededor,
     o traer backticks dentro del texto de una pregunta.
  3. Truncamiento (max_tokens) y rechazo (refusal) se distinguen de
     "JSON invalido", porque son fallas distintas con arreglos distintos.
  4. Un set mal formado se rechaza aqui y no a mitad del websocket, donde
     server.py lee questions[i]["correct_letter"] sin red.
"""
import copy
import json
import os
import sys

os.environ.setdefault("JWT_SECRET", "solo-para-las-pruebas-no-es-un-secreto")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anthropic.types import Message, TextBlock, ThinkingBlock, Usage

from utils import QuestionGenerationError, QuestionGenerator


# --- helpers --------------------------------------------------------------

def make_message(blocks, stop_reason="end_turn"):
    return Message(
        id="msg_test",
        model="claude-sonnet-5",
        role="assistant",
        type="message",
        stop_reason=stop_reason,
        stop_sequence=None,
        content=blocks,
        usage=Usage(input_tokens=1, output_tokens=1),
    )


def thinking_block(text=""):
    return ThinkingBlock(type="thinking", thinking=text, signature="sig")


def text_block(text):
    return TextBlock(type="text", text=text, citations=None)


def good_set():
    return {
        "topic": "historia de mexico",
        "language": "es",
        "questions": [
            {
                "id": i + 1,
                "question": f"Pregunta {i + 1}?",
                "options": {letter: f"Opcion {letter}" for letter in "ABCDEF"},
                "correct_letter": "C",
                "hint": "una pista",
                "explanation_short": "porque si",
            }
            for i in range(10)
        ],
    }


def expect_error(callable_, needle):
    try:
        callable_()
    except QuestionGenerationError as exc:
        assert needle in str(exc), f"el mensaje {str(exc)!r} no menciona {needle!r}"
        return
    raise AssertionError(f"no lanzo QuestionGenerationError sobre {needle!r}")


def expect_invalid(mutate, needle):
    data = copy.deepcopy(good_set())
    mutate(data)
    expect_error(lambda: QuestionGenerator._validate_question_set(data), needle)


# --- 1. el bug original: primer bloque de pensamiento ---------------------

def test_thinking_block_first():
    msg = make_message([thinking_block(""), text_block(json.dumps(good_set()))])
    data = json.loads(QuestionGenerator._extract_json_text(msg))
    assert len(data["questions"]) == 10


def test_content_zero_would_have_broken():
    """Deja constancia de por que content[0].text ya no se usa."""
    msg = make_message([thinking_block(""), text_block("{}")])
    try:
        _ = msg.content[0].text
    except AttributeError:
        return
    raise AssertionError("se esperaba AttributeError en content[0].text")


# --- 2. fences de markdown y prosa ---------------------------------------

def test_fence_with_language_tag():
    msg = make_message([text_block("```json\n" + json.dumps(good_set()) + "\n```")])
    assert json.loads(QuestionGenerator._extract_json_text(msg))["language"] == "es"


def test_fence_without_language_tag():
    msg = make_message([text_block("```\n" + json.dumps(good_set()) + "\n```")])
    assert json.loads(QuestionGenerator._extract_json_text(msg))["language"] == "es"


def test_fence_surrounded_by_prose():
    body = "Aqui van:\n```json\n" + json.dumps(good_set()) + "\n```\nListo."
    msg = make_message([text_block(body)])
    assert json.loads(QuestionGenerator._extract_json_text(msg))["language"] == "es"


def test_backticks_inside_a_question():
    """El viejo split('```') partia el JSON a la mitad en este caso."""
    data = good_set()
    data["questions"][0]["question"] = "Que hace ``` en markdown?"
    msg = make_message([text_block(json.dumps(data))])
    parsed = json.loads(QuestionGenerator._extract_json_text(msg))
    assert parsed["questions"][0]["question"].count("`") == 3


def test_prose_without_fence():
    msg = make_message([text_block("Claro, aqui esta: " + json.dumps(good_set()))])
    assert json.loads(QuestionGenerator._extract_json_text(msg))["language"] == "es"


# --- 3. motivos de corte distinguibles -----------------------------------

def test_truncated_response():
    msg = make_message([text_block('{"questions": [{"quest')], stop_reason="max_tokens")
    expect_error(lambda: QuestionGenerator._extract_json_text(msg), "max_tokens")


def test_refusal():
    msg = make_message([], stop_reason="refusal")
    expect_error(lambda: QuestionGenerator._extract_json_text(msg), "rechazo")


def test_no_text_blocks():
    msg = make_message([thinking_block("")])
    expect_error(lambda: QuestionGenerator._extract_json_text(msg), "bloque de texto")


def test_text_without_json():
    msg = make_message([text_block("Lo siento, no puedo.")])
    expect_error(lambda: QuestionGenerator._extract_json_text(msg), "JSON")


# --- 4. validacion de forma ----------------------------------------------

def test_valid_set_passes():
    QuestionGenerator._validate_question_set(good_set())


def test_nine_questions():
    expect_invalid(lambda d: d["questions"].pop(), "llegaron 9")


def test_eleven_questions():
    expect_invalid(lambda d: d["questions"].append(d["questions"][0]), "llegaron 11")


def test_missing_questions_key():
    expect_invalid(lambda d: d.pop("questions"), "questions")


def test_five_options():
    expect_invalid(lambda d: d["questions"][3]["options"].pop("F"), "pregunta 4")


def test_empty_option():
    expect_invalid(lambda d: d["questions"][0]["options"].update({"B": "  "}), "opcion B")


def test_bad_correct_letter():
    expect_invalid(lambda d: d["questions"][7].update({"correct_letter": "G"}), "correct_letter")


def test_missing_correct_letter():
    expect_invalid(lambda d: d["questions"][0].pop("correct_letter"), "correct_letter")


def test_empty_question_text():
    expect_invalid(lambda d: d["questions"][2].update({"question": ""}), "question")


def test_top_level_not_an_object():
    expect_error(lambda: QuestionGenerator._validate_question_set([1, 2, 3]), "objeto JSON")


# --- 5. configuracion del modelo -----------------------------------------

def test_default_model_is_current():
    generator = QuestionGenerator(api_key="irrelevante", db=None)
    assert generator.model == "claude-sonnet-5"
    assert generator.prompt_version == "v4"


def test_question_model_env_override():
    os.environ["QUESTION_MODEL"] = "claude-haiku-4-5"
    try:
        assert QuestionGenerator(api_key="irrelevante", db=None).model == "claude-haiku-4-5"
    finally:
        del os.environ["QUESTION_MODEL"]


def test_sdk_accepts_thinking_parameter():
    """
    El SDK pinneado tiene que aceptar thinking= y saber parsear bloques de
    pensamiento. anthropic==0.28.0 no hacia ninguna de las dos cosas.
    """
    import inspect

    from anthropic.resources.messages import Messages

    assert "thinking" in inspect.signature(Messages.create).parameters
    make_message([thinking_block("razonando"), text_block("{}")])


def test_retired_model_id_is_gone():
    import llm_chat
    import utils as utils_module

    for module in (utils_module, llm_chat):
        with open(module.__file__, encoding="utf-8") as handle:
            source = handle.read()
        # Solo se permite nombrarlo en el comentario que explica por que se fue.
        live_references = [
            line
            for line in source.splitlines()
            if "claude-3-5-sonnet" in line and "se retiro" not in line
        ]
        assert not live_references, f"{module.__name__}: {live_references}"


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
