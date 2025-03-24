from fastapi import APIRouter, HTTPException, Path, Query
from app.services.fpl_service import FPLService
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

router = APIRouter(
    prefix="/events",
    tags=["events"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

@router.get(
    "/",
    summary="Get all gameweeks",
    description="Retrieve information about all gameweeks in the current season",
    response_description="List of all gameweeks with their details"
)
async def get_events():
    """
    Get all gameweeks in the current season.
    
    Returns:
        List[Dict]: List of gameweeks with their details
    """
    try:
        return FPLService.get_events()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{event_id}",
    summary="Get specific gameweek",
    description="Retrieve detailed information about a specific gameweek",
    response_description="Detailed information about the specified gameweek"
)
async def get_event(
    event_id: int = Path(..., description="The gameweek number", example=1)
):
    """
    Get a specific gameweek.
    
    Args:
        event_id (int): The gameweek number
        
    Returns:
        Dict: Gameweek details
    """
    try:
        return FPLService.get_event(event_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{event_id}/live",
    summary="Get live gameweek data",
    description="Retrieve live data for the specified gameweek",
    response_description="Live data for the specified gameweek"
)
async def get_event_live(
    event_id: int = Path(..., description="The gameweek number", example=1)
):
    """
    Get live data for a specific gameweek.
    
    Args:
        event_id (int): The gameweek number
        
    Returns:
        Dict: Live gameweek data
    """
    try:
        return FPLService.get_event_live(event_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 