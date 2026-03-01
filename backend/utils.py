"""
Knowledge Wars - Utility Functions
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from bson import ObjectId
from passlib.context import CryptContext
from jose import JWTError, jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET", "knowledge-wars-secret-key-change-in-prod")
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
    """ELO rating calculator for Knowledge Wars"""
    
    LEAGUES = {
        'bronce': (0, 999),
        'plata': (1000, 1199),
        'oro': (1200, 1399),
        'diamante': (1400, 1599),
        'maestro': (1600, 1799),
        'gran_maestro': (1800, float('inf'))
    }
    
    @staticmethod
    def calculate_elo_change(rating_a: int, rating_b: int, score_a: float, k_factor: int = 32) -> Tuple[int, int]:
        """
        Calculate ELO change for both players
        
        Args:
            rating_a: Current ELO of player A
            rating_b: Current ELO of player B
            score_a: Actual score (1.0 = A wins, 0.5 = draw, 0.0 = B wins)
            k_factor: K-factor (higher = more volatile changes)
        
        Returns:
            (delta_a, delta_b): ELO changes for both players
        """
        # Expected score for player A
        expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
        
        # ELO change
        delta_a = round(k_factor * (score_a - expected_a))
        delta_b = -delta_a
        
        return delta_a, delta_b
    
    @staticmethod
    def get_league(rating: int) -> str:
        """Get league name from rating"""
        for league, (min_rating, max_rating) in ELOCalculator.LEAGUES.items():
            if min_rating <= rating <= max_rating:
                return league
        return 'bronce'


class QuestionGenerator:
    """OpenAI question generator with caching"""
    
    SYSTEM_PROMPT = """You are a trivia question generator. Output ONLY valid JSON. No markdown. 
Ensure exactly one correct option. Avoid ambiguity and time-sensitive facts."""
    
    def __init__(self, api_key: str, db):
        self.api_key = api_key
        self.db = db
        self.prompt_version = "v1"
    
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
- Questions must be evergreen and not rely on very recent news.

Return ONLY valid JSON (no markdown):
{{"topic":"{topic}","language":"{language}","questions":[...]}}"""
    
    async def generate_questions(self, topic: str, language: str) -> Dict[str, Any]:
        """Generate or retrieve cached question set"""
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
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
        
        # Generate new set
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"qgen_{topic_normalized}_{language}_{datetime.utcnow().timestamp()}",
            system_message=self.SYSTEM_PROMPT
        )
        chat.with_model("openai", "gpt-4o-mini")
        
        prompt = self._build_prompt(topic, language)
        response = await chat.send_message(UserMessage(text=prompt))
        
        # Parse and validate
        response_text = response.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        data = json.loads(response_text)
        
        # Validate structure
        if 'questions' not in data or len(data['questions']) != 10:
            raise ValueError(f"Invalid question set: expected 10 questions, got {len(data.get('questions', []))}")
        
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
