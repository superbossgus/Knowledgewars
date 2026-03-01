"""
Knowledge Wars - Database Models
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, _schema_generator):
        return {"type": "string"}


# User Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    country_code: str
    favorite_topic: str
    language: str = "es"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserProfile(BaseModel):
    id: str
    email: str
    display_name: str
    country_code: str
    favorite_topic: str
    dnd_enabled: bool
    elo_rating: int
    league: str
    premium_status: bool
    premium_expiration: Optional[datetime]
    created_at: datetime
    wins: int = 0
    losses: int = 0
    total_duels: int = 0


# Question Models
class QuestionOption(BaseModel):
    A: str
    B: str
    C: str
    D: str
    E: str
    F: str


class Question(BaseModel):
    id: str
    question: str
    options: QuestionOption
    correct_letter: str
    hint: str
    explanation_short: Optional[str] = None


class QuestionSet(BaseModel):
    topic: str
    language: str
    questions: List[Question]


# Match Models
class MatchCreate(BaseModel):
    opponent_id: str
    topic: str
    language: str


class MatchAnswer(BaseModel):
    match_id: str
    question_index: int
    answer: str


class MatchHint(BaseModel):
    match_id: str
    question_index: int


class MatchState(BaseModel):
    match_id: str
    player_a_id: str
    player_b_id: str
    player_a_name: str
    player_b_name: str
    player_a_country: str
    player_b_country: str
    score_a: int = 0
    score_b: int = 0
    current_question: int = 0
    questions: List[Question]
    started_at: datetime
    status: str = "active"  # active, finished


# Payment Models
class CheckoutRequest(BaseModel):
    product_type: str  # "premium_subscription" or "consumable_100"
    origin_url: str


class CouponCreate(BaseModel):
    code: str
    discount_type: str  # "percentage" or "fixed"
    discount_value: float
    max_uses: int
    expiration: Optional[datetime] = None


class CouponApply(BaseModel):
    code: str
    checkout_session_id: str


# Leaderboard Models
class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    display_name: str
    country_code: str
    elo_rating: int
    league: str
    wins: int
    losses: int
    total_duels: int


class LeaderboardResponse(BaseModel):
    type: str  # "global", "weekly", "topic"
    entries: List[LeaderboardEntry]
