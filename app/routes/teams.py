from fastapi import APIRouter, HTTPException, Path, Query
from app.services.fpl_service import FPLService

router = APIRouter(
    prefix="/teams",
    tags=["teams"],
    responses={
        404: {"description": "Team not found"},
        500: {"description": "Internal server error"}
    }
)

@router.get(
    "/",
    summary="Get All Teams",
    description="Retrieve information about all Premier League teams",
    response_description="List of all teams with their details"
)
async def get_teams():
    """
    Get all Premier League teams.
    
    Returns:
        List[Dict]: List of teams with their details
    """
    try:
        # Get bootstrap-static data
        bootstrap_data = FPLService.get_bootstrap_static()
        
        # Return the teams list
        return bootstrap_data.get("teams", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{team_id}",
    summary="Get Team Details",
    description="Retrieve detailed information about a specific team",
    response_description="Detailed information about the specified team"
)
async def get_team(
    team_id: int = Path(..., description="The team ID", example=1)
):
    """
    Get a specific team by ID.
    
    Args:
        team_id (int): The team ID
        
    Returns:
        Dict: Team details
    """
    try:
        # Get bootstrap-static data
        bootstrap_data = FPLService.get_bootstrap_static()
        
        # Find the team with the given ID
        teams = bootstrap_data.get("teams", [])
        team = next((t for t in teams if t["id"] == team_id), None)
        
        # If team not found, return 404
        if not team:
            raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")
        
        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{team_id}/fixtures",
    summary="Get Team Fixtures",
    description="Retrieve all fixtures for a specific team",
    response_model=dict,
    responses={
        200: {
            "description": "Team fixtures retrieved successfully",
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
async def get_team_fixtures(
    team_id: int = Path(..., description="The ID of the team", example=1)
):
    try:
        return FPLService.get_team_fixtures(team_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 