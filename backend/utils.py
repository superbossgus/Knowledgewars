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


class QuestionGenerator:
    """Anthropic Claude question generator with caching"""
    
    SYSTEM_PROMPT = """You are a trivia question generator. Output ONLY valid JSON. No markdown. 
Ensure exactly one correct option. Avoid ambiguity and time-sensitive facts."""
    
    def __init__(self, api_key: str, db):
        self.api_key = api_key
        self.db = db
        self.prompt_version = "v3"  # Updated for Anthropic Claude
    
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
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            system=self.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse and validate
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.rstrip("```")
        
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
