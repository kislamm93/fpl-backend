from fastapi import APIRouter, HTTPException
from app.services.fpl_service import FPLService

router = APIRouter(tags=["root"])

@router.get(
    "/",
    summary="Root Endpoint",
    description="Welcome to the FPL API",
    response_description="Welcome message and status"
)
async def root():
    """
    Root endpoint of the API.
    
    Returns:
        Dict: Welcome message and status
    """
    return {
        "message": "Welcome to the FPL API",
        "status": "online",
        "docs": "/docs"
    }

@router.get(
    "/health",
    summary="Health Check",
    description="Check if the API is healthy and all required services are available",
    response_description="Health status of the API"
)
async def health_check():
    """
    Check if the API is healthy and can connect to required services.
    
    Returns:
        Dict: Health status with details
    """
    try:
        # Test connection to FPL API
        bootstrap_data = FPLService.get_bootstrap_static()
        fpl_status = "ok" if bootstrap_data else "error"
        
        # Overall health status
        status = "healthy" if fpl_status == "ok" else "unhealthy"
        
        return {
            "status": status,
            "services": {
                "fpl_api": fpl_status
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 