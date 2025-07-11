import os
import sys
import time
import json
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = "http://localhost:5000"  # Update if your app runs on a different URL
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

class TestResult:
    def __init__(self, name):
        self.name = name
        self.passed = False
        self.message = ""
        self.details = {}
    
    def success(self, message="", details=None):
        self.passed = True
        self.message = message
        self.details = details or {}
        return self
    
    def fail(self, message="", details=None):
        self.passed = False
        self.message = message
        self.details = details or {}
        return self
    
    def __str__(self):
        # Use ASCII characters for Windows compatibility
        status = "[PASS]" if self.passed else "[FAIL]"
        return f"{status} - {self.name}: {self.message}"

def get_auth_session():
    """Get an authenticated session for testing"""
    session = requests.Session()
    login_url = f"{BASE_URL}/admin/login"
    
    # Get CSRF token
    response = session.get(login_url)
    csrf_token = None
    if 'csrf_token' in session.cookies:
        csrf_token = session.cookies['csrf_token']
    
    # Login
    login_data = {
        'email': ADMIN_EMAIL,
        'password': ADMIN_PASSWORD,
        'csrf_token': csrf_token
    }
    
    response = session.post(login_url, data=login_data, allow_redirects=True)
    
    if 'admin/dashboard' not in response.url:
        raise Exception("Failed to authenticate as admin")
    
    return session

def test_dashboard_loading():
    """Test if the admin dashboard loads successfully"""
    result = TestResult("Dashboard Loading")
    
    try:
        session = get_auth_session()
        response = session.get(f"{BASE_URL}/admin/dashboard")
        
        if response.status_code == 200:
            return result.success("Dashboard loaded successfully")
        else:
            return result.fail(f"Failed to load dashboard. Status code: {response.status_code}")
    except Exception as e:
        return result.fail(f"Error loading dashboard: {str(e)}")

def test_dashboard_stats():
    """Test if dashboard statistics are displayed correctly"""
    result = TestResult("Dashboard Statistics")
    
    try:
        session = get_auth_session()
        response = session.get(f"{BASE_URL}/admin/dashboard")
        
        if response.status_code != 200:
            return result.fail(f"Failed to load dashboard. Status code: {response.status_code}")
        
        # Check for required stats in the response
        required_stats = [
            'total_users',
            'active_users',
            'new_users_today',
            'total_admins'
        ]
        
        content = response.text
        missing_stats = [stat for stat in required_stats if f'id="{stat}"' not in content]
        
        if missing_stats:
            return result.fail(f"Missing statistics: {', '.join(missing_stats)}")
        else:
            return result.success("All required statistics are displayed")
    except Exception as e:
        return result.fail(f"Error checking dashboard stats: {str(e)}")

def test_feature_usage_charts():
    """Test if feature usage charts are rendered"""
    result = TestResult("Feature Usage Charts")
    
    try:
        session = get_auth_session()
        response = session.get(f"{BASE_URL}/admin/dashboard")
        
        if response.status_code != 200:
            return result.fail(f"Failed to load dashboard. Status code: {response.status_code}")
        
        content = response.text
        
        # Check for chart containers
        required_charts = [
            'userGrowthChart',
            'featureUsageChart'
        ]
        
        missing_charts = [chart for chart in required_charts if f'id="{chart}"' not in content]
        
        if missing_charts:
            return result.fail(f"Missing charts: {', '.join(missing_charts)}")
        else:
            return result.success("All required charts are present")
    except Exception as e:
        return result.fail(f"Error checking feature usage charts: {str(e)}")

def test_recent_activities():
    """Test if recent activities are displayed"""
    result = TestResult("Recent Activities")
    
    try:
        session = get_auth_session()
        response = session.get(f"{BASE_URL}/admin/dashboard")
        
        if response.status_code != 200:
            return result.fail(f"Failed to load dashboard. Status code: {response.status_code}")
        
        content = response.text
        
        # Check for recent activities section
        if 'Recent Activities' not in content:
            return result.fail("Recent activities section not found")
        
        # Check if activities are listed
        if 'No recent activities' not in content and 'activity-item' not in content:
            return result.fail("No activities found in the recent activities section")
        
        return result.success("Recent activities are displayed correctly")
    except Exception as e:
        return result.fail(f"Error checking recent activities: {str(e)}")

def run_dashboard_tests():
    """Run all dashboard tests and return results"""
    # Set console output encoding to UTF-8
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("\n=== Running Admin Dashboard Tests ===\n")
    
    tests = [
        test_dashboard_loading,
        test_dashboard_stats,
        test_feature_usage_charts,
        test_recent_activities
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print(result)
        except Exception as e:
            result = TestResult(test.__name__)
            result.fail(f"Test failed with exception: {str(e)}")
            results.append(result)
            print(result)
    
    # Print summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    print(f"\n=== Test Results: {passed}/{total} passed ===\n")
    
    # Print failed tests
    failed_tests = [r for r in results if not r.passed]
    if failed_tests:
        print("Failed Tests:")
        for test in failed_tests:
            print(f"- {test.name}: {test.message}")
    
    return all(r.passed for r in results)

if __name__ == "__main__":
    try:
        success = run_dashboard_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTesting interrupted by user")
        sys.exit(1)
