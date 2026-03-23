"""
Knowledge Wars - Credit Deduction Bug Testing
Tests the specific bugs reported:
1. /api/matches/pending returns 500 error
2. Credits deducted before match acceptance
3. Opponent not receiving notifications
"""

import requests
import sys
import time
from datetime import datetime

class CreditBugTester:
    def __init__(self, base_url="https://knowledge-wars-pvp.preview.emergentagent.com"):
        self.base_url = base_url
        self.test1_token = None
        self.test2_token = None
        self.test1_user = None
        self.test2_user = None
        self.tests_run = 0
        self.tests_passed = 0

    def log(self, message, status="INFO"):
        icons = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}
        print(f"{icons.get(status, 'ℹ️')} {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None, check_response=None, timeout=15):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        self.log(f"Testing {name}...", "INFO")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"PASSED - Status: {response.status_code}", "PASS")
                
                # Additional response checks
                if check_response and response.status_code == expected_status:
                    try:
                        response_data = response.json()
                        check_result = check_response(response_data)
                        if not check_result:
                            self.log(f"Response check failed", "FAIL")
                            self.tests_passed -= 1
                            success = False
                    except Exception as e:
                        self.log(f"Response check error: {str(e)}", "FAIL")
                        self.tests_passed -= 1
                        success = False
                
                return success, response.json() if response.status_code == expected_status else {}
            else:
                self.log(f"FAILED - Expected {expected_status}, got {response.status_code}", "FAIL")
                try:
                    self.log(f"Response: {response.json()}", "FAIL")
                except:
                    self.log(f"Response: {response.text}", "FAIL")
                return False, {}

        except Exception as e:
            self.log(f"FAILED - Error: {str(e)}", "FAIL")
            return False, {}

    def test_login(self, email, password):
        """Test login and get token"""
        self.log(f"\n🔐 Logging in as {email}...", "INFO")
        success, response = self.run_test(
            f"Login {email}",
            "POST",
            "api/auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'token' in response:
            self.log(f"Login successful, token received", "PASS")
            return response['token'], response.get('user')
        return None, None

    def get_user_credits(self, token):
        """Get current user's game credits"""
        success, response = self.run_test(
            "Get user credits",
            "GET",
            "api/users/credits",
            200,
            token=token
        )
        if success:
            credits = response.get('games_remaining', 0)
            self.log(f"Current credits: {credits}", "INFO")
            return credits
        return None

    def test_pending_endpoint(self, token):
        """Test that /api/matches/pending returns 200 (not 500)"""
        self.log("\n🔍 Testing /api/matches/pending endpoint...", "INFO")
        success, response = self.run_test(
            "Get pending matches",
            "GET",
            "api/matches/pending",
            200,
            token=token
        )
        if success:
            self.log(f"✅ BUG FIX VERIFIED: /api/matches/pending returns 200 (not 500)", "PASS")
            return True
        else:
            self.log(f"❌ BUG STILL EXISTS: /api/matches/pending returns error", "FAIL")
            return False

    def test_create_match_no_credit_deduction(self, challenger_token, opponent_id):
        """Test that creating a match does NOT deduct credits"""
        self.log("\n💰 Testing credit deduction on match creation...", "INFO")
        
        # Get credits before
        credits_before = self.get_user_credits(challenger_token)
        if credits_before is None:
            self.log("Failed to get credits before match creation", "FAIL")
            return None
        
        # Create match (needs longer timeout for LLM question generation)
        self.log("Creating match (this may take 30-60s for question generation)...", "INFO")
        success, response = self.run_test(
            "Create match challenge",
            "POST",
            "api/matches/create",
            200,
            data={
                "opponent_id": opponent_id,
                "topic": "General Knowledge",
                "language": "es"
            },
            token=challenger_token,
            timeout=90
        )
        
        if not success:
            self.log("Failed to create match", "FAIL")
            return None
        
        match_id = response.get('match', {}).get('id')
        self.log(f"Match created with ID: {match_id}", "INFO")
        
        # Get credits after
        time.sleep(1)  # Small delay
        credits_after = self.get_user_credits(challenger_token)
        if credits_after is None:
            self.log("Failed to get credits after match creation", "FAIL")
            return None
        
        # Verify credits NOT deducted
        if credits_before == credits_after:
            self.log(f"✅ BUG FIX VERIFIED: Credits NOT deducted on match creation ({credits_before} → {credits_after})", "PASS")
            return match_id
        else:
            self.log(f"❌ BUG STILL EXISTS: Credits deducted on match creation ({credits_before} → {credits_after})", "FAIL")
            self.tests_passed -= 1
            return match_id

    def test_accept_match_with_credit_deduction(self, match_id, acceptor_token, challenger_token):
        """Test that accepting a match DOES deduct credits from both players"""
        self.log("\n✅ Testing credit deduction on match acceptance...", "INFO")
        
        # Get credits before for both players
        acceptor_credits_before = self.get_user_credits(acceptor_token)
        challenger_credits_before = self.get_user_credits(challenger_token)
        
        if acceptor_credits_before is None or challenger_credits_before is None:
            self.log("Failed to get credits before acceptance", "FAIL")
            return False
        
        # Accept match
        success, response = self.run_test(
            "Accept match challenge",
            "POST",
            f"api/matches/{match_id}/accept",
            200,
            token=acceptor_token
        )
        
        if not success:
            self.log("Failed to accept match", "FAIL")
            return False
        
        # Get credits after for both players
        time.sleep(1)  # Small delay
        acceptor_credits_after = self.get_user_credits(acceptor_token)
        challenger_credits_after = self.get_user_credits(challenger_token)
        
        if acceptor_credits_after is None or challenger_credits_after is None:
            self.log("Failed to get credits after acceptance", "FAIL")
            return False
        
        # Verify credits deducted from both
        acceptor_deducted = acceptor_credits_before - acceptor_credits_after == 1
        challenger_deducted = challenger_credits_before - challenger_credits_after == 1
        
        if acceptor_deducted and challenger_deducted:
            self.log(f"✅ BUG FIX VERIFIED: Credits deducted from BOTH players on acceptance", "PASS")
            self.log(f"   Acceptor: {acceptor_credits_before} → {acceptor_credits_after}", "INFO")
            self.log(f"   Challenger: {challenger_credits_before} → {challenger_credits_after}", "INFO")
            return True
        else:
            self.log(f"❌ BUG: Credits not properly deducted", "FAIL")
            self.log(f"   Acceptor: {acceptor_credits_before} → {acceptor_credits_after} (expected -1)", "FAIL")
            self.log(f"   Challenger: {challenger_credits_before} → {challenger_credits_after} (expected -1)", "FAIL")
            self.tests_passed -= 1
            return False

    def test_reject_match_no_credit_deduction(self, challenger_token, opponent_id, rejecter_token):
        """Test that rejecting a match does NOT deduct credits"""
        self.log("\n🚫 Testing credit deduction on match rejection...", "INFO")
        
        # Create a new match (needs longer timeout for LLM)
        self.log("Creating match for rejection test (this may take 30-60s)...", "INFO")
        success, response = self.run_test(
            "Create match for rejection test",
            "POST",
            "api/matches/create",
            200,
            data={
                "opponent_id": opponent_id,
                "topic": "Science",
                "language": "es"
            },
            token=challenger_token,
            timeout=90
        )
        
        if not success:
            self.log("Failed to create match for rejection test", "FAIL")
            return False
        
        match_id = response.get('match', {}).get('id')
        
        # Get credits before rejection
        rejecter_credits_before = self.get_user_credits(rejecter_token)
        challenger_credits_before = self.get_user_credits(challenger_token)
        
        if rejecter_credits_before is None or challenger_credits_before is None:
            self.log("Failed to get credits before rejection", "FAIL")
            return False
        
        # Reject match
        success, response = self.run_test(
            "Reject match challenge",
            "POST",
            f"api/matches/{match_id}/reject",
            200,
            token=rejecter_token
        )
        
        if not success:
            self.log("Failed to reject match", "FAIL")
            return False
        
        # Get credits after rejection
        time.sleep(1)
        rejecter_credits_after = self.get_user_credits(rejecter_token)
        challenger_credits_after = self.get_user_credits(challenger_token)
        
        if rejecter_credits_after is None or challenger_credits_after is None:
            self.log("Failed to get credits after rejection", "FAIL")
            return False
        
        # Verify NO credits deducted
        if rejecter_credits_before == rejecter_credits_after and challenger_credits_before == challenger_credits_after:
            self.log(f"✅ BUG FIX VERIFIED: NO credits deducted on rejection", "PASS")
            self.log(f"   Rejecter: {rejecter_credits_before} → {rejecter_credits_after}", "INFO")
            self.log(f"   Challenger: {challenger_credits_before} → {challenger_credits_after}", "INFO")
            return True
        else:
            self.log(f"❌ BUG: Credits incorrectly deducted on rejection", "FAIL")
            self.log(f"   Rejecter: {rejecter_credits_before} → {rejecter_credits_after}", "FAIL")
            self.log(f"   Challenger: {challenger_credits_before} → {challenger_credits_after}", "FAIL")
            self.tests_passed -= 1
            return False

    def run_all_tests(self):
        """Run all credit bug tests"""
        self.log("\n" + "="*60, "INFO")
        self.log("🎮 KNOWLEDGE WARS - CREDIT BUG TESTING", "INFO")
        self.log("="*60 + "\n", "INFO")
        
        # Login both test accounts
        self.test1_token, self.test1_user = self.test_login("test1@knowledgewars.app", "test123")
        if not self.test1_token:
            self.log("Failed to login test1 account", "FAIL")
            return 1
        
        self.test2_token, self.test2_user = self.test_login("test2@knowledgewars.app", "test123")
        if not self.test2_token:
            self.log("Failed to login test2 account", "FAIL")
            return 1
        
        test1_id = self.test1_user.get('id')
        test2_id = self.test2_user.get('id')
        
        self.log(f"\n✅ Both test accounts logged in successfully", "PASS")
        self.log(f"   Test1 ID: {test1_id}", "INFO")
        self.log(f"   Test2 ID: {test2_id}", "INFO")
        
        # Test 1: /api/matches/pending returns 200
        self.test_pending_endpoint(self.test1_token)
        
        # Test 2: Create match does NOT deduct credits
        match_id = self.test_create_match_no_credit_deduction(self.test1_token, test2_id)
        
        if match_id:
            # Test 3: Accept match DOES deduct credits from both
            self.test_accept_match_with_credit_deduction(match_id, self.test2_token, self.test1_token)
        
        # Test 4: Reject match does NOT deduct credits
        self.test_reject_match_no_credit_deduction(self.test1_token, test2_id, self.test2_token)
        
        # Print summary
        self.log("\n" + "="*60, "INFO")
        self.log(f"📊 TEST SUMMARY", "INFO")
        self.log("="*60, "INFO")
        self.log(f"Tests Run: {self.tests_run}", "INFO")
        self.log(f"Tests Passed: {self.tests_passed}", "PASS" if self.tests_passed == self.tests_run else "FAIL")
        self.log(f"Tests Failed: {self.tests_run - self.tests_passed}", "FAIL" if self.tests_passed != self.tests_run else "INFO")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%", "INFO")
        self.log("="*60 + "\n", "INFO")
        
        return 0 if self.tests_passed == self.tests_run else 1

def main():
    tester = CreditBugTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
