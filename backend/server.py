"""
Knowledge Wars - Main Server
FastAPI backend with WebSocket support for real-time duels
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient, DESCENDING
from bson import ObjectId

from models import (
    UserCreate, UserLogin, UserProfile, MatchCreate, MatchAnswer, MatchHint,
    CheckoutRequest, CouponCreate, CouponApply, LeaderboardEntry, LeaderboardResponse
)
from utils import (
    hash_password, verify_password, create_access_token, decode_access_token,
    serialize_doc, ELOCalculator, QuestionGenerator
)
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse
)

# Load environment
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Knowledge Wars API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "knowledge_wars")
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Collections
users_col = db["users"]
matches_col = db["matches"]
match_events_col = db["match_events"]
question_sets_col = db["question_sets"]
duel_counters_col = db["duel_counters"]
subscriptions_col = db["subscriptions"]
purchases_col = db["purchases"]
coupons_col = db["coupons"]
payment_transactions_col = db["payment_transactions"]

# Indexes
users_col.create_index("email", unique=True)
matches_col.create_index([("created_at", DESCENDING)])
question_sets_col.create_index([("topic_normalized", 1), ("language", 1)])

# Services
EMERGENT_LLM_KEY = os.getenv("EMERGENT_LLM_KEY")
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
question_generator = QuestionGenerator(EMERGENT_LLM_KEY, db)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.match_rooms: Dict[str, Dict] = {}
    
    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except:
                self.disconnect(user_id)
    
    async def broadcast_to_match(self, match_id: str, message: dict, exclude_user: Optional[str] = None):
        """Broadcast message to all users in a match"""
        match = matches_col.find_one({"_id": ObjectId(match_id)})
        if match:
            for user_id in [str(match["player_a_id"]), str(match["player_b_id"])]:
                if user_id != exclude_user:
                    await self.send_message(user_id, message)

manager = ConnectionManager()


# Authentication dependency
async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Get current authenticated user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = users_col.find_one({"_id": ObjectId(payload["user_id"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return serialize_doc(user)
    except:
        raise HTTPException(status_code=401, detail="Authentication failed")


# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@app.post("/api/auth/register")
async def register(user_data: UserCreate):
    """Register new user"""
    # Check if user exists
    existing = users_col.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_doc = {
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "display_name": user_data.display_name,
        "country_code": user_data.country_code,
        "favorite_topic": user_data.favorite_topic,
        "language": user_data.language,
        "dnd_enabled": False,
        "elo_rating": 1200,
        "league": "plata",
        "premium_status": False,
        "premium_expiration": None,
        "created_at": datetime.utcnow(),
        "wins": 0,
        "losses": 0,
        "total_duels": 0
    }
    
    result = users_col.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    
    # Create JWT token
    token = create_access_token({"user_id": str(result.inserted_id)})
    
    return {
        "token": token,
        "user": serialize_doc(user_doc)
    }


@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    """Login user"""
    user = users_col.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"user_id": str(user["_id"])})
    
    return {
        "token": token,
        "user": serialize_doc(user)
    }


@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    return serialize_doc(current_user)


# ============================================================================
# USER ENDPOINTS
# ============================================================================

@app.get("/api/users/online")
async def get_online_users(current_user: dict = Depends(get_current_user)):
    """Get list of online users for matchmaking"""
    # Get users who are connected via WebSocket and not in DND mode
    online_user_ids = list(manager.active_connections.keys())
    
    users = users_col.find(
        {
            "_id": {"$in": [ObjectId(uid) for uid in online_user_ids if uid != current_user["id"]]},
            "dnd_enabled": False
        },
        {
            "display_name": 1,
            "country_code": 1,
            "elo_rating": 1,
            "league": 1,
            "favorite_topic": 1
        }
    ).limit(50)
    
    return {"users": serialize_doc(list(users))}


@app.patch("/api/users/dnd")
async def toggle_dnd(enabled: bool, current_user: dict = Depends(get_current_user)):
    """Toggle Do Not Disturb mode"""
    users_col.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": {"dnd_enabled": enabled}}
    )
    return {"success": True, "dnd_enabled": enabled}


@app.get("/api/users/profile/{user_id}")
async def get_user_profile(user_id: str):
    """Get user profile by ID"""
    user = users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get match history (without full questions array)
    matches = list(matches_col.find(
        {
            "$or": [
                {"player_a_id": ObjectId(user_id)},
                {"player_b_id": ObjectId(user_id)}
            ],
            "status": "finished"
        },
        {
            "player_a_name": 1,
            "player_b_name": 1,
            "player_a_country": 1,
            "player_b_country": 1,
            "score_a": 1,
            "score_b": 1,
            "topic": 1,
            "language": 1,
            "ended_at": 1,
            "winner_id": 1,
            "elo_delta_a": 1,
            "elo_delta_b": 1
        }
    ).sort("ended_at", DESCENDING).limit(10))
    
    return {
        "user": serialize_doc(user),
        "recent_matches": serialize_doc(matches)
    }


# ============================================================================
# DUEL COUNTER & LIMITS
# ============================================================================

def get_duel_counter(user_id: str) -> dict:
    """Get or create duel counter for current month"""
    current_month = datetime.utcnow().strftime("%Y-%m")
    
    counter = duel_counters_col.find_one({
        "user_id": ObjectId(user_id),
        "month": current_month
    })
    
    if not counter:
        counter = {
            "user_id": ObjectId(user_id),
            "month": current_month,
            "duels_used": 0,
            "consumable_extra_100": 0,
            "rewarded_extra": 0,
            "updated_at": datetime.utcnow()
        }
        duel_counters_col.insert_one(counter)
    
    return counter


def check_duel_limit(user_id: str) -> bool:
    """Check if user can play another duel"""
    user = users_col.find_one({"_id": ObjectId(user_id)})
    
    # Premium users have unlimited duels
    if user.get("premium_status") and user.get("premium_expiration"):
        if user["premium_expiration"] > datetime.utcnow():
            return True
    
    # Check monthly limit
    counter = get_duel_counter(user_id)
    limit = 100 + (counter.get("consumable_extra_100", 0) * 100) + counter.get("rewarded_extra", 0)
    
    return counter.get("duels_used", 0) < limit


def increment_duel_counter(user_id: str):
    """Increment duel counter"""
    current_month = datetime.utcnow().strftime("%Y-%m")
    duel_counters_col.update_one(
        {"user_id": ObjectId(user_id), "month": current_month},
        {"$inc": {"duels_used": 1}, "$set": {"updated_at": datetime.utcnow()}},
        upsert=True
    )


@app.get("/api/users/duels/remaining")
async def get_remaining_duels(current_user: dict = Depends(get_current_user)):
    """Get remaining duels for current user"""
    user = users_col.find_one({"_id": ObjectId(current_user["id"])})
    
    # Premium unlimited
    if user.get("premium_status") and user.get("premium_expiration"):
        if user["premium_expiration"] > datetime.utcnow():
            return {"remaining": -1, "unlimited": True, "premium": True}
    
    counter = get_duel_counter(current_user["id"])
    limit = 100 + (counter.get("consumable_extra_100", 0) * 100) + counter.get("rewarded_extra", 0)
    used = counter.get("duels_used", 0)
    
    return {
        "remaining": max(0, limit - used),
        "limit": limit,
        "used": used,
        "unlimited": False,
        "premium": False
    }


# ============================================================================
# TOPICS & QUESTIONS
# ============================================================================

@app.get("/api/topics/top")
async def get_top_topics():
    """Get top 10 most used topics"""
    pipeline = [
        {"$group": {"_id": "$topic", "count": {"$sum": "$usage_count"}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    result = list(question_sets_col.aggregate(pipeline))
    topics = [{"topic": doc["_id"], "count": doc["count"]} for doc in result]
    
    # Add predefined topics if not enough
    predefined = ["Sports", "History", "Geography", "Science", "Technology", 
                  "Movies/TV", "Music", "Business/Finance", "Gaming", "General Knowledge"]
    
    existing_topics = [t["topic"] for t in topics]
    for topic in predefined:
        if topic not in existing_topics and len(topics) < 10:
            topics.append({"topic": topic, "count": 0})
    
    return {"topics": topics[:10]}


@app.get("/api/questions/generate")
async def generate_questions(topic: str, language: str = "es", current_user: dict = Depends(get_current_user)):
    """Generate questions for a topic (server-only, not exposed to client during match)"""
    try:
        questions = await question_generator.generate_questions(topic, language)
        return questions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")


# ============================================================================
# MATCH ENDPOINTS
# ============================================================================

@app.post("/api/matches/create")
async def create_match(match_data: MatchCreate, current_user: dict = Depends(get_current_user)):
    """Create a new match challenge"""
    # Check duel limit
    if not check_duel_limit(current_user["id"]):
        raise HTTPException(status_code=403, detail="Duel limit reached. Upgrade to Premium or purchase more duels.")
    
    # Check opponent exists and is not in DND
    opponent = users_col.find_one({"_id": ObjectId(match_data.opponent_id)})
    if not opponent:
        raise HTTPException(status_code=404, detail="Opponent not found")
    
    if opponent.get("dnd_enabled"):
        raise HTTPException(status_code=400, detail="Opponent is in Do Not Disturb mode")
    
    # Generate questions
    try:
        question_set = await question_generator.generate_questions(match_data.topic, match_data.language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")
    
    # Create match
    match_doc = {
        "player_a_id": ObjectId(current_user["id"]),
        "player_b_id": ObjectId(match_data.opponent_id),
        "player_a_name": current_user["display_name"],
        "player_b_name": opponent["display_name"],
        "player_a_country": current_user["country_code"],
        "player_b_country": opponent["country_code"],
        "topic": match_data.topic,
        "language": match_data.language,
        "questions": question_set["questions"],
        "score_a": 0,
        "score_b": 0,
        "current_question": 0,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "started_at": None,
        "ended_at": None,
        "winner_id": None,
        "elo_delta_a": 0,
        "elo_delta_b": 0
    }
    
    result = matches_col.insert_one(match_doc)
    match_doc["_id"] = result.inserted_id
    
    # Send challenge notification to opponent
    await manager.send_message(match_data.opponent_id, {
        "type": "challenge_received",
        "match": serialize_doc(match_doc),
        "challenger": serialize_doc(current_user)
    })
    
    return {"match": serialize_doc(match_doc)}


@app.post("/api/matches/{match_id}/accept")
async def accept_match(match_id: str, current_user: dict = Depends(get_current_user)):
    """Accept a match challenge"""
    match = matches_col.find_one({"_id": ObjectId(match_id)})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if str(match["player_b_id"]) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if match["status"] != "pending":
        raise HTTPException(status_code=400, detail="Match already started or finished")
    
    # Check duel limit for accepter
    if not check_duel_limit(current_user["id"]):
        raise HTTPException(status_code=403, detail="Duel limit reached")
    
    # Update match status
    matches_col.update_one(
        {"_id": ObjectId(match_id)},
        {"$set": {"status": "active", "started_at": datetime.utcnow()}}
    )
    
    # Increment duel counters for both players
    increment_duel_counter(str(match["player_a_id"]))
    increment_duel_counter(str(match["player_b_id"]))
    
    # Notify both players
    await manager.broadcast_to_match(match_id, {
        "type": "match_started",
        "match_id": match_id
    })
    
    return {"success": True, "match_id": match_id}


@app.post("/api/matches/{match_id}/reject")
async def reject_match(match_id: str, current_user: dict = Depends(get_current_user)):
    """Reject a match challenge"""
    match = matches_col.find_one({"_id": ObjectId(match_id)})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if str(match["player_b_id"]) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update match status
    matches_col.update_one(
        {"_id": ObjectId(match_id)},
        {"$set": {"status": "rejected"}}
    )
    
    # Notify challenger
    await manager.send_message(str(match["player_a_id"]), {
        "type": "challenge_rejected",
        "match_id": match_id
    })
    
    return {"success": True}


@app.get("/api/matches/{match_id}")
async def get_match(match_id: str, current_user: dict = Depends(get_current_user)):
    """Get match details"""
    match = matches_col.find_one({"_id": ObjectId(match_id)})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Check authorization
    if str(match["player_a_id"]) not in [current_user["id"]] and str(match["player_b_id"]) not in [current_user["id"]]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {"match": serialize_doc(match)}


# ============================================================================
# WEBSOCKET FOR REAL-TIME MATCH
# ============================================================================

@app.websocket("/ws/match/{match_id}")
async def websocket_match(websocket: WebSocket, match_id: str, token: str):
    """WebSocket endpoint for real-time match gameplay"""
    # Authenticate
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=1008)
        return
    
    user_id = payload["user_id"]
    
    # Verify match exists and user is participant
    match = matches_col.find_one({"_id": ObjectId(match_id)})
    if not match:
        await websocket.close(code=1008)
        return
    
    if str(match["player_a_id"]) != user_id and str(match["player_b_id"]) != user_id:
        await websocket.close(code=1008)
        return
    
    await manager.connect(user_id, websocket)
    
    try:
        # Send initial match state (without correct answers)
        match_state = serialize_doc(match)
        
        # Remove correct answers from questions
        for q in match_state["questions"]:
            q.pop("correct_letter", None)
            q.pop("explanation_short", None)
        
        await websocket.send_json({
            "type": "match_state",
            "match": match_state
        })
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "submit_answer":
                await handle_answer_submission(match_id, user_id, data)
            
            elif data["type"] == "request_hint":
                await handle_hint_request(match_id, user_id, data)
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(user_id)


async def handle_answer_submission(match_id: str, user_id: str, data: dict):
    """Handle answer submission in real-time"""
    match = matches_col.find_one({"_id": ObjectId(match_id)})
    if not match or match["status"] != "active":
        return
    
    question_index = data.get("question_index", 0)
    answer = data.get("answer")
    timestamp = datetime.utcnow()
    
    # Get correct answer
    if question_index >= len(match["questions"]):
        return
    
    correct_answer = match["questions"][question_index]["correct_letter"]
    
    # Check if already answered correctly by someone
    events = list(match_events_col.find({
        "match_id": ObjectId(match_id),
        "question_index": question_index,
        "event_type": "correct_answer"
    }))
    
    if events:
        # Already answered
        await manager.send_message(user_id, {
            "type": "answer_result",
            "result": "already_answered",
            "score_delta": 0
        })
        return
    
    # Determine if user is player A or B
    is_player_a = str(match["player_a_id"]) == user_id
    
    # Check if correct
    if answer == correct_answer:
        # Correct! Award +2 points
        score_field = "score_a" if is_player_a else "score_b"
        matches_col.update_one(
            {"_id": ObjectId(match_id)},
            {"$inc": {score_field: 2}}
        )
        
        # Log event
        match_events_col.insert_one({
            "match_id": ObjectId(match_id),
            "user_id": ObjectId(user_id),
            "question_index": question_index,
            "event_type": "correct_answer",
            "answer": answer,
            "timestamp": timestamp
        })
        
        # Notify both players
        await manager.broadcast_to_match(match_id, {
            "type": "answer_result",
            "user_id": user_id,
            "result": "correct",
            "score_delta": 2,
            "correct_answer": correct_answer
        })
        
        # Check if match is finished (10 questions)
        if question_index >= 9:
            await finish_match(match_id)
    
    else:
        # Incorrect
        match_events_col.insert_one({
            "match_id": ObjectId(match_id),
            "user_id": ObjectId(user_id),
            "question_index": question_index,
            "event_type": "incorrect_answer",
            "answer": answer,
            "timestamp": timestamp
        })
        
        # Notify user
        await manager.send_message(user_id, {
            "type": "answer_result",
            "result": "incorrect",
            "score_delta": 0
        })
        
        # Notify opponent they can try
        opponent_id = str(match["player_b_id"]) if is_player_a else str(match["player_a_id"])
        await manager.send_message(opponent_id, {
            "type": "opponent_locked",
            "question_index": question_index
        })


async def handle_hint_request(match_id: str, user_id: str, data: dict):
    """Handle hint request"""
    match = matches_col.find_one({"_id": ObjectId(match_id)})
    if not match or match["status"] != "active":
        return
    
    question_index = data.get("question_index", 0)
    
    # Check if hint already requested for this question by this user
    existing = match_events_col.find_one({
        "match_id": ObjectId(match_id),
        "user_id": ObjectId(user_id),
        "question_index": question_index,
        "event_type": "hint_requested"
    })
    
    if existing:
        await manager.send_message(user_id, {
            "type": "hint_result",
            "result": "already_requested"
        })
        return
    
    # Deduct 1 point
    is_player_a = str(match["player_a_id"]) == user_id
    score_field = "score_a" if is_player_a else "score_b"
    
    matches_col.update_one(
        {"_id": ObjectId(match_id)},
        {"$inc": {score_field: -1}}
    )
    
    # Log event
    match_events_col.insert_one({
        "match_id": ObjectId(match_id),
        "user_id": ObjectId(user_id),
        "question_index": question_index,
        "event_type": "hint_requested",
        "timestamp": datetime.utcnow()
    })
    
    # Send hint to user
    hint = match["questions"][question_index].get("hint", "")
    await manager.send_message(user_id, {
        "type": "hint_result",
        "result": "success",
        "hint": hint,
        "score_delta": -1
    })
    
    # Notify opponent
    opponent_id = str(match["player_b_id"]) if is_player_a else str(match["player_a_id"])
    await manager.send_message(opponent_id, {
        "type": "opponent_hint",
        "question_index": question_index
    })


async def finish_match(match_id: str):
    """Finish a match and calculate ELO changes"""
    match = matches_col.find_one({"_id": ObjectId(match_id)})
    if not match or match["status"] != "active":
        return
    
    # Get final scores
    score_a = match["score_a"]
    score_b = match["score_b"]
    
    # Determine winner
    winner_id = None
    score_result = 0.5  # draw
    
    if score_a > score_b:
        winner_id = match["player_a_id"]
        score_result = 1.0
    elif score_b > score_a:
        winner_id = match["player_b_id"]
        score_result = 0.0
    
    # Get current ELO ratings
    user_a = users_col.find_one({"_id": match["player_a_id"]})
    user_b = users_col.find_one({"_id": match["player_b_id"]})
    
    elo_a = user_a["elo_rating"]
    elo_b = user_b["elo_rating"]
    
    # Calculate ELO changes
    delta_a, delta_b = ELOCalculator.calculate_elo_change(elo_a, elo_b, score_result)
    
    new_elo_a = elo_a + delta_a
    new_elo_b = elo_b + delta_b
    
    # Update users
    users_col.update_one(
        {"_id": match["player_a_id"]},
        {
            "$set": {
                "elo_rating": new_elo_a,
                "league": ELOCalculator.get_league(new_elo_a)
            },
            "$inc": {
                "total_duels": 1,
                "wins": 1 if score_result == 1.0 else 0,
                "losses": 1 if score_result == 0.0 else 0
            }
        }
    )
    
    users_col.update_one(
        {"_id": match["player_b_id"]},
        {
            "$set": {
                "elo_rating": new_elo_b,
                "league": ELOCalculator.get_league(new_elo_b)
            },
            "$inc": {
                "total_duels": 1,
                "wins": 1 if score_result == 0.0 else 0,
                "losses": 1 if score_result == 1.0 else 0
            }
        }
    )
    
    # Update match
    matches_col.update_one(
        {"_id": ObjectId(match_id)},
        {
            "$set": {
                "status": "finished",
                "ended_at": datetime.utcnow(),
                "winner_id": winner_id,
                "elo_delta_a": delta_a,
                "elo_delta_b": delta_b
            }
        }
    )
    
    # Notify both players
    await manager.broadcast_to_match(match_id, {
        "type": "match_finished",
        "winner_id": str(winner_id) if winner_id else None,
        "score_a": score_a,
        "score_b": score_b,
        "elo_delta_a": delta_a,
        "elo_delta_b": delta_b,
        "new_elo_a": new_elo_a,
        "new_elo_b": new_elo_b
    })


# ============================================================================
# LEADERBOARDS
# ============================================================================

@app.get("/api/leaderboards/global")
async def get_global_leaderboard(limit: int = 50):
    """Get global leaderboard by ELO"""
    users = list(users_col.find(
        {},
        {
            "display_name": 1,
            "country_code": 1,
            "elo_rating": 1,
            "league": 1,
            "wins": 1,
            "losses": 1,
            "total_duels": 1
        }
    ).sort("elo_rating", DESCENDING).limit(limit))
    
    entries = []
    for rank, user in enumerate(users, 1):
        entries.append({
            "rank": rank,
            "user_id": str(user["_id"]),
            "display_name": user["display_name"],
            "country_code": user["country_code"],
            "elo_rating": user["elo_rating"],
            "league": user["league"],
            "wins": user.get("wins", 0),
            "losses": user.get("losses", 0),
            "total_duels": user.get("total_duels", 0)
        })
    
    return {"type": "global", "entries": entries}


@app.get("/api/leaderboards/weekly")
async def get_weekly_leaderboard(limit: int = 50):
    """Get weekly leaderboard (ELO change this week)"""
    # For MVP, return global leaderboard
    # In production, track weekly ELO changes
    return await get_global_leaderboard(limit)


# ============================================================================
# PAYMENTS (STRIPE)
# ============================================================================

@app.post("/api/payments/checkout")
async def create_checkout(checkout_data: CheckoutRequest, current_user: dict = Depends(get_current_user)):
    """Create Stripe checkout session"""
    # Product definitions
    PRODUCTS = {
        "premium_subscription": {"amount": 3.99, "currency": "usd"},
        "consumable_100": {"amount": 2.50, "currency": "usd"}
    }
    
    if checkout_data.product_type not in PRODUCTS:
        raise HTTPException(status_code=400, detail="Invalid product type")
    
    product = PRODUCTS[checkout_data.product_type]
    
    # Initialize Stripe
    webhook_url = f"{checkout_data.origin_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    # Build URLs
    success_url = f"{checkout_data.origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{checkout_data.origin_url}/payment/cancel"
    
    # Create checkout session
    request = CheckoutSessionRequest(
        amount=product["amount"],
        currency=product["currency"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "product_type": checkout_data.product_type,
            "user_id": current_user["id"]
        }
    )
    
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(request)
    
    # Store transaction
    payment_transactions_col.insert_one({
        "user_id": ObjectId(current_user["id"]),
        "session_id": session.session_id,
        "product_type": checkout_data.product_type,
        "amount": product["amount"],
        "currency": product["currency"],
        "status": "pending",
        "payment_status": "unpaid",
        "created_at": datetime.utcnow()
    })
    
    return {
        "checkout_url": session.url,
        "session_id": session.session_id
    }


@app.get("/api/payments/status/{session_id}")
async def get_payment_status(session_id: str, current_user: dict = Depends(get_current_user)):
    """Get payment status"""
    transaction = payment_transactions_col.find_one({
        "session_id": session_id,
        "user_id": ObjectId(current_user["id"])
    })
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check with Stripe
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
    status = await stripe_checkout.get_checkout_status(session_id)
    
    # Update transaction if status changed
    if status.payment_status == "paid" and transaction["payment_status"] != "paid":
        # Mark as paid
        payment_transactions_col.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "paid", "status": "completed", "updated_at": datetime.utcnow()}}
        )
        
        # Apply benefits
        product_type = transaction["product_type"]
        
        if product_type == "premium_subscription":
            # Activate premium for 1 month
            users_col.update_one(
                {"_id": ObjectId(current_user["id"])},
                {"$set": {
                    "premium_status": True,
                    "premium_expiration": datetime.utcnow() + timedelta(days=30)
                }}
            )
        
        elif product_type == "consumable_100":
            # Add 100 duels
            current_month = datetime.utcnow().strftime("%Y-%m")
            duel_counters_col.update_one(
                {"user_id": ObjectId(current_user["id"]), "month": current_month},
                {"$inc": {"consumable_extra_100": 1}, "$set": {"updated_at": datetime.utcnow()}},
                upsert=True
            )
    
    return {
        "status": status.status,
        "payment_status": status.payment_status,
        "product_type": transaction["product_type"]
    }


@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Handle event
        if webhook_response.event_type in ["checkout.session.completed", "invoice.paid"]:
            session_id = webhook_response.session_id
            metadata = webhook_response.metadata
            
            # Update transaction
            payment_transactions_col.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "paid", "status": "completed", "updated_at": datetime.utcnow()}}
            )
            
            # Apply benefits
            user_id = metadata.get("user_id")
            product_type = metadata.get("product_type")
            
            if user_id and product_type == "premium_subscription":
                users_col.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {
                        "premium_status": True,
                        "premium_expiration": datetime.utcnow() + timedelta(days=30)
                    }}
                )
            
            elif user_id and product_type == "consumable_100":
                current_month = datetime.utcnow().strftime("%Y-%m")
                duel_counters_col.update_one(
                    {"user_id": ObjectId(user_id), "month": current_month},
                    {"$inc": {"consumable_extra_100": 1}, "$set": {"updated_at": datetime.utcnow()}},
                    upsert=True
                )
        
        return {"status": "success"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.post("/api/admin/coupons")
async def create_coupon(coupon_data: CouponCreate, current_user: dict = Depends(get_current_user)):
    """Create discount coupon (admin only)"""
    # TODO: Add admin role check
    
    coupon_doc = {
        "code": coupon_data.code.upper(),
        "discount_type": coupon_data.discount_type,
        "discount_value": coupon_data.discount_value,
        "max_uses": coupon_data.max_uses,
        "times_used": 0,
        "expiration": coupon_data.expiration,
        "active": True,
        "created_at": datetime.utcnow(),
        "created_by": ObjectId(current_user["id"])
    }
    
    result = coupons_col.insert_one(coupon_doc)
    coupon_doc["_id"] = result.inserted_id
    
    return {"coupon": serialize_doc(coupon_doc)}


@app.get("/api/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """Get admin statistics"""
    # TODO: Add admin role check
    
    total_users = users_col.count_documents({})
    total_matches = matches_col.count_documents({"status": "finished"})
    premium_users = users_col.count_documents({"premium_status": True})
    
    # Monthly duels
    current_month = datetime.utcnow().strftime("%Y-%m")
    monthly_duels = duel_counters_col.aggregate([
        {"$match": {"month": current_month}},
        {"$group": {"_id": None, "total": {"$sum": "$duels_used"}}}
    ])
    monthly_duels_count = list(monthly_duels)
    
    return {
        "total_users": total_users,
        "total_matches": total_matches,
        "premium_users": premium_users,
        "monthly_duels": monthly_duels_count[0]["total"] if monthly_duels_count else 0
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Knowledge Wars API"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
