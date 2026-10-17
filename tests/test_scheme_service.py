import pytest
from fastapi.testclient import TestClient
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'scheme-service'))

from main import app

client = TestClient(app)

class TestSchemeService:
    """Test Scheme Service endpoints"""
    
    def test_health_check(self):
        """Test health check"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    @pytest.fixture
    def sample_scheme(self):
        """Create a sample scheme"""
        return {
            "name": "Farmer Subsidy",
            "description": "Subsidy for small farmers",
            "ministry": "Department of Agriculture",
            "eligibility_rules": [
                {
                    "field": "age",
                    "operator": ">=",
                    "value": 18,
                    "description": "Applicant must be 18 or older"
                },
                {
                    "field": "land_size",
                    "operator": "<",
                    "value": 5,
                    "description": "Land should be less than 5 acres"
                },
                {
                    "field": "income",
                    "operator": "<=",
                    "value": 500000,
                    "description": "Annual income must be <= 5 lakhs"
                }
            ],
            "pseudocode": "IF age >= 18 AND land_size < 5 acres AND income <= 500000 THEN eligible",
            "form_fields": ["age", "land_size", "income", "state", "district"]
        }
    
    def test_create_scheme(self, sample_scheme):
        """Test creating a scheme"""
        response = client.post("/schemes", json=sample_scheme)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "draft"
        assert data["version"] == "v1.0"
        assert "scheme_id" in data
    
    def test_list_schemes_empty(self):
        """Test listing schemes (empty)"""
        response = client.get("/schemes")
        assert response.status_code == 200
        # Should be empty or have test data
    
    def test_get_scheme_not_found(self):
        """Test getting non-existent scheme"""
        response = client.get("/schemes/nonexistent-id")
        assert response.status_code == 404
    
    def test_update_scheme(self, sample_scheme):
        """Test updating a scheme (creates new version)"""
        # Create scheme
        create_response = client.post("/schemes", json=sample_scheme)
        scheme_id = create_response.json()["scheme_id"]
        
        # Update scheme
        update_data = {
            "description": "Updated description",
            "eligibility_rules": [
                {
                    "field": "age",
                    "operator": ">=",
                    "value": 21,
                    "description": "Applicant must be 21 or older"
                }
            ]
        }
        
        response = client.patch(f"/schemes/{scheme_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["new_version"] == "v1.1"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
