"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root endpoint redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that get activities returns 200 status code"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that all activities are returned"""
        response = client.get("/activities")
        data = response.json()
        
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        assert "Basketball Team" in data
        
    def test_get_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_signup_adds_participant(self, client):
        """Test that signup actually adds participant to the activity"""
        email = "teststudent@mergington.edu"
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]
    
    def test_signup_duplicate_fails(self, client):
        """Test that signing up twice for the same activity fails"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_signup_with_special_characters_in_name(self, client):
        """Test signup with activity name that has special characters"""
        response = client.post(
            "/activities/Art Studio/signup?email=artist@mergington.edu"
        )
        assert response.status_code == 200


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/signup endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        email = "test@mergington.edu"
        
        # First sign up
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Then unregister
        response = client.delete(f"/activities/Chess Club/signup?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes participant from the activity"""
        email = "removeme@mergington.edu"
        
        # Sign up
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Unregister
        client.delete(f"/activities/Chess Club/signup?email={email}")
        
        # Verify participant was removed
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Chess Club"]["participants"]
    
    def test_unregister_not_signed_up_fails(self, client):
        """Test that unregistering when not signed up fails"""
        response = client.delete(
            "/activities/Chess Club/signup?email=notsignedup@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()
    
    def test_unregister_nonexistent_activity_fails(self, client):
        """Test that unregistering from non-existent activity fails"""
        response = client.delete(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        # Michael is already signed up for Chess Club in the initial data
        response = client.delete(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify removal
        response = client.get("/activities")
        data = response.json()
        assert "michael@mergington.edu" not in data["Chess Club"]["participants"]


class TestActivityCapacity:
    """Tests for activity capacity handling"""
    
    def test_multiple_signups_within_capacity(self, client):
        """Test that multiple students can sign up within capacity"""
        emails = [f"student{i}@mergington.edu" for i in range(3)]
        
        for email in emails:
            response = client.post(f"/activities/Chess Club/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all added
        response = client.get("/activities")
        data = response.json()
        for email in emails:
            assert email in data["Chess Club"]["participants"]


class TestEndToEndWorkflow:
    """Tests for complete user workflows"""
    
    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow of signing up and unregistering"""
        email = "workflow@mergington.edu"
        activity = "Programming Class"
        
        # Get initial state
        response = client.get("/activities")
        initial_participants = response.json()[activity]["participants"].copy()
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        response = client.delete(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify back to initial state
        response = client.get("/activities")
        assert response.json()[activity]["participants"] == initial_participants
