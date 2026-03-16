""" 
Knowledge Wars - Main Server
FastAPI backend with WebSocket support for real-time duels
"""

import os
import asyncio
import httpx
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header, Request, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from pydantic import BaseModel

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
DB_NAME = os.getenv("DB_NAME")
if not DB_NAME:
    raise ValueError("DB_NAME environment variable is required")
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
user_sessions_col = db["user_sessions"]  # New collection for Google OAuth sessions

# Indexes
users_col.create_index("email", unique=True)
users_col.create_index("elo_rating")
users_col.create_index([("dnd_enabled", 1)])
users_col.create_index([("last_seen", DESCENDING)])
matches_col.create_index([("created_at", DESCENDING)])
matches_col.create_index([("player_a_id", 1), ("status", 1)])
matches_col.create_index([("player_b_id", 1), ("status", 1)])
matches_col.create_index([("status", 1), ("ended_at", DESCENDING)])
question_sets_col.create_index([("topic_normalized", 1), ("language", 1)])
match_events_col.create_index([("match_id", 1), ("question_index", 1), ("event_type", 1)])
user_sessions_col.create_index("session_token", unique=True)
user_sessions_col.create_index("user_id")

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
async def get_current_user(
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None)
) -> dict:
    """Get current authenticated user - supports both JWT and session cookie"""
    token = None
    
    # First try Authorization header (JWT)
    if authorization:
        token = authorization.replace("Bearer ", "")
        try:
            payload = decode_access_token(token)
            if payload:
                user = users_col.find_one({"_id": ObjectId(payload["user_id"])})
                if user:
                    return serialize_doc(user)
        except:
            pass
    
    # Then try session cookie (Google OAuth)
    if session_token:
        session = user_sessions_col.find_one({"session_token": session_token}, {"_id": 0})
        if session:
            # Check expiry with timezone awareness
            expires_at = session.get("expires_at")
            if expires_at:
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < datetime.now(timezone.utc):
                    raise HTTPException(status_code=401, detail="Session expired")
            
            # Find user by user_id field
            user = users_col.find_one({"user_id": session["user_id"]}, {"_id": 0})
            if not user:
                # Also try finding by MongoDB _id for backward compatibility
                user = users_col.find_one({"_id": ObjectId(session["user_id"])})
            if user:
                return serialize_doc(user)
    
    raise HTTPException(status_code=401, detail="Not authenticated")


# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@app.post("/api/auth/register")
async def register(user_data: UserCreate, response: Response):
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
        "last_seen": datetime.utcnow(),
        "wins": 0,
        "losses": 0,
        "total_duels": 0,
        "auth_provider": "email"  # Track auth provider
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
async def login(credentials: UserLogin, response: Response):
    """Login user"""
    user = users_col.find_one({"email": credentials.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if user registered with Google (no password)
    if not user.get("password"):
        raise HTTPException(status_code=400, detail="Please use Google sign-in for this account")
    
    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Update last_seen on login
    users_col.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_seen": datetime.utcnow()}}
    )
    
    token = create_access_token({"user_id": str(user["_id"])})
    
    return {
        "token": token,
        "user": serialize_doc(user)
    }


# ============================================================================
# GOOGLE OAUTH ENDPOINTS (Emergent Auth)
# ============================================================================

class GoogleSessionRequest(BaseModel):
    session_id: str
    remember_me: bool = False


@app.post("/api/auth/google/session")
async def process_google_session(data: GoogleSessionRequest, response: Response):
    """
    Process Google OAuth session from Emergent Auth.
    Exchange session_id for user data and create local session.
    """
    try:
        # Call Emergent Auth to get session data
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": data.session_id},
                timeout=10.0
            )
        
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        google_data = auth_response.json()
        email = google_data.get("email")
        name = google_data.get("name", "Player")
        picture = google_data.get("picture", "")
        emergent_session_token = google_data.get("session_token")
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        
        # Find or create user
        user = users_col.find_one({"email": email})
        
        if user:
            # Update existing user with Google info
            users_col.update_one(
                {"_id": user["_id"]},
                {"$set": {
                    "last_seen": datetime.utcnow(),
                    "google_picture": picture,
                    "auth_provider": user.get("auth_provider", "google")
                }}
            )
            user_id = str(user["_id"])
        else:
            # Create new user from Google data
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            user_doc = {
                "user_id": user_id,
                "email": email,
                "display_name": name.split()[0] if name else "Player",
                "google_picture": picture,
                "country_code": "us",  # Default, user can change later
                "favorite_topic": "General Knowledge",
                "language": "es",
                "dnd_enabled": False,
                "elo_rating": 1200,
                "league": "plata",
                "premium_status": False,
                "premium_expiration": None,
                "created_at": datetime.now(timezone.utc),
                "last_seen": datetime.now(timezone.utc),
                "wins": 0,
                "losses": 0,
                "total_duels": 0,
                "auth_provider": "google"
            }
            result = users_col.insert_one(user_doc)
            user = user_doc
            user["_id"] = result.inserted_id
            user_id = str(result.inserted_id)
        
        # Create local session with appropriate expiry
        local_session_token = f"kw_{uuid.uuid4().hex}"
        
        # If remember_me is True, session lasts forever (100 years)
        # Otherwise, use standard 7 days
        if data.remember_me:
            expires_at = datetime.now(timezone.utc) + timedelta(days=36500)  # ~100 years
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        user_sessions_col.insert_one({
            "user_id": user_id,
            "session_token": local_session_token,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
            "remember_me": data.remember_me
        })
        
        # Set session cookie
        response.set_cookie(
            key="session_token",
            value=local_session_token,
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
            max_age=int((expires_at - datetime.now(timezone.utc)).total_seconds())
        )
        
        # Also return JWT token for backward compatibility
        jwt_token = create_access_token({"user_id": user_id})
        
        return {
            "success": True,
            "token": jwt_token,
            "user": serialize_doc(user)
        }
        
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify Google session: {str(e)}")


