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
user_sessions_col = db["user_sessions"]  # For Google OAuth sessions
password_resets_col = db["password_resets"]  # For password recovery
admin_users_col = db["admin_users"]  # Admin panel users

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
password_resets_col.create_index("token", unique=True)
password_resets_col.create_index("email")
password_resets_col.create_index("expires_at")
coupons_col.create_index("code", unique=True)

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
    # First try Authorization header (JWT)
    if authorization:
        try:
            token = authorization.replace("Bearer ", "")
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
                try:
                    user = users_col.find_one({"_id": ObjectId(session["user_id"])})
                except:
                    pass
            if user:
                return serialize_doc(user)
    
    raise HTTPException(status_code=401, detail="Not authenticated")


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
    
    # Create user with game credits system
    # New users start with 5 FREE games to try the app
    user_doc = {
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "display_name": user_data.display_name,
        "country_code": user_data.country_code,
        "favorite_topic": user_data.favorite_topic,
        "language": user_data.language,
        "dnd_enabled": False,
        "elo_rating": 500,
        "league": "plata",
        "created_at": datetime.utcnow(),
        "last_seen": datetime.utcnow(),
        "wins": 0,
        "losses": 0,
        "total_duels": 0,
        "auth_provider": "email",
        # New monetization system: game credits
        "games_remaining": 5,  # 5 free games for new users
        "total_games_purchased": 0,
        "coupons_used": []  # Track used coupons
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
        async with httpx.AsyncClient() as http_client:
            auth_response = await http_client.get(
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
            # Create new user from Google data with game credits
            user_doc = {
                "email": email,
                "display_name": name.split()[0] if name else "Player",
                "google_picture": picture,
                "country_code": "us",  # Default, user can change later
                "favorite_topic": "General Knowledge",
                "language": "es",
                "dnd_enabled": False,
                "elo_rating": 500,
                "league": "plata",
                "created_at": datetime.now(timezone.utc),
                "last_seen": datetime.now(timezone.utc),
                "wins": 0,
                "losses": 0,
                "total_duels": 0,
                "auth_provider": "google",
                # New monetization system: game credits
                "games_remaining": 5,  # 5 free games for new users
                "total_games_purchased": 0,
                "coupons_used": []
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
# PASSWORD RECOVERY ENDPOINTS
# ============================================================================

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

@app.post("/api/auth/forgot-password")
async def forgot_password(data: PasswordResetRequest):
    """Request password reset - generates a reset token"""
    user = users_col.find_one({"email": data.email})
    
    if not user:
        # Don't reveal if email exists or not for security
        return {"success": True, "message": "Si el email existe, recibirás instrucciones"}
    
    # Check if user uses Google auth (no password to reset)
    if user.get("auth_provider") == "google" and not user.get("password"):
        return {"success": True, "message": "Esta cuenta usa Google Sign-In. Por favor inicia sesión con Google."}
    
    # Delete any existing reset tokens for this email
    password_resets_col.delete_many({"email": data.email})
    
    # Generate reset token (6-digit code for simplicity)
    import random
    reset_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    reset_token = f"reset_{uuid.uuid4().hex}"
    
    # Store reset token (expires in 15 minutes)
    password_resets_col.insert_one({
        "email": data.email,
        "token": reset_token,
        "code": reset_code,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
        "created_at": datetime.now(timezone.utc),
        "used": False
    })
    
    # In production, you would send an email here with the code
    # For now, we'll return the code in the response (REMOVE IN PRODUCTION)
    return {
        "success": True,
        "message": "Código de recuperación enviado",
        "reset_token": reset_token,
        # NOTA: En producción, NO devolver el código - enviarlo por email
        "_dev_code": reset_code  # Solo para desarrollo
    }

@app.post("/api/auth/verify-reset-code")
async def verify_reset_code(email: str, code: str):
    """Verify the reset code and return the reset token"""
    reset_doc = password_resets_col.find_one({
        "email": email,
        "code": code,
        "used": False
    })
    
    if not reset_doc:
        raise HTTPException(status_code=400, detail="Código inválido o expirado")
    
    # Check expiry
    expires_at = reset_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="El código ha expirado")
    
    return {"success": True, "reset_token": reset_doc["token"]}

@app.post("/api/auth/reset-password")
async def reset_password(data: PasswordResetConfirm):
    """Reset password using the reset token"""
    reset_doc = password_resets_col.find_one({
        "token": data.token,
        "used": False
    })
    
    if not reset_doc:
        raise HTTPException(status_code=400, detail="Token inválido o ya usado")
    
    # Check expiry
    expires_at = reset_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="El token ha expirado")
    
    # Validate new password
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    
    # Update password
    users_col.update_one(
        {"email": reset_doc["email"]},
        {"$set": {"password": hash_password(data.new_password)}}
    )
    
    # Mark token as used
    password_resets_col.update_one(
        {"token": data.token},
        {"$set": {"used": True}}
    )
    
    return {"success": True, "message": "Contraseña actualizada exitosamente"}


# ============================================================================
# GAME CREDITS & COUPONS SYSTEM
# ============================================================================

class CouponCreateRequest(BaseModel):
    code: str
    coupon_type: str  # "discount" or "free_games"
    value: int  # For discount: percentage (10-100), for free_games: number of games
    max_uses: int = 100
    expiration_days: int = 30
    description: str = ""

class CouponRedeemRequest(BaseModel):
    code: str

@app.get("/api/users/credits")
async def get_user_credits(current_user: dict = Depends(get_current_user)):
    """Get current user's game credits status"""
    user = users_col.find_one({"_id": ObjectId(current_user["id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    games_remaining = user.get("games_remaining", 0)
    
    return {
        "games_remaining": games_remaining,
        "total_games_purchased": user.get("total_games_purchased", 0),
        "low_credits_warning": games_remaining <= 5,
        "no_credits": games_remaining <= 0
    }

@app.post("/api/coupons/redeem")
async def redeem_coupon(data: CouponRedeemRequest, current_user: dict = Depends(get_current_user)):
    """Redeem a coupon for free games or discount"""
    code = data.code.upper().strip()
    
    # Find coupon
    coupon = coupons_col.find_one({"code": code})
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")
    
    # Check if coupon is active
    if not coupon.get("active", True):
        raise HTTPException(status_code=400, detail="Este cupón ya no está activo")
    
    # Check expiration
    if coupon.get("expires_at"):
        expires_at = coupon["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Este cupón ha expirado")
    
    # Check max uses
    if coupon.get("uses", 0) >= coupon.get("max_uses", 100):
        raise HTTPException(status_code=400, detail="Este cupón ha alcanzado su límite de usos")
    
    # Check if user already used this coupon
    user = users_col.find_one({"_id": ObjectId(current_user["id"])})
    used_coupons = user.get("coupons_used", [])
    if code in used_coupons:
        raise HTTPException(status_code=400, detail="Ya has usado este cupón")
    
    # Process coupon based on type
    coupon_type = coupon.get("coupon_type", "free_games")
    value = coupon.get("value", 0)
    
    result = {"success": True, "coupon_type": coupon_type}
    
    if coupon_type == "free_games":
        # Add free games to user account
        users_col.update_one(
            {"_id": ObjectId(current_user["id"])},
            {
                "$inc": {"games_remaining": value},
                "$push": {"coupons_used": code}
            }
        )
        result["games_added"] = value
        result["message"] = f"¡{value} partidas gratis añadidas a tu cuenta!"
    
    elif coupon_type == "discount":
        # Store discount for next purchase
        # The discount will be applied at checkout
        users_col.update_one(
            {"_id": ObjectId(current_user["id"])},
            {
                "$set": {"pending_discount": {"code": code, "percentage": value}},
                "$push": {"coupons_used": code}
            }
        )
        result["discount_percentage"] = value
        result["message"] = f"¡Descuento del {value}% aplicado a tu próxima compra!"
    
    # Increment coupon usage
    coupons_col.update_one(
        {"code": code},
        {"$inc": {"uses": 1}}
    )
    
    # Get updated user credits
    updated_user = users_col.find_one({"_id": ObjectId(current_user["id"])})
    result["games_remaining"] = updated_user.get("games_remaining", 0)
    
    return result

@app.post("/api/games/purchase")
async def purchase_games(current_user: dict = Depends(get_current_user)):
    """
    Purchase 50 games for $99 MXN
    This creates a checkout session for payment
    """
    user = users_col.find_one({"_id": ObjectId(current_user["id"])})
    
    # Check for pending discount
    pending_discount = user.get("pending_discount")
    
    # Calculate price
    base_price = 9900  # $99 MXN in centavos
    final_price = base_price
    discount_applied = None
    
    if pending_discount:
        discount_pct = pending_discount.get("percentage", 0)
        final_price = int(base_price * (100 - discount_pct) / 100)
        discount_applied = {
            "code": pending_discount.get("code"),
            "percentage": discount_pct,
            "savings": base_price - final_price
        }
    
    # Create purchase record
    purchase_id = str(uuid.uuid4())
    purchases_col.insert_one({
        "purchase_id": purchase_id,
        "user_id": str(current_user["id"]),
        "product": "50_games",
        "games_quantity": 50,
        "base_price": base_price,
        "final_price": final_price,
        "discount_applied": discount_applied,
        "status": "pending",
        "created_at": datetime.now(timezone.utc)
    })
    
    return {
        "success": True,
        "purchase_id": purchase_id,
        "product": "50 Partidas",
        "base_price_mxn": base_price / 100,
        "final_price_mxn": final_price / 100,
        "discount_applied": discount_applied,
        "message": "Redirigiendo a pago..."
    }

@app.post("/api/games/confirm-purchase/{purchase_id}")
async def confirm_purchase(purchase_id: str, current_user: dict = Depends(get_current_user)):
    """
    Confirm a purchase and add games to user account
    In production, this would be called by payment webhook
    """
    purchase = purchases_col.find_one({
        "purchase_id": purchase_id,
        "user_id": str(current_user["id"]),
        "status": "pending"
    })
    
    if not purchase:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    
    games_to_add = purchase.get("games_quantity", 50)
    
    # Add games to user account
    users_col.update_one(
        {"_id": ObjectId(current_user["id"])},
        {
            "$inc": {
                "games_remaining": games_to_add,
                "total_games_purchased": games_to_add
            },
            "$unset": {"pending_discount": ""}  # Clear used discount
        }
    )
    
    # Update purchase status
    purchases_col.update_one(
        {"purchase_id": purchase_id},
        {"$set": {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc)
        }}
    )
    
    # Get updated user
    updated_user = users_col.find_one({"_id": ObjectId(current_user["id"])})
    
    return {
        "success": True,
        "message": f"¡{games_to_add} partidas añadidas a tu cuenta!",
        "games_remaining": updated_user.get("games_remaining", 0)
    }

@app.post("/api/games/use-credit")
async def use_game_credit(current_user: dict = Depends(get_current_user)):
    """
    Use one game credit when starting a match
    Returns whether user can play
    """
    user = users_col.find_one({"_id": ObjectId(current_user["id"])})
    games_remaining = user.get("games_remaining", 0)
    
    if games_remaining <= 0:
        return {
            "success": False,
            "can_play": False,
            "message": "No tienes partidas disponibles. ¡Compra más para seguir jugando!",
            "games_remaining": 0
        }
    
    # Deduct one game credit
    users_col.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$inc": {"games_remaining": -1}}
    )
    
    new_remaining = games_remaining - 1
    
    response = {
        "success": True,
        "can_play": True,
        "games_remaining": new_remaining
    }
    
    # Warning when low on credits
    if new_remaining <= 5 and new_remaining > 0:
        response["warning"] = f"¡Te quedan solo {new_remaining} partidas! Compra más para seguir jugando."
    elif new_remaining == 0:
        response["warning"] = "¡Esta es tu última partida! Compra más para seguir jugando."
    
    return response


# ============================================================================
# ADMIN ENDPOINTS (Coupon Management)
# ============================================================================

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "knowledge-wars-admin-2024")

async def verify_admin(authorization: Optional[str] = Header(None)):
    """Verify admin access"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    
    token = authorization.replace("Bearer ", "")
    if token != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin credentials")
    
    return True

@app.post("/api/admin/coupons/create")
async def create_coupon(coupon: CouponCreateRequest, admin: bool = Depends(verify_admin)):
    """Create a new coupon (Admin only)"""
    code = coupon.code.upper().strip()
    
    # Check if code already exists
    existing = coupons_col.find_one({"code": code})
    if existing:
        raise HTTPException(status_code=400, detail="Este código de cupón ya existe")
    
    # Validate coupon type
    if coupon.coupon_type not in ["discount", "free_games"]:
        raise HTTPException(status_code=400, detail="Tipo de cupón inválido")
    
    # Validate value
    if coupon.coupon_type == "discount" and (coupon.value < 1 or coupon.value > 100):
        raise HTTPException(status_code=400, detail="El descuento debe ser entre 1% y 100%")
    
    if coupon.coupon_type == "free_games" and coupon.value < 1:
        raise HTTPException(status_code=400, detail="El número de partidas gratis debe ser mayor a 0")
    
    # Create coupon
    coupon_doc = {
        "code": code,
        "coupon_type": coupon.coupon_type,
        "value": coupon.value,
        "max_uses": coupon.max_uses,
        "uses": 0,
        "description": coupon.description,
        "active": True,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=coupon.expiration_days)
    }
    
    coupons_col.insert_one(coupon_doc)
    
    return {
        "success": True,
        "message": "Cupón creado exitosamente",
        "coupon": {
            "code": code,
            "type": coupon.coupon_type,
            "value": coupon.value,
            "max_uses": coupon.max_uses,
            "expires_at": coupon_doc["expires_at"].isoformat()
        }
    }

@app.get("/api/admin/coupons")
async def list_coupons(admin: bool = Depends(verify_admin)):
    """List all coupons (Admin only)"""
    coupons = list(coupons_col.find({}, {"_id": 0}))
    return {"coupons": serialize_doc(coupons)}

@app.patch("/api/admin/coupons/{code}/toggle")
async def toggle_coupon(code: str, admin: bool = Depends(verify_admin)):
    """Toggle coupon active status (Admin only)"""
    code = code.upper().strip()
    coupon = coupons_col.find_one({"code": code})
    
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")
    
    new_status = not coupon.get("active", True)
    coupons_col.update_one(
        {"code": code},
        {"$set": {"active": new_status}}
    )
    
    return {
        "success": True,
        "code": code,
        "active": new_status
    }

@app.delete("/api/admin/coupons/{code}")
async def delete_coupon(code: str, admin: bool = Depends(verify_admin)):
    """Delete a coupon (Admin only)"""
    code = code.upper().strip()
    result = coupons_col.delete_one({"code": code})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")
    
    return {"success": True, "message": "Cupón eliminado"}

@app.get("/api/admin/stats")
async def get_admin_stats(admin: bool = Depends(verify_admin)):
    """Get admin dashboard stats"""
    total_users = users_col.count_documents({})
    total_matches = matches_col.count_documents({})
    total_purchases = purchases_col.count_documents({"status": "completed"})
    active_coupons = coupons_col.count_documents({"active": True})
    
    # Revenue calculation
    completed_purchases = list(purchases_col.find({"status": "completed"}))
    total_revenue = sum(p.get("final_price", 0) for p in completed_purchases)
    
    # Games distributed
    total_games_given = sum(p.get("games_quantity", 0) for p in completed_purchases)
    
    return {
        "total_users": total_users,
        "total_matches": total_matches,
        "total_purchases": total_purchases,
        "total_revenue_mxn": total_revenue / 100,
        "total_games_distributed": total_games_given,
        "active_coupons": active_coupons
    }


# ============================================================================
# USER ENDPOINTS
# ============================================================================

@app.get("/api/users/online")
async def get_online_users(current_user: dict = Depends(get_current_user)):
    """Get list of online users for matchmaking (filtered by same tier)"""
    # Consider users online if they've been active in the last 5 minutes
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
    
    # Update current user's last_seen timestamp
    users_col.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": {"last_seen": datetime.utcnow()}}
    )
    
    # Get current user's ELO tier range for matchmaking
    current_elo = current_user.get("elo_rating", 500)
    tier_min, tier_max = ELOCalculator.get_tier_range(current_elo)
    
    # Find recently active users in the same tier (excluding current user and DND users)
    users = users_col.find(
        {
            "_id": {"$ne": ObjectId(current_user["id"])},
            "dnd_enabled": False,
            "last_seen": {"$gte": five_minutes_ago},
            "elo_rating": {"$gte": tier_min, "$lte": tier_max}
        },
        {
            "display_name": 1,
            "country_code": 1,
            "elo_rating": 1,
            "league": 1,
            "rank_name": 1,
            "favorite_topic": 1,
            "last_seen": 1
        }
    ).sort("last_seen", DESCENDING).limit(50)
    
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
        {"$match": {"usage_count": {"$gt": 0}}},  # Only topics that have been actually used
        {"$group": {"_id": "$topic", "count": {"$sum": "$usage_count"}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    result = list(question_sets_col.aggregate(pipeline))
    topics = [{"topic": doc["_id"], "count": doc["count"]} for doc in result]
    
    # If we have less than 10, add predefined topics but mark them as suggestions
    if len(topics) < 10:
        predefined = ["General Knowledge", "Sports", "History", "Geography", "Science", 
                      "Technology", "Movies/TV", "Music", "Business/Finance", "Gaming"]
        
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
    """Create a new match challenge - NO credit deduction here, only when match starts"""
    
    # Check if user has credits (but don't deduct yet)
    user = users_col.find_one({"_id": ObjectId(current_user["id"])})
    if user.get("games_remaining", 0) <= 0:
        raise HTTPException(status_code=403, detail="No tienes partidas disponibles. Compra más en la tienda.")
    
    # Check opponent exists and is not in DND
    opponent = users_col.find_one({"_id": ObjectId(match_data.opponent_id)})
    if not opponent:
        raise HTTPException(status_code=404, detail="Opponent not found")
    
    if opponent.get("dnd_enabled"):
        raise HTTPException(status_code=400, detail="Opponent is in Do Not Disturb mode")
    
    # Check opponent has credits too
    if opponent.get("games_remaining", 0) <= 0:
        raise HTTPException(status_code=400, detail="El oponente no tiene partidas disponibles")
    
    # Generate questions
    try:
        question_set = await question_generator.generate_questions(match_data.topic, match_data.language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")
    
    # Create match with pending status
    match_doc = {
        "player_a_id": ObjectId(current_user["id"]),
        "player_b_id": ObjectId(match_data.opponent_id),
        "player_a_name": current_user["display_name"],
        "player_b_name": opponent["display_name"],
        "player_a_country": current_user.get("country_code", "us"),
        "player_b_country": opponent.get("country_code", "us"),
        "topic": match_data.topic,
        "language": match_data.language,
        "questions": question_set["questions"],
        "score_a": 0,
        "score_b": 0,
        "current_question": 0,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=2),  # Challenge expires in 2 minutes
        "started_at": None,
        "ended_at": None,
        "winner_id": None,
        "elo_delta_a": 0,
        "elo_delta_b": 0,
        "credits_deducted": False  # Track if credits were deducted
    }
    
    result = matches_col.insert_one(match_doc)
    match_doc["_id"] = result.inserted_id
    
    # Send challenge notification to opponent via WebSocket
    await manager.send_message(match_data.opponent_id, {
        "type": "challenge_received",
        "match": serialize_doc(match_doc),
        "challenger": {
            "id": current_user["id"],
            "display_name": current_user["display_name"],
            "country_code": current_user.get("country_code", "us"),
            "elo_rating": current_user.get("elo_rating", 1200)
        }
    })
    
    return {"match": serialize_doc(match_doc), "message": "Desafío enviado. Esperando respuesta..."}


@app.post("/api/matches/{match_id}/accept")
async def accept_match(match_id: str, current_user: dict = Depends(get_current_user)):
    """Accept a match challenge - THIS is when credits are deducted"""
    match = matches_col.find_one({"_id": ObjectId(match_id)})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if str(match["player_b_id"]) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if match["status"] != "pending":
        raise HTTPException(status_code=400, detail="Match already started or finished")
    
    # Check if challenge expired
    expires_at = match.get("expires_at")
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at < datetime.utcnow():
            matches_col.update_one(
                {"_id": ObjectId(match_id)},
                {"$set": {"status": "expired"}}
            )
            raise HTTPException(status_code=400, detail="El desafío ha expirado")
    
    # Check both players have credits
    player_a = users_col.find_one({"_id": match["player_a_id"]})
    player_b = users_col.find_one({"_id": ObjectId(current_user["id"])})
    
    if player_a.get("games_remaining", 0) <= 0:
        raise HTTPException(status_code=400, detail="El retador ya no tiene partidas disponibles")
    
    if player_b.get("games_remaining", 0) <= 0:
        raise HTTPException(status_code=403, detail="No tienes partidas disponibles")
    
    # NOW deduct credits from both players
    users_col.update_one(
        {"_id": match["player_a_id"]},
        {"$inc": {"games_remaining": -1}}
    )
    users_col.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$inc": {"games_remaining": -1}}
    )
    
    # Update match status
    matches_col.update_one(
        {"_id": ObjectId(match_id)},
        {"$set": {
            "status": "active", 
            "started_at": datetime.utcnow(),
            "credits_deducted": True
        }}
    )
    
    # Notify challenger that match was accepted
    await manager.send_message(str(match["player_a_id"]), {
        "type": "challenge_accepted",
        "match_id": match_id,
        "message": f"{current_user['display_name']} aceptó tu desafío!"
    })
    
    # Notify both players to start the match
    await manager.broadcast_to_match(match_id, {
        "type": "match_started",
        "match_id": match_id
    })
    
    return {"success": True, "match_id": match_id, "message": "¡Partida iniciada!"}


@app.post("/api/matches/{match_id}/reject")
async def reject_match(match_id: str, current_user: dict = Depends(get_current_user)):
    """Reject a match challenge - NO credits are deducted"""
    match = matches_col.find_one({"_id": ObjectId(match_id)})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if str(match["player_b_id"]) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if match["status"] != "pending":
        raise HTTPException(status_code=400, detail="Match cannot be rejected")
    
    # Update match status
    matches_col.update_one(
        {"_id": ObjectId(match_id)},
        {"$set": {"status": "rejected", "ended_at": datetime.utcnow()}}
    )
    
    # Notify challenger that match was rejected
    await manager.send_message(str(match["player_a_id"]), {
        "type": "challenge_rejected",
        "match_id": match_id,
        "message": f"{current_user['display_name']} rechazó tu desafío"
    })
    
    return {"success": True}


@app.post("/api/matches/{match_id}/cancel")
async def cancel_match(match_id: str, current_user: dict = Depends(get_current_user)):
    """Cancel a pending match challenge (by the challenger)"""
    match = matches_col.find_one({"_id": ObjectId(match_id)})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Only the challenger can cancel
    if str(match["player_a_id"]) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if match["status"] != "pending":
        raise HTTPException(status_code=400, detail="Solo se pueden cancelar desafíos pendientes")
    
    # Update match status
    matches_col.update_one(
        {"_id": ObjectId(match_id)},
        {"$set": {"status": "cancelled", "ended_at": datetime.utcnow()}}
    )
    
    # Notify opponent
    await manager.send_message(str(match["player_b_id"]), {
        "type": "challenge_cancelled",
        "match_id": match_id,
        "message": f"{current_user['display_name']} canceló el desafío"
    })
    
    return {"success": True, "message": "Desafío cancelado"}


@app.get("/api/matches/pending")
async def get_pending_matches(current_user: dict = Depends(get_current_user)):
    """Get pending match challenges for current user - excludes expired ones"""
    now = datetime.utcnow()
    
    # First, mark expired matches
    matches_col.update_many(
        {
            "status": "pending",
            "expires_at": {"$lt": now}
        },
        {"$set": {"status": "expired"}}
    )
    
    # Get non-expired pending matches
    matches = list(matches_col.find(
        {
            "player_b_id": ObjectId(current_user["id"]),
            "status": "pending",
            "$or": [
                {"expires_at": {"$gte": now}},
                {"expires_at": {"$exists": False}}
            ]
        },
        {
            "player_a_id": 1,
            "player_a_name": 1,
            "player_a_country": 1,
            "topic": 1,
            "language": 1,
            "created_at": 1,
            "expires_at": 1
        }
    ).sort("created_at", DESCENDING).limit(10))
    
    return {"matches": serialize_doc(matches)}


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


@app.websocket("/ws/notify/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: str, token: str):
    """WebSocket endpoint for real-time notifications (challenges, match updates, etc.)"""
    # Authenticate
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    # Verify user_id matches token
    if payload["user_id"] != user_id:
        await websocket.close(code=1008, reason="User ID mismatch")
        return
    
    await manager.connect(user_id, websocket)
    print(f"🔔 User {user_id} connected for notifications")
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to notification service"
        })
        
        # Keep connection alive and listen for any messages
        while True:
            try:
                data = await websocket.receive_json()
                # Handle any client-side messages if needed
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except Exception:
                # If receive fails, just continue (might be a disconnect)
                break
    
    except WebSocketDisconnect:
        print(f"🔔 User {user_id} disconnected from notifications")
        manager.disconnect(user_id)
    except Exception as e:
        print(f"Notification WebSocket error for user {user_id}: {e}")
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
    }).limit(1))
    
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
    existing = match_events_col.find_one(
        {
            "match_id": ObjectId(match_id),
            "user_id": ObjectId(user_id),
            "question_index": question_index,
            "event_type": "hint_requested"
        },
        {"_id": 1}
    )
    
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
    player_a_won = False
    player_b_won = False
    is_draw = False
    
    if score_a > score_b:
        winner_id = match["player_a_id"]
        player_a_won = True
    elif score_b > score_a:
        winner_id = match["player_b_id"]
        player_b_won = True
    else:
        is_draw = True
    
    # Get current ELO ratings
    user_a = users_col.find_one({"_id": match["player_a_id"]})
    user_b = users_col.find_one({"_id": match["player_b_id"]})
    
    elo_a = user_a["elo_rating"]
    elo_b = user_b["elo_rating"]
    
    # Calculate ELO changes using new system (+2 win, -1 loss, 0 draw)
    if is_draw:
        delta_a = 0
        delta_b = 0
    else:
        delta_a = ELOCalculator.calculate_elo_change(player_a_won)
        delta_b = ELOCalculator.calculate_elo_change(player_b_won)
    
    new_elo_a = max(0, elo_a + delta_a)  # Don't go below 0
    new_elo_b = max(0, elo_b + delta_b)
    
    # Get rank info for both players
    rank_info_a = ELOCalculator.get_rank(new_elo_a)
    rank_info_b = ELOCalculator.get_rank(new_elo_b)
    
    # Update users
    users_col.update_one(
        {"_id": match["player_a_id"]},
        {
            "$set": {
                "elo_rating": new_elo_a,
                "league": rank_info_a['tier'],
                "rank_name": rank_info_a['name']
            },
            "$inc": {
                "total_duels": 1,
                "wins": 1 if player_a_won else 0,
                "losses": 1 if player_b_won else 0
            }
        }
    )
    
    users_col.update_one(
        {"_id": match["player_b_id"]},
        {
            "$set": {
                "elo_rating": new_elo_b,
                "league": rank_info_b['tier'],
                "rank_name": rank_info_b['name']
            },
            "$inc": {
                "total_duels": 1,
                "wins": 1 if player_b_won else 0,
                "losses": 1 if player_a_won else 0
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


@app.delete("/api/admin/test-data")
async def clear_test_data(current_user: dict = Depends(get_current_user)):
    """Clear test data from POC phase"""
    # TODO: Add admin role check
    
    # Delete question sets with usage_count = 0 (never used in real matches)
    result_questions = question_sets_col.delete_many({"usage_count": 0})
    
    # Delete test users (you can add specific criteria if needed)
    # For now, we'll just report counts
    
    return {
        "deleted_question_sets": result_questions.deleted_count,
        "message": "Test data cleared successfully"
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def root_health_check():
    """Root health check endpoint for Kubernetes probes"""
    return {"status": "ok"}


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
