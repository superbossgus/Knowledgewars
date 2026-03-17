"""
Knowledge Wars - Backend API Testing
Tests all API endpoints using the public URL
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Optional

# Public backend URL
BASE_URL = "https://neon-trivia-2.preview.emergentagent.com"

class KnowledgeWarsAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.user_id = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
    def log_test(self, name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} - {name}")
        if details and not passed:
            print(f"      Details: {details}")
        
        self.test_results.append({
            "test": name,
            "passed": passed,
            "details": details
        })
    
    def test_endpoint(self, method: str, endpoint: str, expected_status: int, 
                     data: Optional[Dict] = None, auth: bool = False) -> tuple:
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=10)
            else:
                return False, f"Unsupported method: {method}", None
            
            success = response.status_code == expected_status
            
            if success:
                try:
                    return True, "", response.json()
                except:
                    return True, "", {}
            else:
                error_msg = f"Expected {expected_status}, got {response.status_code}"
                try:
                    error_detail = response.json().get('detail', '')
                    if error_detail:
                        error_msg += f" - {error_detail}"
                except:
                    pass
                return False, error_msg, None
                
        except requests.exceptions.Timeout:
            return False, "Request timeout", None
        except requests.exceptions.ConnectionError:
            return False, "Connection error", None
        except Exception as e:
            return False, str(e), None
    
    def test_health(self):
        """Test health check endpoint"""
        print("\n[1] Testing Health Check")
        success, error, data = self.test_endpoint('GET', '/api/health', 200)
        self.log_test("GET /api/health", success, error)
        return success
    
    def test_register(self):
        """Test user registration"""
        print("\n[2] Testing User Registration")
        
        # Generate unique email
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        test_user = {
            "email": f"test_user_{timestamp}@test.com",
            "password": "TestPass123!",
            "display_name": f"TestUser{timestamp}",
            "country_code": "us",
            "favorite_topic": "General Knowledge",
            "language": "en"
        }
        
        success, error, data = self.test_endpoint('POST', '/api/auth/register', 200, test_user)
        
        if success and data:
            self.token = data.get('token')
            self.user_data = data.get('user')
            self.user_id = self.user_data.get('id')
            self.log_test("POST /api/auth/register", True)
            print(f"      User ID: {self.user_id}")
            print(f"      Token: {self.token[:20]}...")
            return True
        else:
            self.log_test("POST /api/auth/register", False, error)
            return False
    
    def test_login(self):
        """Test user login"""
        print("\n[3] Testing User Login")
        
        # Create a new user for login test
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S") + "login"
        register_data = {
            "email": f"login_test_{timestamp}@test.com",
            "password": "LoginPass123!",
            "display_name": f"LoginUser{timestamp}",
            "country_code": "mx",
            "favorite_topic": "Sports",
            "language": "es"
        }
        
        # Register first
        success, error, data = self.test_endpoint('POST', '/api/auth/register', 200, register_data)
        if not success:
            self.log_test("POST /api/auth/login (setup)", False, "Failed to create test user")
            return False
        
        # Now test login
        login_data = {
            "email": register_data["email"],
            "password": register_data["password"]
        }
        
        success, error, data = self.test_endpoint('POST', '/api/auth/login', 200, login_data)
        
        if success and data and 'token' in data:
            self.log_test("POST /api/auth/login", True)
            return True
        else:
            self.log_test("POST /api/auth/login", False, error)
            return False
    
    def test_get_me(self):
        """Test get current user"""
        print("\n[4] Testing Get Current User")
        
        if not self.token:
            self.log_test("GET /api/auth/me", False, "No auth token available")
            return False
        
        success, error, data = self.test_endpoint('GET', '/api/auth/me', 200, auth=True)
        
        if success and data:
            self.log_test("GET /api/auth/me", True)
            print(f"      Display Name: {data.get('display_name')}")
            print(f"      ELO: {data.get('elo_rating')}")
            print(f"      League: {data.get('league')}")
            return True
        else:
            self.log_test("GET /api/auth/me", False, error)
            return False
    
    def test_duels_remaining(self):
        """Test get remaining duels"""
        print("\n[5] Testing Duels Remaining")
        
        if not self.token:
            self.log_test("GET /api/users/duels/remaining", False, "No auth token")
            return False
        
        success, error, data = self.test_endpoint('GET', '/api/users/duels/remaining', 200, auth=True)
        
        if success and data:
            self.log_test("GET /api/users/duels/remaining", True)
            print(f"      Remaining: {data.get('remaining')}")
            print(f"      Unlimited: {data.get('unlimited')}")
            return True
        else:
            self.log_test("GET /api/users/duels/remaining", False, error)
            return False
    
    def test_top_topics(self):
        """Test get top topics"""
        print("\n[6] Testing Top Topics")
        
        success, error, data = self.test_endpoint('GET', '/api/topics/top', 200)
        
        if success and data and 'topics' in data:
            self.log_test("GET /api/topics/top", True)
            print(f"      Topics count: {len(data['topics'])}")
            if data['topics']:
                print(f"      Sample: {data['topics'][0].get('topic')}")
            return True
        else:
            self.log_test("GET /api/topics/top", False, error)
            return False
    
    def test_online_users(self):
        """Test get online users"""
        print("\n[7] Testing Online Users")
        
        if not self.token:
            self.log_test("GET /api/users/online", False, "No auth token")
            return False
        
        success, error, data = self.test_endpoint('GET', '/api/users/online', 200, auth=True)
        
        if success and data:
            self.log_test("GET /api/users/online", True)
            print(f"      Online users: {len(data.get('users', []))}")
            return True
        else:
            self.log_test("GET /api/users/online", False, error)
            return False
    
    def test_leaderboards(self):
        """Test leaderboards"""
        print("\n[8] Testing Leaderboards")
        
        # Test global leaderboard
        success, error, data = self.test_endpoint('GET', '/api/leaderboards/global', 200)
        
        if success and data and 'entries' in data:
            self.log_test("GET /api/leaderboards/global", True)
            print(f"      Global entries: {len(data['entries'])}")
        else:
            self.log_test("GET /api/leaderboards/global", False, error)
            return False
        
        # Test weekly leaderboard
        success, error, data = self.test_endpoint('GET', '/api/leaderboards/weekly', 200)
        
        if success and data:
            self.log_test("GET /api/leaderboards/weekly", True)
            return True
        else:
            self.log_test("GET /api/leaderboards/weekly", False, error)
            return False
    
    def test_question_generation(self):
        """Test question generation (requires auth)"""
        print("\n[9] Testing Question Generation")
        
        if not self.token:
            self.log_test("GET /api/questions/generate", False, "No auth token")
            return False
        
        # Test with General Knowledge topic
        success, error, data = self.test_endpoint(
            'GET', 
            '/api/questions/generate?topic=General Knowledge&language=en', 
            200, 
            auth=True
        )
        
        if success and data:
            # Check if questions are present
            if 'questions' in data and len(data['questions']) == 10:
                self.log_test("GET /api/questions/generate", True)
                print(f"      Generated {len(data['questions'])} questions")
                # Validate structure
                sample = data['questions'][0]
                has_required = all(k in sample for k in ['question', 'options', 'correct_letter', 'hint'])
                if has_required:
                    print(f"      ✓ Question structure valid")
                else:
                    print(f"      ⚠ Question structure incomplete")
                return True
            else:
                self.log_test("GET /api/questions/generate", False, "Invalid question count or structure")
                return False
        else:
            self.log_test("GET /api/questions/generate", False, error)
            return False
    
    def test_payments_checkout(self):
        """Test Stripe checkout creation"""
        print("\n[10] Testing Stripe Checkout")
        
        if not self.token:
            self.log_test("POST /api/payments/checkout", False, "No auth token")
            return False
        
        # Test premium subscription checkout
        checkout_data = {
            "product_type": "premium_subscription",
            "origin_url": "https://neon-trivia-2.preview.emergentagent.com"
        }
        
        success, error, data = self.test_endpoint(
            'POST', 
            '/api/payments/checkout', 
            200, 
            checkout_data, 
            auth=True
        )
        
        if success and data and 'checkout_url' in data:
            self.log_test("POST /api/payments/checkout (subscription)", True)
            print(f"      Checkout URL: {data['checkout_url'][:50]}...")
        else:
            self.log_test("POST /api/payments/checkout (subscription)", False, error)
            return False
        
        # Test consumable checkout
        checkout_data['product_type'] = 'consumable_100'
        success, error, data = self.test_endpoint(
            'POST', 
            '/api/payments/checkout', 
            200, 
            checkout_data, 
            auth=True
        )
        
        if success and data and 'checkout_url' in data:
            self.log_test("POST /api/payments/checkout (consumable)", True)
            return True
        else:
            self.log_test("POST /api/payments/checkout (consumable)", False, error)
            return False
    
    def test_admin_stats(self):
        """Test admin stats endpoint"""
        print("\n[11] Testing Admin Stats")
        
        if not self.token:
            self.log_test("GET /api/admin/stats", False, "No auth token")
            return False
        
        success, error, data = self.test_endpoint('GET', '/api/admin/stats', 200, auth=True)
        
        if success and data:
            self.log_test("GET /api/admin/stats", True)
            print(f"      Total users: {data.get('total_users')}")
            print(f"      Total matches: {data.get('total_matches')}")
            return True
        else:
            self.log_test("GET /api/admin/stats", False, error)
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("=" * 80)
        print("KNOWLEDGE WARS - BACKEND API TESTING")
        print("=" * 80)
        print(f"Base URL: {self.base_url}")
        print("=" * 80)
        
        # Run tests in order
        self.test_health()
        self.test_register()
        self.test_login()
        self.test_get_me()
        self.test_duels_remaining()
        self.test_top_topics()
        self.test_online_users()
        self.test_leaderboards()
        self.test_question_generation()
        self.test_payments_checkout()
        self.test_admin_stats()
        
        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        print("=" * 80)
        
        return self.tests_passed == self.tests_run


def main():
    tester = KnowledgeWarsAPITester()
    success = tester.run_all_tests()
    
    # Save results to file
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_tests': tester.tests_run,
            'passed': tester.tests_passed,
            'failed': tester.tests_run - tester.tests_passed,
            'success_rate': (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0,
            'results': tester.test_results
        }, f, indent=2)
    
    print(f"\n✓ Results saved to /app/backend_test_results.json")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
