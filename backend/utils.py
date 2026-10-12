"""
Knowledge Wars - Utility Functions
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from bson import ObjectId
from passlib.context import CryptContext
from jose import JWTError, jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration - REQUIRED environment variable
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET environment variable is required for production security")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict]:
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def serialize_doc(doc: Any) -> Any:
    """Serialize MongoDB document for JSON response"""
    if doc is None:
        return None
    
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    
    if isinstance(doc, dict):
        serialized = {}
        for key, value in doc.items():
            if key == "_id" and isinstance(value, ObjectId):
                serialized["id"] = str(value)
            elif isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = serialize_doc(value)
            elif isinstance(value, list):
                serialized[key] = serialize_doc(value)
            else:
                serialized[key] = value
        return serialized
    
    return doc


class ELOCalculator:
    """ELO rating calculator for Knowledge Wars - New Ranking System"""
    
    # Starting ELO for new players
    STARTING_ELO = 500
    
    # Points per result
    WIN_POINTS = 2
    LOSS_POINTS = -1
    
    # All ranks from lowest to highest (each 50 ELO points)
    RANKS = [
        # Bronce (500-649)
        {'name': 'BRONCE III', 'min': 500, 'max': 549, 'tier': 'bronce', 'tier_num': 1},
        {'name': 'BRONCE II', 'min': 550, 'max': 599, 'tier': 'bronce', 'tier_num': 1},
        {'name': 'BRONCE I', 'min': 600, 'max': 649, 'tier': 'bronce', 'tier_num': 1},
        # Plata (650-799)
        {'name': 'PLATA III', 'min': 650, 'max': 699, 'tier': 'plata', 'tier_num': 2},
        {'name': 'PLATA II', 'min': 700, 'max': 749, 'tier': 'plata', 'tier_num': 2},
        {'name': 'PLATA I', 'min': 750, 'max': 799, 'tier': 'plata', 'tier_num': 2},
        # Oro (800-949)
        {'name': 'ORO III', 'min': 800, 'max': 849, 'tier': 'oro', 'tier_num': 3},
        {'name': 'ORO II', 'min': 850, 'max': 899, 'tier': 'oro', 'tier_num': 3},
        {'name': 'ORO I', 'min': 900, 'max': 949, 'tier': 'oro', 'tier_num': 3},
        # Platino (950-1099)
        {'name': 'PLATINO III', 'min': 950, 'max': 999, 'tier': 'platino', 'tier_num': 4},
        {'name': 'PLATINO II', 'min': 1000, 'max': 1049, 'tier': 'platino', 'tier_num': 4},
        {'name': 'PLATINO I', 'min': 1050, 'max': 1099, 'tier': 'platino', 'tier_num': 4},
        # Diamante (1100-1249)
        {'name': 'DIAMANTE III', 'min': 1100, 'max': 1149, 'tier': 'diamante', 'tier_num': 5},
        {'name': 'DIAMANTE II', 'min': 1150, 'max': 1199, 'tier': 'diamante', 'tier_num': 5},
        {'name': 'DIAMANTE I', 'min': 1200, 'max': 1249, 'tier': 'diamante', 'tier_num': 5},
        # Maestro (1250-1399)
        {'name': 'MAESTRO III', 'min': 1250, 'max': 1299, 'tier': 'maestro', 'tier_num': 6},
        {'name': 'MAESTRO II', 'min': 1300, 'max': 1349, 'tier': 'maestro', 'tier_num': 6},
        {'name': 'MAESTRO I', 'min': 1350, 'max': 1399, 'tier': 'maestro', 'tier_num': 6},
        # Campeón (1400-1549)
        {'name': 'CAMPEÓN III', 'min': 1400, 'max': 1449, 'tier': 'campeon', 'tier_num': 7},
        {'name': 'CAMPEÓN II', 'min': 1450, 'max': 1499, 'tier': 'campeon', 'tier_num': 7},
        {'name': 'CAMPEÓN I', 'min': 1500, 'max': 1549, 'tier': 'campeon', 'tier_num': 7},
        # Gran Maestro (1550-1699)
        {'name': 'GRAN MAESTRO III', 'min': 1550, 'max': 1599, 'tier': 'gran_maestro', 'tier_num': 8},
        {'name': 'GRAN MAESTRO II', 'min': 1600, 'max': 1649, 'tier': 'gran_maestro', 'tier_num': 8},
        {'name': 'GRAN MAESTRO I', 'min': 1650, 'max': 1699, 'tier': 'gran_maestro', 'tier_num': 8},
        # Genio del Conocimiento (1700+)
        {'name': 'GENIO DEL CONOCIMIENTO', 'min': 1700, 'max': float('inf'), 'tier': 'genio', 'tier_num': 9},
    ]
    
    # Tier ranges for matchmaking
    TIER_RANGES = {
        'bronce': (500, 649),
        'plata': (650, 799),
        'oro': (800, 949),
        'platino': (950, 1099),
        'diamante': (1100, 1249),
        'maestro': (1250, 1399),
        'campeon': (1400, 1549),
        'gran_maestro': (1550, 1699),
        'genio': (1700, float('inf'))
    }
    
    @staticmethod
    def calculate_elo_change(winner: bool) -> int:
        """
        Calculate ELO change based on win/loss
        
        Args:
            winner: True if player won, False if lost
        
        Returns:
            ELO change (positive for win, negative for loss)
        """
        return ELOCalculator.WIN_POINTS if winner else ELOCalculator.LOSS_POINTS
    
    @staticmethod
    def get_rank(rating: int) -> dict:
        """Get full rank info from rating"""
        # Handle below minimum
        if rating < 500:
            return ELOCalculator.RANKS[0]
        
        for rank in ELOCalculator.RANKS:
            if rank['min'] <= rating <= rank['max']:
                return rank
        
        # Default to highest rank if above max
        return ELOCalculator.RANKS[-1]
    
    @staticmethod
    def get_rank_name(rating: int) -> str:
        """Get rank name from rating"""
        return ELOCalculator.get_rank(rating)['name']
    
    @staticmethod
    def get_tier(rating: int) -> str:
        """Get tier name from rating (for matchmaking)"""
        return ELOCalculator.get_rank(rating)['tier']
    
    @staticmethod
    def get_tier_range(rating: int) -> tuple:
        """Get the ELO range for matchmaking based on player's tier"""
        tier = ELOCalculator.get_tier(rating)
        return ELOCalculator.TIER_RANGES.get(tier, (500, 649))
    
    @staticmethod
    def get_league(rating: int) -> str:
        """Get league name from rating (legacy compatibility)"""
        return ELOCalculator.get_tier(rating)
    
    @staticmethod
    def get_progress_to_next_rank(rating: int) -> dict:
        """Get progress info towards next rank"""
        rank = ELOCalculator.get_rank(rating)
        rank_index = ELOCalculator.RANKS.index(rank)
        
        # If at max rank
        if rank_index == len(ELOCalculator.RANKS) - 1:
            return {
                'current_rank': rank['name'],
                'next_rank': None,
                'progress': 100,
                'points_to_next': 0
            }
        
        next_rank = ELOCalculator.RANKS[rank_index + 1]
        points_in_current = rating - rank['min']
        points_needed = rank['max'] - rank['min'] + 1  # 50 points per rank
        progress = min(100, int((points_in_current / points_needed) * 100))
        
        return {
            'current_rank': rank['name'],
            'next_rank': next_rank['name'],
            'progress': progress,
            'points_to_next': next_rank['min'] - rating
        }


