import requests
import json
import logging
import argparse
from typing import Optional

# Configure logging for verbosity
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("API_Verifier")

class APIVerifier:
    """
    A modular class for verifying ZELIA API endpoints.
    Handles session state (e.g. auth tokens) and makes verbose requests.
    """
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.token: Optional[str] = None

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """Internal helper to execute requests and inject auth token if present."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Executing Request: {method} {url} | kwargs: {kwargs}")
        
        # Inject authorization header if token exists and headers aren't explicitly passed
        if self.token and "headers" not in kwargs:
            kwargs["headers"] = {"Authorization": f"Bearer {self.token}"}
            
        try:
            resp = self.session.request(method, url, **kwargs)
            logger.debug(f"Received Response: {resp.status_code} - {resp.text}")
            return resp
        except requests.RequestException as e:
            logger.error(f"Request failed: {method} {url} | Error: {e}")
            return None

    def verify_health(self) -> bool:
        """Step 1: Verify the API Health Check."""
        logger.info("=== [1] Testing Health Check ===")
        resp = self._request("GET", "/health")
        
        if resp and resp.status_code == 200:
            logger.info("✓ Health Check Passed")
            return True
        else:
            status = resp.status_code if resp else "Connection Failed"
            logger.error(f"✗ Health Check Failed: {status}")
            return False

    def verify_auth(self, username: str = "chw", password: str = "password123") -> bool:
        """Step 2: Verify Authentication and token retrieval."""
        logger.info("=== [2] Testing Authentication ===")
        payload = {"username": username, "password": password}
        
        resp = self._request("POST", "/auth/login", json=payload)
        
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                self.token = data.get("access_token")
                if self.token:
                    logger.info(f"✓ Login Successful. Token obtained: {self.token[:15]}...")
                    return True
            except json.JSONDecodeError:
                logger.error("✗ Login Failed: Invalid JSON in response")
        
        status = resp.status_code if resp else "Connection Failed"
        text = resp.text if resp else "No Response"
        logger.error(f"✗ Login Failed: {status} - {text}")
        return False

    def verify_schemes(self) -> bool:
        """Step 3: Verify the Schemes endpoint."""
        logger.info("=== [3] Testing Schemes Endpoint ===")
        resp = self._request("GET", "/schemes/")
        
        if not resp or resp.status_code != 200:
            status = resp.status_code if resp else "Connection Failed"
            text = resp.text if resp else "No Response"
            logger.error(f"✗ Schemes Request Failed: {status} - {text}")
            return False
            
        try:
            schemes = resp.json()
            logger.info(f"✓ Schemes List Retrieved: {len(schemes)} items")
            
            if len(schemes) == 0:
                logger.info("List is empty. Attempting to CREATE a test scheme...")
                return self._create_test_scheme()
            else:
                logger.info(f"Example Scheme found: {schemes[0].get('name', 'N/A')}")
                return True
                
        except json.JSONDecodeError:
            logger.error("✗ Failed to decode schemes JSON response")
            return False

    def _create_test_scheme(self) -> bool:
        """Helper to create a test scheme if the list is empty."""
        new_scheme = {
            "name": "Integration Test Scheme",
            "description": "Created by verify_api.py",
            "criteria": {"min_age": 18},
            "benefits": "Verification Success"
        }
        
        resp = self._request("POST", "/schemes/", json=new_scheme)
        
        if resp and resp.status_code == 200:
            try:
                created = resp.json()
                logger.info(f"✓ Created Scheme: {created.get('name')} (ID: {created.get('id', 'N/A')})")
                return True
            except json.JSONDecodeError:
                logger.error("✗ Created scheme response is not valid JSON")
                return False
                
        status = resp.status_code if resp else "Connection Failed"
        text = resp.text if resp else "No Response"
        logger.error(f"✗ Creation Failed: {status} - {text}")
        return False

    def run_all(self):
        """Execute the entire verification suite sequentially."""
        logger.info(f"Starting ZELIA API Gateway Verification for: {self.base_url}")
        
        # Abort if health check fails, as API is likely down
        if not self.verify_health():
            logger.critical("Aborting verification due to health check failure.")
            return
            
        self.verify_auth()
        self.verify_schemes()
        logger.info("API Verification Completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZELIA API Gateway Verification Script")
    parser.add_argument(
        "--url", 
        default="http://localhost:8000", 
        help="Base URL of the API gateway (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Enable verbose debug logging (shows full request/response data)"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    verifier = APIVerifier(base_url=args.url)
    verifier.run_all()
