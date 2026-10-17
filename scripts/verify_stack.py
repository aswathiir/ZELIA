import requests
import subprocess
import sys

def check_service(name, url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✓ {name} is UP ({url})")
        else:
            print(f"✗ {name} returned {response.status_code}")
    except Exception as e:
        print(f"✗ {name} is DOWN ({url}) - {str(e)}")

def check_internal_ocr():
    print("\nRunning Internal OCR validation (inside container)...")
    try:
        # Run docker-compose exec
        # We use shell=True for windows convenience with docker-compose commands sometimes, 
        # but list format is safer.
        result = subprocess.run(
            ["docker-compose", "exec", "-T", "ocr-service", "python", "test_ocr_internal.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ Internal OCR Test Passed")
            print(result.stdout)
        else:
            print("✗ Internal OCR Test Failed")
            print(result.stderr)
            print(result.stdout)
    except Exception as e:
        print(f"✗ Failed to run docker command: {e}")

def main():
    print("=== ZELIA Stack Verification (Python) ===\n")
    
    print("Checking HTTP Health Endpoints...")
    check_service("Embedding Service", "http://localhost:8001/health")
    check_service("OCR Service",       "http://localhost:8002/health")
    check_service("Layout Service",    "http://localhost:8003/health")
    check_service("n8n",               "http://localhost:5678")
    check_service("MinIO Console",     "http://localhost:9001/login")
    check_service("MinIO API",         "http://localhost:9005/minio/health/live")
    
    check_internal_ocr()
    print("\nVerification Complete.")

if __name__ == "__main__":
    main()
