from fastapi import APIRouter, HTTPException, Path, Query
from app.services.fpl_service import FPLService
from typing import Optional

router = APIRouter(
    prefix="/fixtures",
    tags=["fixtures"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

@router.get(
    "/",
    summary="Get all fixtures",
    description="Retrieve all fixtures for the Premier League season. Optionally filter by gameweek.",
    response_description="List of fixtures with details"
)
async def get_fixtures(
    event: Optional[int] = Query(None, description="Filter fixtures by gameweek number", example=1)
):
    """
    Get all fixtures in the current FPL season, with an optional gameweek filter.
    
    Args:
        event (int, optional): Filter by gameweek
        
    Returns:
        List[Dict]: List of fixtures with details
    """
    try:
        if event:
            # If event parameter is provided, filter fixtures by event
            return FPLService.get_fixtures_by_event(event)
        
        # Otherwise, return all fixtures
        return FPLService.get_fixtures()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{fixture_id}",
    summary="Get specific fixture",
    description="Retrieve detailed information about a specific fixture",
    response_description="Detailed information about the specified fixture"
)
async def get_fixture(
    fixture_id: int = Path(..., description="The fixture ID", example=1)
):
    """
    Get details for a specific fixture.
    
    Args:
        fixture_id (int): The fixture ID
        
    Returns:
        Dict: Fixture details
    """
    try:
        return FPLService.get_fixture(fixture_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/event/{event_id}",
    summary="Get Event Fixtures",
    description="Retrieve all fixtures for a specific gameweek",
    response_model=dict,
    responses={
        200: {
            "description": "Event fixtures retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "code": 1,
                            "event": 1,
                            "finished": True,
                            "finished_provisional": True,
                            "kickoff_time": "2024-01-01T12:00:00Z",
                            "minutes": 90,
                            "provisional_start_time": False,
                            "started": True,
                            "team_a": 1,
                            "team_a_score": 2,
                            "team_h": 2,
                            "team_h_score": 1,
                            "stats": [
                                {
                                    "identifier": "goals_scored",
                                    "a": 1,
                                    "h": 2
                                }
                            ],
                            "team_h_difficulty": 3,
                            "team_a_difficulty": 4
                        }
                    ]
                }
            }
        }
    }
)
async def get_event_fixtures(
    event_id: int = Path(..., description="The ID of the gameweek", example=1)
):
    try:
        return FPLService.get_event_fixtures(event_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 