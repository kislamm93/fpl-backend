from fastapi import APIRouter, HTTPException, Path
from app.services.fpl_service import FPLService
import logging

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

# Registered before /{event_id} on purpose: that route parses the path segment
# as an int, so "upcoming" would 422 there if it matched first.
@router.get(
    "/upcoming",
    summary="Get the upcoming gameweek",
    description="The gameweek being picked for — the first one that isn't finished",
    response_description="Details of the upcoming gameweek"
)
async def get_upcoming_event():
    """
    Get the gameweek to pick for.

    Returns:
        Dict: Upcoming gameweek details
    """
    try:
        return FPLService.get_upcoming_event()
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