@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    # Update last_seen timestamp
    user_id = current_user.get("id") or current_user.get("user_id")
    if user_id:
        try:
            users_col.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_seen": datetime.utcnow()}}
            )
        except:
            # Try with user_id field for Google OAuth users
            users_col.update_one(
                {"user_id": user_id},
                {"$set": {"last_seen": datetime.utcnow()}}
            )
    return serialize_doc(current_user)


@app.post("/api/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """Logout user - clear session"""
    if session_token:
        user_sessions_col.delete_one({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"success": True}


# ============================================================================
# USER ENDPOINTS
# ============================================================================

@app.get("/api/users/online")
async def get_online_users(current_user: dict = Depends(get_current_user)):
    """Get list of online users for matchmaking (based on recent activity)"""
    # Consider users online if they've been active in the last 5 minutes
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
    
    # Get current user id
    current_user_id = current_user.get("id") or current_user.get("user_id")
    
    # Update current user's last_seen timestamp
    try:
        users_col.update_one(
            {"_id": ObjectId(current_user_id)},
            {"$set": {"last_seen": datetime.utcnow()}}
        )
    except:
        users_col.update_one(
            {"user_id": current_user_id},
            {"$set": {"last_seen": datetime.utcnow()}}
        )
    
    # Find recently active users (excluding current user and DND users)
    try:
        exclude_filter = {"_id": {"$ne": ObjectId(current_user_id)}}
    except:
        exclude_filter = {"user_id": {"$ne": current_user_id}}
    
    users = users_col.find(
        {
            **exclude_filter,
            "dnd_enabled": False,
            "last_seen": {"$gte": five_minutes_ago}
        },
        {
            "display_name": 1,
            "country_code": 1,
            "elo_rating": 1,
            "league": 1,
            "favorite_topic": 1,
            "last_seen": 1,
            "user_id": 1
        }
    ).sort("last_seen", DESCENDING).limit(50)
    
    return {"users": serialize_doc(list(users))}


@app.patch("/api/users/dnd")
async def toggle_dnd(enabled: bool, current_user: dict = Depends(get_current_user)):
    """Toggle Do Not Disturb mode"""
    user_id = current_user.get("id") or current_user.get("user_id")
    try:
        users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"dnd_enabled": enabled}}
        )
    except:
        users_col.update_one(
            {"user_id": user_id},
            {"$set": {"dnd_enabled": enabled}}
        )
    return {"success": True, "dnd_enabled": enabled}
