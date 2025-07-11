import os
import sys
import time
import json
import requests
from dotenv import load_dotenv
from flask import url_for
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = "http://localhost:5000"  # Update if your app runs on a different URL
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

# Test data
TEST_USER = {
    'email': 'testuser@example.com',
    'password': 'testpass123',
    'name': 'Test User'
}

# Test assessment data
TEST_ASSESSMENT = {
    'title': 'Test Assessment',
    'description': 'This is a test assessment',
    'questions': [
        {'question': 'Question 1', 'options': ['Option 1', 'Option 2']},
        {'question': 'Question 2', 'options': ['Option A', 'Option B']}
    ]
}

# Test journal entry data
TEST_JOURNAL_ENTRY = {
    'title': 'Test Journal Entry',
    'content': 'This is a test journal entry',
    'mood': 'happy',
    'tags': 'test, journal'
}

class TestResult:
    def __init__(self, name):
        self.name = name
        self.passed = False
        self.message = ""
        self.details = {}
    
    def success(self, message="", details=None):
        self.passed = True
        self.message = message
        if details:
            self.details = details
        return self
    
    def fail(self, message="", details=None):
        self.passed = False
        self.message = message
        if details:
            self.details = details
        return self
    
    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        details = f"\n    Details: {json.dumps(self.details, indent=2)}" if self.details else ""
        return f"{status} - {self.name}: {self.message}{details}"

def test_admin_login():
    """Test admin login functionality"""
    result = TestResult("Admin Login")
    login_url = f"{BASE_URL}/admin/login"
    
    try:
        # Create a session to maintain cookies
        session = requests.Session()
        
        # Get the login page to get CSRF token
        response = session.get(login_url)
        if response.status_code != 200:
            return result.fail("Failed to load login page", 
                             {"status_code": response.status_code, "error": response.text[:200]})
        
        # Try to log in
        login_data = {
            'email': ADMIN_EMAIL,
            'password': ADMIN_PASSWORD,
            'submit': 'Login'
        }
        
        start_time = time.time()
        response = session.post(login_url, data=login_data, allow_redirects=True)
        response_time = (time.time() - start_time) * 1000  # in milliseconds
        
        if 'Welcome, admin!' in response.text or 'Dashboard' in response.text:
            return result.success("Admin login successful", 
                                {"response_time_ms": f"{response_time:.2f}"})
        else:
            return result.fail("Admin login failed", 
                             {"status_code": response.status_code, 
                              "response": response.text[:500]})
    except Exception as e:
        return result.fail(f"Exception during admin login: {str(e)}")
    
    return result

def test_admin_dashboard(session):
    """Test admin dashboard access"""
    result = TestResult("Admin Dashboard")
    dashboard_url = f"{BASE_URL}/admin/dashboard"
    
    try:
        start_time = time.time()
        response = session.get(dashboard_url)
        response_time = (time.time() - start_time) * 1000  # in milliseconds
        
        if response.status_code == 200 and 'Dashboard' in response.text:
            # Check for key dashboard elements
            checks = {
                'user_stats': 'User Statistics' in response.text,
                'recent_activity': 'Recent Activity' in response.text,
                'quick_links': 'Quick Links' in response.text
            }
            
            if all(checks.values()):
                return result.success("Admin dashboard loaded successfully",
                                    {"response_time_ms": f"{response_time:.2f}"})
            else:
                missing = [k for k, v in checks.items() if not v]
                return result.fail("Missing dashboard elements",
                                 {"missing_elements": missing})
        else:
            return result.fail("Failed to load admin dashboard",
                             {"status_code": response.status_code,
                              "response": response.text[:500]})
    except Exception as e:
        return result.fail(f"Exception during dashboard test: {str(e)}")

def test_users_page(session):
    """Test users management page"""
    result = TestResult("Users Management")
    users_url = f"{BASE_URL}/admin/users"
    
    try:
        start_time = time.time()
        response = session.get(users_url)
        response_time = (time.time() - start_time) * 1000  # in milliseconds
        
        if response.status_code != 200:
            return result.fail("Failed to load users page",
                             {"status_code": response.status_code})
        
        # Check for required elements
        checks = {
            'page_loaded': 'Users' in response.text,
            'admin_user_found': 'admin@example.com' in response.text,
            'user_table_exists': '<table' in response.text and '</table>' in response.text
        }
        
        if not all(checks.values()):
            missing = [k for k, v in checks.items() if not v]
            return result.fail("Missing elements in users page",
                             {"missing_elements": missing})
        
        # Test user search functionality
        search_url = f"{users_url}?search=admin"
        search_response = session.get(search_url)
        
        if search_response.status_code != 200 or 'admin@example.com' not in search_response.text:
            return result.fail("User search failed",
                             {"status_code": search_response.status_code})
        
        return result.success("Users management page loaded successfully",
                            {"response_time_ms": f"{response_time:.2f}",
                             "search_functional": True})
    except Exception as e:
        return result.fail(f"Exception during users page test: {str(e)}")

