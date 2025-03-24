#!/usr/bin/env python3
"""
Simple test script to verify the API works without models.py
Run this after removing models.py to ensure all endpoints are working.
"""

import requests
import sys
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint: str, expected_status: int = 200) -> Dict[str, Any]:
    """Test an API endpoint and return the response."""
    url = f"{BASE_URL}{endpoint}"
    print(f"Testing: {url}")
    
    try:
        response = requests.get(url)
        status = response.status_code
        
        if status == expected_status:
            print(f"✅ Status: {status}")
            try:
                return response.json()
            except json.JSONDecodeError:
                print("❌ Could not parse JSON response")
                return {}
        else:
            print(f"❌ Status: {status} (expected {expected_status})")
            return {}
    except requests.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
        return {}

def main():
    """Run tests for all endpoints."""
    # Make sure the API is running
    print("🔍 Testing FPL API endpoints without models.py")
    print("=============================================\n")
    
    # Test root endpoints
    test_endpoint("/")
    test_endpoint("/health")
    
    # Test team endpoints
    test_endpoint("/teams")
    test_endpoint("/teams/1")
    
    # Test players endpoints
    test_endpoint("/players")
    test_endpoint("/players/1")
    test_endpoint("/players/1/summary")
    test_endpoint("/players/1/history")
    test_endpoint("/players/by-team/1")
    
    # Test events endpoints
    test_endpoint("/events")
    test_endpoint("/events/1")
    test_endpoint("/events/1/live")
    
    # Test fixtures endpoints
    test_endpoint("/fixtures")
    test_endpoint("/fixtures/1")
    
    # Test entry endpoints (these might fail if the manager ID doesn't exist)
    test_endpoint("/entry/1234567", expected_status=404)
    
    # Test league endpoints (these might fail if the league ID doesn't exist)
    test_endpoint("/leagues-classic/12345/standings", expected_status=404)
    
    print("\n✅ Tests completed")

if __name__ == "__main__":
    main() 