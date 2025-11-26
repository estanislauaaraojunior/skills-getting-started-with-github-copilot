"""
Tests for Mergington High School API

This module contains comprehensive tests for the FastAPI application,
including activity listing, signup functionality, and error handling.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI application"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        },
    }
    
    # Reset to original state
    activities.clear()
    activities.update(original_activities)
    
    yield
    
    # Clean up after test
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_index(self, client):
        """Test that root path redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_all_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_activity_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)
            assert isinstance(activity_details["max_participants"], int)
    
    def test_activity_participants_are_valid_emails(self, client):
        """Test that participant emails contain @ symbol"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            for participant in activity_details["participants"]:
                assert "@" in participant


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_student(self, client):
        """Test signing up a new student for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify student was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_duplicate_student(self, client):
        """Test that signing up the same student twice returns an error"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"].lower()
    
    def test_signup_nonexistent_activity(self, client):
        """Test signing up for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signing up for activities with special characters"""
        # Add an activity with special characters for testing
        activities["Art & Craft"] = {
            "description": "Creative arts",
            "schedule": "Mondays",
            "max_participants": 10,
            "participants": []
        }
        
        response = client.post(
            "/activities/Art & Craft/signup",
            params={"email": "artist@mergington.edu"}
        )
        assert response.status_code == 200
    
    def test_signup_multiple_students_different_activities(self, client):
        """Test multiple students signing up for different activities"""
        students = [
            ("student1@mergington.edu", "Chess Club"),
            ("student2@mergington.edu", "Programming Class"),
            ("student3@mergington.edu", "Gym Class"),
        ]
        
        for email, activity in students:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all signups
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        for email, activity in students:
            assert email in activities_data[activity]["participants"]
    
    def test_signup_preserves_existing_participants(self, client):
        """Test that signing up a new student doesn't remove existing ones"""
        # Get initial participants
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()["Chess Club"]["participants"].copy()
        
        # Sign up new student
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "newbie@mergington.edu"}
        )
        
        # Check all original participants are still there
        final_response = client.get("/activities")
        final_participants = final_response.json()["Chess Club"]["participants"]
        
        for participant in initial_participants:
            assert participant in final_participants
        assert "newbie@mergington.edu" in final_participants


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""
    
    def test_signup_with_empty_email(self, client):
        """Test signing up with an empty email"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": ""}
        )
        # Should still process (validation could be added)
        assert response.status_code in [200, 400, 422]
    
    def test_activity_name_case_sensitivity(self, client):
        """Test that activity names are case-sensitive"""
        response = client.post(
            "/activities/chess club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
    
    def test_get_activities_returns_json(self, client):
        """Test that activities endpoint returns valid JSON"""
        response = client.get("/activities")
        assert response.headers["content-type"] == "application/json"


class TestDataIntegrity:
    """Tests for data integrity and consistency"""
    
    def test_max_participants_not_exceeded(self, client):
        """Test that participant count doesn't exceed max_participants"""
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        for activity_name, activity_details in activities_data.items():
            participant_count = len(activity_details["participants"])
            max_count = activity_details["max_participants"]
            assert participant_count <= max_count, \
                f"{activity_name} has {participant_count} participants but max is {max_count}"
    
    def test_no_duplicate_participants_in_activity(self, client):
        """Test that an activity doesn't have duplicate participants"""
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        for activity_name, activity_details in activities_data.items():
            participants = activity_details["participants"]
            assert len(participants) == len(set(participants)), \
                f"{activity_name} has duplicate participants"
