#!/usr/bin/env python3
"""Simple API test script."""

import requests
import json
import sys
from urllib.parse import urljoin


class APITester:
    """Test the Flask MunkiReport API."""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
        self.session = requests.Session()
    
    def test_health(self):
        """Test health endpoint (no auth)."""
        print("\n" + "="*60)
        print("TEST: Health Check")
        print("="*60)
        
        url = urljoin(self.base_url, "/api/v1/health")
        resp = self.session.get(url)
        
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        
        assert resp.status_code == 200, "Health check failed"
        assert resp.json()["success"], "Health check not successful"
        print("✅ PASSED")
    
    def test_status(self):
        """Test status endpoint (no auth)."""
        print("\n" + "="*60)
        print("TEST: Status Check")
        print("="*60)
        
        url = urljoin(self.base_url, "/api/v1/status")
        resp = self.session.get(url)
        
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        
        assert resp.status_code == 200, "Status check failed"
        assert resp.json()["database"]["accessible"], "Database not accessible"
        print("✅ PASSED")
    
    def test_auth_required(self):
        """Test that auth is required."""
        print("\n" + "="*60)
        print("TEST: Authentication Required")
        print("="*60)
        
        url = urljoin(self.base_url, "/api/v1/tools/get_database_stats")
        resp = self.session.get(url)  # No API key
        
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        
        assert resp.status_code == 401, "Should require auth"
        print("✅ PASSED")
    
    def test_query_machines(self):
        """Test query_machines endpoint."""
        print("\n" + "="*60)
        print("TEST: Query Machines")
        print("="*60)
        
        url = urljoin(self.base_url, "/api/v1/tools/query_machines")
        data = {
            "filters": {"mdm_enrolled": "No"},
            "limit": 5
        }
        
        resp = self.session.post(url, json=data, headers=self.headers)
        
        print(f"Status: {resp.status_code}")
        result = resp.json()
        print(f"Success: {result.get('success')}")
        print(f"Count: {result.get('count')}")
        
        if result.get('data'):
            print(f"First machine: {result['data'][0].get('hostname', 'N/A')}")
        
        assert resp.status_code == 200, "Query failed"
        assert result["success"], "Query not successful"
        print("✅ PASSED")
    
    def test_database_stats(self):
        """Test database stats endpoint."""
        print("\n" + "="*60)
        print("TEST: Database Stats")
        print("="*60)
        
        url = urljoin(self.base_url, "/api/v1/tools/get_database_stats")
        resp = self.session.get(url, headers=self.headers)
        
        print(f"Status: {resp.status_code}")
        result = resp.json()
        print(f"Success: {result.get('success')}")
        
        if result.get('data'):
            data = result['data']
            print(f"Tables: {data.get('total_tables')}")
            print(f"Size: {data.get('database_size_mb')} MB")
        
        assert resp.status_code == 200, "Query failed"
        assert result["success"], "Query not successful"
        print("✅ PASSED")
    
    def test_get_events(self):
        """Test get events endpoint."""
        print("\n" + "="*60)
        print("TEST: Get Events")
        print("="*60)
        
        url = urljoin(self.base_url, "/api/v1/tools/get_events")
        data = {
            "filters": {"type": ["error", "danger"]},
            "limit": 5
        }
        
        resp = self.session.post(url, json=data, headers=self.headers)
        
        print(f"Status: {resp.status_code}")
        result = resp.json()
        print(f"Success: {result.get('success')}")
        print(f"Count: {result.get('count')}")
        
        assert resp.status_code == 200, "Query failed"
        assert result["success"], "Query not successful"
        print("✅ PASSED")
    
    def run_all_tests(self):
        """Run all tests."""
        print("\n" + "#"*60)
        print("# Flask MunkiReport API Test Suite")
        print("#"*60)
        
        tests = [
            self.test_health,
            self.test_status,
            self.test_auth_required,
            self.test_query_machines,
            self.test_database_stats,
            self.test_get_events,
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                test()
                passed += 1
            except Exception as e:
                print(f"❌ FAILED: {e}")
                failed += 1
        
        print("\n" + "="*60)
        print(f"Tests passed: {passed}/{len(tests)}")
        print(f"Tests failed: {failed}/{len(tests)}")
        print("="*60)
        
        return failed == 0


def main():
    if len(sys.argv) < 3:
        print("Usage: python test_api.py <base_url> <api_key>")
        print("Example: python test_api.py http://localhost:5000 your-api-key")
        sys.exit(1)
    
    base_url = sys.argv[1]
    api_key = sys.argv[2]
    
    tester = APITester(base_url, api_key)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