def test_assessments_page(session):
    """Test assessments page"""
    print("\n=== Testing Assessments Page ===")
    assessments_url = f"{BASE_URL}/admin/assessments"
    response = session.get(assessments_url)
    
    if response.status_code == 200 and 'Assessments' in response.text:
        print("✅ Assessments page loaded successfully")
        
        # Check if test assessment data is displayed
        if 'depression' in response.text and 'anxiety' in response.text:
            print("✅ Test assessment data found")
        else:
            print("⚠️ Test assessment data not found")
            
        return True
    else:
        print("❌ Failed to load assessments page")
        print(f"Response status: {response.status_code}")
        return False

def test_journal_entries(session):
    """Test journal entries functionality"""
    print("\n=== Testing Journal Entries ===")
    journal_url = f"{BASE_URL}/journal"
    response = session.get(journal_url)
    
    if response.status_code == 200 and 'Journal Entries' in response.text:
        print("✅ Journal entries page loaded successfully")
        
        # Check if test journal entries are displayed
        if 'First Entry' in response.text and 'Second Entry' in response.text:
            print("✅ Test journal entries found")
        else:
            print("⚠️ Test journal entries not found")
            
        return True
    else:
        print("❌ Failed to load journal entries page")
        print(f"Response status: {response.status_code}")
        return False

def test_game_sessions(session):
    """Test game sessions functionality"""
    result = TestResult("Game Sessions")
    games_url = f"{BASE_URL}/games"
    
    try:
        # First try the main games page
        start_time = time.time()
        response = session.get(games_url)
        response_time = (time.time() - start_time) * 1000  # in milliseconds
        
        if response.status_code != 200:
            return result.fail("Failed to load games page",
                             {"status_code": response.status_code})
        
        # Check for game statistics or session data
        has_game_data = ('game' in response.text.lower() or 
                        'session' in response.text.lower() or
                        'statistics' in response.text.lower())
        
        if not has_game_data:
            return result.fail("Game session data not found")
        
        # If we have a game sessions API endpoint, test it
        sessions_url = f"{BASE_URL}/api/game_sessions"
        try:
            sessions_response = session.get(sessions_url)
            if sessions_response.status_code == 200:
                try:
                    sessions = sessions_response.json()
                    has_sessions = isinstance(sessions, list)
                    result.details['api_sessions_found'] = has_sessions
                    if has_sessions:
                        result.details['session_count'] = len(sessions)
                except:
                    result.details['api_response'] = "Invalid JSON response"
            else:
                result.details['api_status'] = sessions_response.status_code
        except Exception as api_error:
            result.details['api_error'] = str(api_error)
        
        return result.success("Game sessions page loaded successfully",
                            {"response_time_ms": f"{response_time:.2f}",
                             "has_game_data": has_game_data})
    except Exception as e:
        return result.fail(f"Exception during game sessions test: {str(e)}")

def run_all_tests():
    """Run all admin panel tests and return results"""
    results = []
    session = None
    
    try:
        # Test login first
        login_result = test_admin_login()
        results.append(login_result)
        
        if login_result.passed:
            # Create a session for authenticated tests
            session = requests.Session()
            login_data = {'email': ADMIN_EMAIL, 'password': ADMIN_PASSWORD, 'submit': 'Login'}
            session.post(f"{BASE_URL}/admin/login", data=login_data, allow_redirects=True)
            
            # Run other tests
            results.append(test_admin_dashboard(session))
            results.append(test_users_page(session))
            results.append(test_assessments_page(session))
            results.append(test_journal_entries(session))
            results.append(test_game_sessions(session))
        
        return results, session
    except Exception as e:
        results.append(TestResult("Test Runner").fail(f"Test runner error: {str(e)}"))
        return results, None

def print_summary(results):
    """Print test results summary"""
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    print(f"\n✅ {passed} of {total} tests passed ({passed/total*100:.1f}%)")
    
    # Print detailed results
    print("\nDETAILED RESULTS:")
    for result in results:
        print(f"\n{result}")
    
    print("\n" + "="*50)
    return passed == total

def main():
    print("=== Starting Admin Panel Tests ===\n")
    
    # Run all tests
    results, session = run_all_tests()
    
    # Print summary
    all_passed = print_summary(results)
    
    # Clean up (if needed)
    if session:
        session.close()
    
    # Exit with appropriate status code
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
