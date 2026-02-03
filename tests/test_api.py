"""
Tests for the Mergington High School API
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
    
    # Restore original state
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check structure of first activity
        first_activity = list(data.values())[0]
        assert "description" in first_activity
        assert "schedule" in first_activity
        assert "max_participants" in first_activity
        assert "participants" in first_activity
    
    def test_get_activities_contains_expected_activities(self, client):
        """Test that response contains expected activities"""
        response = client.get("/activities")
        data = response.json()
        
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data


class TestSignup:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup"""
        test_email = "test@mergington.edu"
        activity_name = "Chess Club"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()[activity_name]["participants"]
        
        # Sign up
        response = client.post(
            f"/activities/{activity_name}/signup?email={test_email}"
        )
        assert response.status_code == 200
        assert response.json()["message"] == f"Signed up {test_email} for {activity_name}"
        
        # Verify participant was added
        updated_response = client.get("/activities")
        updated_participants = updated_response.json()[activity_name]["participants"]
        assert test_email in updated_participants
        assert len(updated_participants) == len(initial_participants) + 1
    
    def test_signup_duplicate_fails(self, client):
        """Test that duplicate signup fails"""
        test_email = "duplicate@mergington.edu"
        activity_name = "Programming Class"
        
        # First signup
        response1 = client.post(
            f"/activities/{activity_name}/signup?email={test_email}"
        )
        assert response1.status_code == 200
        
        # Second signup (duplicate)
        response2 = client.post(
            f"/activities/{activity_name}/signup?email={test_email}"
        )
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"]
    
    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signup for non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_signup_with_special_characters_in_email(self, client):
        """Test signup with special characters in email"""
        from urllib.parse import quote
        
        test_email = "test+special@mergington.edu"
        activity_name = "Drama Club"
        
        response = client.post(
            f"/activities/{activity_name}/signup?email={quote(test_email)}"
        )
        assert response.status_code == 200
        
        # Verify participant was added
        updated_response = client.get("/activities")
        updated_participants = updated_response.json()[activity_name]["participants"]
        assert test_email in updated_participants


class TestUnregister:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration"""
        test_email = "unregister@mergington.edu"
        activity_name = "Science Club"
        
        # First sign up
        client.post(f"/activities/{activity_name}/signup?email={test_email}")
        
        # Verify signed up
        response = client.get("/activities")
        participants_before = response.json()[activity_name]["participants"]
        assert test_email in participants_before
        
        # Unregister
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={test_email}"
        )
        assert response.status_code == 200
        assert response.json()["message"] == f"Unregistered {test_email} from {activity_name}"
        
        # Verify unregistered
        response = client.get("/activities")
        participants_after = response.json()[activity_name]["participants"]
        assert test_email not in participants_after
        assert len(participants_after) == len(participants_before) - 1
    
    def test_unregister_not_registered_fails(self, client):
        """Test that unregistering a non-registered participant fails"""
        test_email = "notregistered@mergington.edu"
        activity_name = "Basketball Team"
        
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={test_email}"
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]
    
    def test_unregister_nonexistent_activity_fails(self, client):
        """Test that unregistering from non-existent activity fails"""
        response = client.delete(
            "/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant from initial data"""
        activity_name = "Chess Club"
        existing_email = "michael@mergington.edu"
        
        # Verify participant exists
        response = client.get("/activities")
        participants_before = response.json()[activity_name]["participants"]
        assert existing_email in participants_before
        
        # Unregister
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={existing_email}"
        )
        assert response.status_code == 200
        
        # Verify removed
        response = client.get("/activities")
        participants_after = response.json()[activity_name]["participants"]
        assert existing_email not in participants_after


class TestIntegration:
    """Integration tests for multiple operations"""
    
    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow of signup and unregister"""
        test_email = "workflow@mergington.edu"
        activity_name = "Swimming Club"
        
        # Get initial state
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()[activity_name]["participants"]
        initial_count = len(initial_participants)
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup?email={test_email}"
        )
        assert signup_response.status_code == 200
        
        # Verify added
        after_signup = client.get("/activities")
        after_signup_participants = after_signup.json()[activity_name]["participants"]
        assert len(after_signup_participants) == initial_count + 1
        assert test_email in after_signup_participants
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity_name}/unregister?email={test_email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify removed
        after_unregister = client.get("/activities")
        after_unregister_participants = after_unregister.json()[activity_name]["participants"]
        assert len(after_unregister_participants) == initial_count
        assert test_email not in after_unregister_participants
    
    def test_multiple_signups_different_activities(self, client):
        """Test signing up for multiple activities"""
        test_email = "multi@mergington.edu"
        activities_to_join = ["Chess Club", "Art Studio", "Debate Team"]
        
        for activity_name in activities_to_join:
            response = client.post(
                f"/activities/{activity_name}/signup?email={test_email}"
            )
            assert response.status_code == 200
        
        # Verify all signups
        all_activities = client.get("/activities").json()
        for activity_name in activities_to_join:
            assert test_email in all_activities[activity_name]["participants"]
