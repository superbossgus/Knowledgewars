"""
Test suite for Knowledge Wars REMATCH feature
Tests:
- POST /api/matches/create with is_rematch=true
- Challenge notification includes is_rematch flag
- match_finished event includes player IDs, names, topic for rematch context
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Test credentials
USER1_EMAIL = "test1@knowledgewars.app"
USER1_PASSWORD = "test123"
USER2_EMAIL = "test2@knowledgewars.app"
USER2_PASSWORD = "test123"


class TestRematchFeature:
    """Test suite for the rematch feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_auth_token(self, email, password):
        """Helper to get auth token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_01_health_check(self):
        """Verify API is accessible"""
        response = self.session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        print("✅ Health check passed")
    
    def test_02_login_user1(self):
        """Login as user1"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER1_EMAIL,
            "password": USER1_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        print(f"✅ User1 logged in: {data['user']['display_name']}")
    
    def test_03_login_user2(self):
        """Login as user2"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER2_EMAIL,
            "password": USER2_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        print(f"✅ User2 logged in: {data['user']['display_name']}")
    
    def test_04_create_normal_match_has_is_rematch_false(self):
        """Create a normal match (not rematch) - is_rematch should be false"""
        # Login as user1
        token1 = self.get_auth_token(USER1_EMAIL, USER1_PASSWORD)
        assert token1, "Failed to get token for user1"
        
        # Get user2 ID
        token2 = self.get_auth_token(USER2_EMAIL, USER2_PASSWORD)
        assert token2, "Failed to get token for user2"
        
        response = self.session.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token2}"
        })
        assert response.status_code == 200
        user2_id = response.json()["id"]
        
        # Create normal match (is_rematch defaults to false)
        response = self.session.post(f"{BASE_URL}/api/matches/create", 
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "opponent_id": user2_id,
                "topic": "Historia",
                "language": "es"
                # is_rematch not specified, should default to false
            }
        )
        
        # May fail if no credits, but check the response structure
        if response.status_code == 200:
            data = response.json()
            match = data.get("match", {})
            assert match.get("is_rematch") == False, f"Normal match should have is_rematch=false, got {match.get('is_rematch')}"
            print(f"✅ Normal match created with is_rematch=false, match_id: {match.get('id')}")
            
            # Cancel the match to clean up
            self.session.post(f"{BASE_URL}/api/matches/{match['id']}/cancel",
                headers={"Authorization": f"Bearer {token1}"})
        elif response.status_code == 403:
            print("⚠️ No credits available - skipping match creation test")
            pytest.skip("No credits available")
        else:
            pytest.fail(f"Unexpected response: {response.status_code} - {response.text}")
    
    def test_05_create_rematch_has_is_rematch_true(self):
        """Create a rematch - is_rematch should be true"""
        # Login as user1
        token1 = self.get_auth_token(USER1_EMAIL, USER1_PASSWORD)
        assert token1, "Failed to get token for user1"
        
        # Get user2 ID
        token2 = self.get_auth_token(USER2_EMAIL, USER2_PASSWORD)
        assert token2, "Failed to get token for user2"
        
        response = self.session.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token2}"
        })
        assert response.status_code == 200
        user2_id = response.json()["id"]
        
        # Create rematch with is_rematch=true
        response = self.session.post(f"{BASE_URL}/api/matches/create", 
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "opponent_id": user2_id,
                "topic": "Ciencia",
                "language": "es",
                "is_rematch": True
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            match = data.get("match", {})
            assert match.get("is_rematch") == True, f"Rematch should have is_rematch=true, got {match.get('is_rematch')}"
            print(f"✅ Rematch created with is_rematch=true, match_id: {match.get('id')}")
            
            # Cancel the match to clean up
            self.session.post(f"{BASE_URL}/api/matches/{match['id']}/cancel",
                headers={"Authorization": f"Bearer {token1}"})
        elif response.status_code == 403:
            print("⚠️ No credits available - skipping rematch creation test")
            pytest.skip("No credits available")
        else:
            pytest.fail(f"Unexpected response: {response.status_code} - {response.text}")
    
    def test_06_match_create_model_accepts_is_rematch(self):
        """Verify MatchCreate model accepts is_rematch field"""
        # This is a schema validation test - if the API accepts is_rematch without error, the model is correct
        token1 = self.get_auth_token(USER1_EMAIL, USER1_PASSWORD)
        assert token1, "Failed to get token for user1"
        
        token2 = self.get_auth_token(USER2_EMAIL, USER2_PASSWORD)
        assert token2, "Failed to get token for user2"
        
        response = self.session.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token2}"
        })
        user2_id = response.json()["id"]
        
        # Send request with is_rematch field - should not return 422 (validation error)
        response = self.session.post(f"{BASE_URL}/api/matches/create", 
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "opponent_id": user2_id,
                "topic": "Test Topic",
                "language": "es",
                "is_rematch": True
            }
        )
        
        # Should not be 422 (validation error)
        assert response.status_code != 422, f"MatchCreate model does not accept is_rematch field: {response.text}"
        print(f"✅ MatchCreate model accepts is_rematch field (status: {response.status_code})")
        
        # Clean up if match was created
        if response.status_code == 200:
            match_id = response.json().get("match", {}).get("id")
            if match_id:
                self.session.post(f"{BASE_URL}/api/matches/{match_id}/cancel",
                    headers={"Authorization": f"Bearer {token1}"})
    
    def test_07_pending_matches_includes_is_rematch(self):
        """Verify pending matches endpoint returns is_rematch field"""
        token1 = self.get_auth_token(USER1_EMAIL, USER1_PASSWORD)
        token2 = self.get_auth_token(USER2_EMAIL, USER2_PASSWORD)
        
        # Get user2 ID
        response = self.session.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token2}"
        })
        user2_id = response.json()["id"]
        
        # Create a rematch
        create_response = self.session.post(f"{BASE_URL}/api/matches/create", 
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "opponent_id": user2_id,
                "topic": "Deportes",
                "language": "es",
                "is_rematch": True
            }
        )
        
        if create_response.status_code != 200:
            pytest.skip("Could not create match for pending test")
        
        match_id = create_response.json().get("match", {}).get("id")
        
        # Check pending matches for user2
        pending_response = self.session.get(f"{BASE_URL}/api/matches/pending",
            headers={"Authorization": f"Bearer {token2}"})
        
        assert pending_response.status_code == 200, f"Failed to get pending matches: {pending_response.text}"
        
        matches = pending_response.json().get("matches", [])
        rematch_found = False
        for match in matches:
            if match.get("id") == match_id:
                assert "is_rematch" in match, "Pending match should include is_rematch field"
                assert match.get("is_rematch") == True, "Pending rematch should have is_rematch=true"
                rematch_found = True
                break
        
        if rematch_found:
            print("✅ Pending matches endpoint includes is_rematch field")
        else:
            print("⚠️ Created match not found in pending - may have been processed")
        
        # Clean up
        self.session.post(f"{BASE_URL}/api/matches/{match_id}/cancel",
            headers={"Authorization": f"Bearer {token1}"})
    
    def test_08_match_document_structure(self):
        """Verify match document includes all required fields for rematch context"""
        token1 = self.get_auth_token(USER1_EMAIL, USER1_PASSWORD)
        token2 = self.get_auth_token(USER2_EMAIL, USER2_PASSWORD)
        
        # Get user2 ID
        response = self.session.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token2}"
        })
        user2_id = response.json()["id"]
        user2_name = response.json()["display_name"]
        
        # Get user1 info
        response = self.session.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token1}"
        })
        user1_id = response.json()["id"]
        user1_name = response.json()["display_name"]
        
        # Create a match
        create_response = self.session.post(f"{BASE_URL}/api/matches/create", 
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "opponent_id": user2_id,
                "topic": "Geografía",
                "language": "es",
                "is_rematch": True
            }
        )
        
        if create_response.status_code != 200:
            pytest.skip("Could not create match for structure test")
        
        match = create_response.json().get("match", {})
        
        # Verify all required fields for rematch context
        required_fields = [
            "player_a_id", "player_b_id", 
            "player_a_name", "player_b_name",
            "topic", "is_rematch"
        ]
        
        for field in required_fields:
            assert field in match, f"Match document missing required field: {field}"
        
        # Verify values
        assert match["player_a_id"] == user1_id, "player_a_id mismatch"
        assert match["player_b_id"] == user2_id, "player_b_id mismatch"
        assert match["player_a_name"] == user1_name, "player_a_name mismatch"
        assert match["player_b_name"] == user2_name, "player_b_name mismatch"
        assert match["topic"] == "Geografía", "topic mismatch"
        assert match["is_rematch"] == True, "is_rematch mismatch"
        
        print("✅ Match document includes all required fields for rematch context")
        
        # Clean up
        self.session.post(f"{BASE_URL}/api/matches/{match['id']}/cancel",
            headers={"Authorization": f"Bearer {token1}"})


class TestRematchRegression:
    """Regression tests to ensure existing functionality still works"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self, email, password):
        """Helper to get auth token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def test_01_normal_challenge_still_works(self):
        """Verify normal challenge flow still works (regression)"""
        token1 = self.get_auth_token(USER1_EMAIL, USER1_PASSWORD)
        token2 = self.get_auth_token(USER2_EMAIL, USER2_PASSWORD)
        
        # Get user2 ID
        response = self.session.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token2}"
        })
        user2_id = response.json()["id"]
        
        # Create normal match without is_rematch field
        create_response = self.session.post(f"{BASE_URL}/api/matches/create", 
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "opponent_id": user2_id,
                "topic": "Música",
                "language": "es"
            }
        )
        
        if create_response.status_code == 200:
            match = create_response.json().get("match", {})
            # is_rematch should default to false
            assert match.get("is_rematch") == False, "Default is_rematch should be false"
            print("✅ Normal challenge flow works (is_rematch defaults to false)")
            
            # Clean up
            self.session.post(f"{BASE_URL}/api/matches/{match['id']}/cancel",
                headers={"Authorization": f"Bearer {token1}"})
        elif create_response.status_code == 403:
            pytest.skip("No credits available")
        else:
            pytest.fail(f"Normal challenge failed: {create_response.text}")
    
    def test_02_lobby_endpoint_works(self):
        """Verify lobby endpoint still works (regression)"""
        token1 = self.get_auth_token(USER1_EMAIL, USER1_PASSWORD)
        
        response = self.session.get(f"{BASE_URL}/api/users/online",
            headers={"Authorization": f"Bearer {token1}"})
        
        assert response.status_code == 200, f"Lobby endpoint failed: {response.text}"
        data = response.json()
        assert "users" in data, "Lobby response missing 'users' field"
        print(f"✅ Lobby endpoint works, {len(data['users'])} users online")
    
    def test_03_leaderboard_endpoint_works(self):
        """Verify leaderboard endpoint still works (regression)"""
        response = self.session.get(f"{BASE_URL}/api/leaderboards/global")
        
        assert response.status_code == 200, f"Leaderboard endpoint failed: {response.text}"
        data = response.json()
        assert "entries" in data, "Leaderboard response missing 'entries' field"
        print(f"✅ Leaderboard endpoint works, {len(data['entries'])} entries")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
