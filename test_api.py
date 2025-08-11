#!/usr/bin/env python
"""
Quick API test script for PyBiorythm Django API Server

This script demonstrates basic API usage and tests key endpoints.
"""

import requests
import json
import sys
from datetime import date, timedelta

# Configuration
BASE_URL = "http://127.0.0.1:8001/api"
AUTH_TOKEN = None  # Will be set after reading from file or environment


def load_token():
    """Load API token from file or environment."""
    global AUTH_TOKEN
    
    # Try to load from auth_token.txt file
    try:
        with open('auth_token.txt', 'r') as f:
            content = f.read()
            # Extract token from file content
            for line in content.split('\n'):
                if 'Token' in line and ':' in line:
                    AUTH_TOKEN = line.split()[-1]
                    break
        
        if AUTH_TOKEN:
            print(f"✅ Loaded API token from auth_token.txt")
            return True
    except FileNotFoundError:
        pass
    
    # Try environment variable
    import os
    AUTH_TOKEN = os.getenv('API_TOKEN')
    if AUTH_TOKEN:
        print(f"✅ Loaded API token from environment")
        return True
    
    print("❌ No API token found. Please:")
    print("1. Run ./setup.sh to create a token")
    print("2. Or set API_TOKEN environment variable")
    print("3. Or manually create auth_token.txt with your token")
    return False


def get_headers():
    """Get HTTP headers with authentication."""
    return {
        "Authorization": f"Token {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }


def test_api_connection():
    """Test basic API connection."""
    print("\n🔗 Testing API connection...")
    
    try:
        response = requests.get(f"{BASE_URL}/", headers=get_headers())
        if response.status_code == 200:
            print("✅ API connection successful")
            return True
        else:
            print(f"❌ API connection failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False


def test_people_endpoints():
    """Test people management endpoints."""
    print("\n👥 Testing people endpoints...")
    
    # List people
    response = requests.get(f"{BASE_URL}/people/", headers=get_headers())
    if response.status_code == 200:
        people = response.json()
        print(f"✅ Listed {len(people.get('results', []))} people")
        
        if people.get('results'):
            person_id = people['results'][0]['id']
            person_name = people['results'][0]['name']
            print(f"📊 Found person: {person_name} (ID: {person_id})")
            return person_id
    else:
        print(f"❌ Failed to list people: {response.status_code}")
    
    return None


def test_biorhythm_data(person_id):
    """Test biorhythm data endpoints."""
    if not person_id:
        print("\n⏭️  Skipping biorhythm data tests (no person found)")
        return
    
    print(f"\n📊 Testing biorhythm data for person {person_id}...")
    
    # Get biorhythm data
    response = requests.get(
        f"{BASE_URL}/people/{person_id}/biorhythm_data/",
        headers=get_headers(),
        params={"limit": 10}
    )
    
    if response.status_code == 200:
        data = response.json()
        biorhythm_data = data.get('biorhythm_data', [])
        print(f"✅ Retrieved {len(biorhythm_data)} biorhythm data points")
        
        if biorhythm_data:
            latest = biorhythm_data[0]
            print(f"📅 Latest data: {latest['date']}")
            print(f"🏃 Physical: {latest['physical']:.3f}")
            print(f"💭 Emotional: {latest['emotional']:.3f}")
            print(f"🧠 Intellectual: {latest['intellectual']:.3f}")
    else:
        print(f"❌ Failed to get biorhythm data: {response.status_code}")


def test_statistics(person_id):
    """Test statistics endpoint."""
    if not person_id:
        print("\n⏭️  Skipping statistics tests (no person found)")
        return
    
    print(f"\n📈 Testing statistics for person {person_id}...")
    
    response = requests.get(
        f"{BASE_URL}/people/{person_id}/statistics/",
        headers=get_headers()
    )
    
    if response.status_code == 200:
        stats = response.json()
        print("✅ Retrieved statistics")
        
        if 'statistics' in stats:
            stat_data = stats['statistics']
            if 'total_data_points' in stat_data:
                print(f"📊 Total data points: {stat_data['total_data_points']}")
            
            if 'critical_days' in stat_data:
                critical = stat_data['critical_days']
                print(f"⚠️  Critical days: {critical.get('total', 0)}")
    else:
        print(f"❌ Failed to get statistics: {response.status_code}")


def test_calculation_endpoint():
    """Test real-time calculation endpoint."""
    print("\n🧮 Testing calculation endpoint...")
    
    # First, we need a person to calculate for
    response = requests.get(f"{BASE_URL}/people/", headers=get_headers())
    if response.status_code != 200:
        print("❌ Cannot test calculation - no people available")
        return
    
    people = response.json().get('results', [])
    if not people:
        print("❌ Cannot test calculation - no people in database")
        return
    
    person_id = people[0]['id']
    
    # Test calculation
    calc_data = {
        "person_id": person_id,
        "days": 7,
        "notes": "API test calculation"
    }
    
    response = requests.post(
        f"{BASE_URL}/calculations/calculate/",
        headers=get_headers(),
        json=calc_data
    )
    
    if response.status_code == 201:
        result = response.json()
        print("✅ Calculation successful")
        print(f"📊 Created {result.get('data_points_created', 0)} data points")
    else:
        print(f"❌ Calculation failed: {response.status_code}")
        if response.content:
            print(f"Error: {response.text}")


def main():
    """Run all API tests."""
    print("🚀 PyBiorythm Django API Server - Test Script")
    print("=" * 50)
    
    # Load authentication token
    if not load_token():
        sys.exit(1)
    
    # Test API connection
    if not test_api_connection():
        print("\n❌ Cannot connect to API. Make sure the server is running:")
        print("   uv run daphne biorhythm_api.asgi:application -p 8001")
        sys.exit(1)
    
    # Run tests
    person_id = test_people_endpoints()
    test_biorhythm_data(person_id)
    test_statistics(person_id)
    test_calculation_endpoint()
    
    print("\n✨ API testing completed!")
    print("\n📖 Next steps:")
    print("1. Explore the browsable API: http://127.0.0.1:8001/api/")
    print("2. Check Django Admin: http://127.0.0.1:8001/admin/")
    print("3. Review API documentation in README.md")


if __name__ == '__main__':
    main()