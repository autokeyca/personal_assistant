#!/usr/bin/env python3
"""Test script for Jarvis Agent API."""

import requests
import json

# Configuration
API_URL = "http://127.0.0.1:8000"
API_KEY = "nU9W9FzaMkjfBRe1DJEit7fSjSP4E3SytinNp7ev38Y"  # Replace with your actual key

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


def test_health_check():
    """Test health check endpoint."""
    print("\n=== Health Check ===")
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")


def test_send_message():
    """Test sending a message."""
    print("\n=== Send Message ===")
    data = {
        "message": "🤖 Test message from external agent via API!",
        "parse_mode": "Markdown"
    }
    response = requests.post(f"{API_URL}/message", headers=headers, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")


def test_create_task():
    """Test creating a task."""
    print("\n=== Create Task ===")
    data = {
        "title": "Test task from API",
        "description": "This task was created by an external agent via the API",
        "priority": "medium"
    }
    response = requests.post(f"{API_URL}/task", headers=headers, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json().get("id")


def test_list_tasks():
    """Test listing tasks."""
    print("\n=== List Tasks ===")
    response = requests.get(f"{API_URL}/tasks?limit=5", headers=headers)
    print(f"Status: {response.status_code}")
    tasks = response.json()
    print(f"Found {len(tasks)} tasks:")
    for task in tasks:
        print(f"  #{task['id']}: {task['title']} [{task['status']}]")


def test_get_status():
    """Test getting Jarvis status."""
    print("\n=== Get Status ===")
    response = requests.get(f"{API_URL}/status", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def main():
    """Run all tests."""
    print("Testing Jarvis Agent API")
    print("=" * 60)

    try:
        # Health check (no auth required)
        test_health_check()

        # Authenticated endpoints
        test_get_status()
        test_list_tasks()
        test_send_message()
        test_create_task()

        print("\n" + "=" * 60)
        print("✅ All tests completed!")

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API server.")
        print("Make sure the API server is running: python run_api.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
