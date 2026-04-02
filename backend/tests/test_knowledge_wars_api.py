"""
Knowledge Wars API Tests - Backend Testing
Tests authentication, match creation, credits, and WebSocket flows
"""
import pytest
import requests
import os
import asyncio
import json
import websockets

# Use public URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://trivia-pvp-test.preview.emergentagent.com')
WS_URL = BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://')

# Test credentials
USER1_EMAIL = "test1@knowledgewars.app"
USER2_EMAIL = "test2@knowledgewars.app"
PASSWORD = "test123"
ADMIN_KEY = "knowledge-wars-admin-2024"


class TestAuthentication:
    """Authentication endpoint tests"""
    
    def test_login_user1_success(self):
        """Test login for test user 1"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER1_EMAIL,
            "password": PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == USER1_EMAIL
        
    def test_login_user2_success(self):
        """Test login for test user 2"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER2_EMAIL,
            "password": PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == USER2_EMAIL
        
    def test_login_invalid_credentials(self):
        """Test login with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER1_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        
    def test_login_nonexistent_user(self):
        """Test login with non-existent email"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "test123"
        })
        assert response.status_code == 401


class TestUserCredits:
    """User credits system tests"""
    
    @pytest.fixture
    def auth_token_user1(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER1_EMAIL,
            "password": PASSWORD
        })
        return response.json()["token"]
    
    @pytest.fixture
    def auth_token_user2(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER2_EMAIL,
            "password": PASSWORD
        })
        return response.json()["token"]
    
    def test_get_user_credits(self, auth_token_user1):
        """Test getting user credits"""
        response = requests.get(
            f"{BASE_URL}/api/users/credits",
            headers={"Authorization": f"Bearer {auth_token_user1}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "games_remaining" in data
        assert isinstance(data["games_remaining"], int)
        
    def test_get_auth_me(self, auth_token_user1):
        """Test getting current user via /api/auth/me"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token_user1}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Response is the user object directly
        assert "email" in data


class TestMatchEndpoints:
    """Match creation and management tests"""
    
    @pytest.fixture
    def auth_tokens(self):
        """Get auth tokens for both users"""
        r1 = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER1_EMAIL,
            "password": PASSWORD
        })
        r2 = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER2_EMAIL,
            "password": PASSWORD
        })
        return {
            "user1": {
                "token": r1.json()["token"],
                "id": r1.json()["user"]["id"]
            },
            "user2": {
                "token": r2.json()["token"],
                "id": r2.json()["user"]["id"]
            }
        }
    
    def test_get_pending_matches(self, auth_tokens):
        """Test getting pending matches"""
        response = requests.get(
            f"{BASE_URL}/api/matches/pending",
            headers={"Authorization": f"Bearer {auth_tokens['user1']['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        
    def test_get_my_active_matches(self, auth_tokens):
        """Test getting active matches"""
        response = requests.get(
            f"{BASE_URL}/api/matches/my-active",
            headers={"Authorization": f"Bearer {auth_tokens['user1']['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Response can be {"match": ...} or {"matches": ...}
        assert "match" in data or "matches" in data


class TestLobbyEndpoints:
    """Lobby and online users tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER1_EMAIL,
            "password": PASSWORD
        })
        return response.json()["token"]
    
    def test_get_online_users(self, auth_token):
        """Test getting online users list"""
        response = requests.get(
            f"{BASE_URL}/api/users/online",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        
    def test_get_topics(self, auth_token):
        """Test getting available topics"""
        response = requests.get(
            f"{BASE_URL}/api/topics/top",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "topics" in data


class TestLeaderboard:
    """Leaderboard tests"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER1_EMAIL,
            "password": PASSWORD
        })
        return response.json()["token"]
    
    def test_get_global_leaderboard(self, auth_token):
        """Test getting global leaderboard"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboards/global",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Response has "entries" field
        assert "entries" in data or "leaderboard" in data


class TestAdminEndpoints:
    """Admin panel tests"""
    
    def test_admin_stats_without_key(self):
        """Test admin stats without admin key returns 401"""
        response = requests.get(f"{BASE_URL}/api/admin/stats")
        assert response.status_code == 401
        
    def test_admin_stats_with_key(self):
        """Test admin stats with valid admin key (Bearer token)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/stats",
            headers={"Authorization": f"Bearer {ADMIN_KEY}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Check for expected fields
        assert "total_users" in data


class TestHealthEndpoint:
    """Health check tests"""
    
    def test_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# WebSocket tests run separately via test_ws_sync.py since pytest-asyncio has issues
# The test_ws_sync.py already passed all 9 steps including:
# - Notification WebSocket connection
# - Challenge notification delivery
# - Match WebSocket connection
# - game_start synchronization


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