class QuestionGenerationError(RuntimeError):
    """
    Falla al generar un set de preguntas.

    server.py convierte cualquier excepcion de generate_questions en un
    HTTPException 500, asi que el mensaje de esta excepcion es lo unico que
    llega a los logs: tiene que decir *por que* fallo, no solo que fallo.
    """


class QuestionGenerator:
    """Anthropic Claude question generator with caching"""

    SYSTEM_PROMPT = """You are a trivia question generator. Output ONLY valid JSON. No markdown.
Ensure exactly one correct option. Avoid ambiguity and time-sensitive facts."""

    # claude-3-5-sonnet-20241022 se retiro el 2025-10-28 y devolvia 404, lo que
    # rompia POST /api/matches/create. El reemplazo directo es claude-sonnet-5.
    # Configurable por entorno para poder bajar a claude-haiku-4-5 sin redeploy
    # de codigo si el costo por tema nuevo llega a importar.
    DEFAULT_MODEL = "claude-sonnet-5"

    # Un set son 10 preguntas x 6 opciones + pista + explicacion. Con el
    # tokenizador nuevo (~30% mas tokens que el modelo retirado) 2048 truncaba
    # la respuesta a la mitad y json.loads moria con "Unterminated string".
    MAX_TOKENS = 8192

    EXPECTED_QUESTIONS = 10
    OPTION_LETTERS = ("A", "B", "C", "D", "E", "F")

    # Pedimos JSON sin markdown, pero el modelo a veces lo envuelve igual.
    _FENCE_RE = re.compile(r"```[a-zA-Z0-9_+-]*\s*(?P<body>.*?)\s*```", re.DOTALL)

    def __init__(self, api_key: str, db, model: Optional[str] = None):
        self.api_key = api_key
        self.db = db
        self.model = model or os.getenv("QUESTION_MODEL") or self.DEFAULT_MODEL
        self.prompt_version = "v4"  # v4: claude-sonnet-5 + parseo/validacion estrictos

    def _normalize_topic(self, topic: str) -> str:
        """Normalize topic for caching"""
        return topic.lower().strip().replace(" ", "_")
    
    def _build_prompt(self, topic: str, language: str) -> str:
        """Build generation prompt"""
        lang_map = {"es": "Spanish", "en": "English", "pt": "Portuguese"}
        lang_full = lang_map.get(language, "English")
        
        return f"""Generate 10 multiple-choice trivia questions in {lang_full} about: "{topic}".
Rules:
- 6 options labeled A,B,C,D,E,F.
- Exactly one correct option.
- Provide fields: id, question, options (object with A,B,C,D,E,F keys), correct_letter, hint, explanation_short.
- IMPORTANT: ALL text fields (question, options, hint, explanation_short) MUST be in {lang_full}. Do NOT use English for hints if the language is {lang_full}.
- Questions must be evergreen and not rely on very recent news.

Return ONLY valid JSON (no markdown):
{{"topic":"{topic}","language":"{language}","questions":[...]}}"""

    @classmethod
    def _extract_json_text(cls, message: Any) -> str:
        """
        Saca el JSON del mensaje de Claude.

        Antes esto era `message.content[0].text`, que asume que el primer bloque
        de la respuesta es texto. Con los modelos actuales el primer bloque puede
        ser un bloque de pensamiento (texto vacio por omision) y la indexacion
        silenciosamente entregaba una cadena vacia a json.loads. Tambien separa
        los dos motivos de corte que antes se veian identicos a "JSON invalido":
        respuesta truncada y rechazo del clasificador.
        """
        stop_reason = getattr(message, "stop_reason", None)
        if stop_reason == "refusal":
            raise QuestionGenerationError(
                "El modelo rechazo generar preguntas para este tema "
                "(stop_reason=refusal). Pide otro tema."
            )
        if stop_reason == "max_tokens":
            raise QuestionGenerationError(
                f"La respuesta se trunco al llegar a max_tokens={cls.MAX_TOKENS}; "
                "el JSON quedo incompleto."
            )

        texts = [
            block.text
            for block in getattr(message, "content", []) or []
            if getattr(block, "type", None) == "text"
        ]
        if not texts:
            raise QuestionGenerationError(
                f"La respuesta no trae ningun bloque de texto (stop_reason={stop_reason})."
            )

        text = "".join(texts).strip()

        # Quita el bloque de markdown completo si viene envuelto.
        fenced = cls._FENCE_RE.search(text)
        if fenced:
            text = fenced.group("body").strip()

        # Ultimo recurso: recorta cualquier prosa antes/despues del objeto JSON.
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end <= start:
                raise QuestionGenerationError(
                    "La respuesta no contiene un objeto JSON reconocible."
                )
            text = text[start:end + 1]

        return text

    @classmethod
    def _validate_question_set(cls, data: Any) -> None:
        """
        Exige la forma exacta que server.py consume mas adelante.

        server.py:1854 lee `questions[i]["correct_letter"]` sin red de proteccion:
        un set mal formado no falla al crear la partida, falla a mitad del
        websocket cuando los dos jugadores ya estan dentro. Mejor reventar aqui.
        """
        if not isinstance(data, dict):
            raise QuestionGenerationError(
                f"Se esperaba un objeto JSON, llego {type(data).__name__}."
            )

        questions = data.get("questions")
        if not isinstance(questions, list):
            raise QuestionGenerationError(
                "Falta la lista 'questions' o no es una lista."
            )
        if len(questions) != cls.EXPECTED_QUESTIONS:
            raise QuestionGenerationError(
                f"Se esperaban {cls.EXPECTED_QUESTIONS} preguntas, llegaron {len(questions)}."
            )

        for index, question in enumerate(questions):
            where = f"pregunta {index + 1}"

            if not isinstance(question, dict):
                raise QuestionGenerationError(
                    f"{where}: se esperaba un objeto, llego {type(question).__name__}."
                )

            text = question.get("question")
            if not isinstance(text, str) or not text.strip():
                raise QuestionGenerationError(f"{where}: 'question' vacio o no es texto.")

            options = question.get("options")
            if not isinstance(options, dict):
                raise QuestionGenerationError(f"{where}: falta el objeto 'options'.")
            if set(options) != set(cls.OPTION_LETTERS):
                raise QuestionGenerationError(
                    f"{where}: 'options' debe tener exactamente las llaves "
                    f"{', '.join(cls.OPTION_LETTERS)}; llegaron: "
                    f"{', '.join(sorted(map(str, options))) or '(ninguna)'}."
                )
            for letter in cls.OPTION_LETTERS:
                value = options[letter]
                if not isinstance(value, str) or not value.strip():
                    raise QuestionGenerationError(
                        f"{where}: la opcion {letter} esta vacia o no es texto."
                    )

            correct = question.get("correct_letter")
            if correct not in cls.OPTION_LETTERS:
                raise QuestionGenerationError(
                    f"{where}: 'correct_letter' debe ser una de "
                    f"{', '.join(cls.OPTION_LETTERS)}; llego {correct!r}."
                )

            # server.py lee estos dos con .get()/.pop(), asi que no son
            # obligatorios, pero si vienen deben ser texto.
            for optional_field in ("hint", "explanation_short"):
                value = question.get(optional_field)
                if value is not None and not isinstance(value, str):
                    raise QuestionGenerationError(
                        f"{where}: '{optional_field}' debe ser texto si viene."
                    )

    async def generate_questions(self, topic: str, language: str) -> Dict[str, Any]:
        """Generate or retrieve cached question set"""
        import anthropic
        
        topic_normalized = self._normalize_topic(topic)
        
        # Check cache first
        cached = self.db.question_sets.find_one({
            'topic_normalized': topic_normalized,
            'language': language,
            'prompt_version': self.prompt_version
        })
        
        if cached:
            # Increment usage count
            self.db.question_sets.update_one(
                {'_id': cached['_id']},
                {'$inc': {'usage_count': 1}}
            )
            return cached['questions_json']
        
        # Generate new set using Anthropic Claude
        client = anthropic.Anthropic(api_key=self.api_key)

        prompt = self._build_prompt(topic, language)
        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=self.MAX_TOKENS,
                system=self.SYSTEM_PROMPT,
                # Generar trivia es una tarea determinista y los tokens de
                # razonamiento salen del mismo max_tokens que el JSON. En
                # claude-sonnet-5 el pensamiento adaptativo esta encendido por
                # omision, asi que hay que apagarlo de forma explicita.
                thinking={"type": "disabled"},
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
        except anthropic.APIStatusError as exc:
            raise QuestionGenerationError(
                f"La API de Anthropic rechazo la peticion con modelo '{self.model}' "
                f"(HTTP {exc.status_code}): {exc}"
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise QuestionGenerationError(
                f"No se pudo contactar la API de Anthropic: {exc}"
            ) from exc

        # Parse and validate
        response_text = self._extract_json_text(message)
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise QuestionGenerationError(
                f"El modelo '{self.model}' no devolvio JSON valido ({exc.msg} "
                f"en la posicion {exc.pos}); longitud de la respuesta: {len(response_text)}"
            ) from exc

        self._validate_question_set(data)

        # Cache the set
        self.db.question_sets.insert_one({
            'topic': topic,
            'topic_normalized': topic_normalized,
            'language': language,
            'prompt_version': self.prompt_version,
            'questions_json': data,
            'created_at': datetime.utcnow(),
            'usage_count': 1
        })
        
        return data
