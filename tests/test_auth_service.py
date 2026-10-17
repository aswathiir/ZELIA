import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'auth-service'))

from main import app

client = TestClient(app)

@pytest.fixture
def valid_phone():
    return "9876543210"

@pytest.fixture
def valid_aadhaar_hash():
    # SHA256 hash of a test Aadhaar
    return "a" * 64

class TestAuthService:
    """Test Auth Service endpoints"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_send_otp_success(self, valid_phone):
        """Test successful OTP sending"""
        response = client.post(
            "/auth/send-otp",
            json={"phone_number": valid_phone}
        )
        assert response.status_code == 200
        assert "expires_in" in response.json()
    
    def test_send_otp_invalid_phone(self):
        """Test OTP sending with invalid phone"""
        response = client.post(
            "/auth/send-otp",
            json={"phone_number": "123"}  # Too short
        )
        assert response.status_code == 400
    
    def test_send_otp_rate_limit(self, valid_phone):
        """Test OTP rate limiting"""
        # Send 5 OTPs (should succeed)
        for i in range(5):
            response = client.post(
                "/auth/send-otp",
                json={"phone_number": valid_phone}
            )
            assert response.status_code == 200
        
        # 6th OTP should fail
        response = client.post(
            "/auth/send-otp",
            json={"phone_number": valid_phone}
        )
        assert response.status_code == 429
    
    def test_verify_otp_invalid_otp(self, valid_phone, valid_aadhaar_hash):
        """Test OTP verification with invalid OTP"""
        # First send OTP
        client.post("/auth/send-otp", json={"phone_number": valid_phone})
        
        # Try to verify with wrong OTP
        response = client.post(
            "/auth/verify-otp",
            json={
                "phone_number": valid_phone,
                "otp_code": "000000",
                "aadhaar_hash": valid_aadhaar_hash
            }
        )
        assert response.status_code == 401

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
