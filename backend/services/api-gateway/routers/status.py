from fastapi import APIRouter
import httpx
import asyncio
from typing import Dict, Any

router = APIRouter()

# Service endpoints
SERVICES = {
    "ocr": "http://ocr-service:8002/health",
    "layout": "http://layout-worker:8003/health",
    "embedding": "http://embedding-service:8001/health",
    "submission": "http://submission-service:8004/health",
    "minio": "http://minio:9000/minio/health/live",
    "n8n": "http://n8n:5678",
}

async def check_service(name: str, url: str) -> Dict[str, Any]:
    """Check if a service is healthy."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return {"name": name, "status": "healthy", "code": response.status_code}
            else:
                return {"name": name, "status": "degraded", "code": response.status_code}
    except httpx.ConnectError:
        return {"name": name, "status": "unreachable", "error": "Connection refused"}
    except httpx.TimeoutException:
        return {"name": name, "status": "timeout", "error": "Request timed out"}
    except Exception as e:
        return {"name": name, "status": "error", "error": str(e)}

async def check_database() -> Dict[str, Any]:
    """Check database connection."""
    try:
        from database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return {"name": "postgres", "status": "healthy"}
    except Exception as e:
        return {"name": "postgres", "status": "error", "error": str(e)}

@router.get("/")
async def system_status():
    """
    Get health status of all system components.
    Returns a summary of each service's health.
    """
    # Check all services concurrently
    tasks = [check_service(name, url) for name, url in SERVICES.items()]
    tasks.append(check_database())
    
    results = await asyncio.gather(*tasks)
    
    # Compute overall status
    all_healthy = all(r["status"] == "healthy" for r in results)
    some_healthy = any(r["status"] == "healthy" for r in results)
    
    if all_healthy:
        overall = "healthy"
    elif some_healthy:
        overall = "degraded"
    else:
        overall = "critical"
    
    return {
        "overall_status": overall,
        "services": {r["name"]: r for r in results},
        "healthy_count": sum(1 for r in results if r["status"] == "healthy"),
        "total_count": len(results)
    }

@router.get("/quick")
async def quick_status():
    """Quick status check - just returns API Gateway status."""
    return {"status": "up", "service": "api-gateway"}
