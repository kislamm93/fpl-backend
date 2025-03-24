from fastapi import APIRouter, HTTPException, Path, Query
from app.services.fpl_service import FPLService
from typing import Optional

router = APIRouter(
    prefix="/players",
    tags=["players"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

@router.get(
    "/",
    summary="Get All Players",
    description="Retrieve information about all players in the FPL game",
    response_description="List of all players with their details"
)
async def get_players():
    """
    Get all players in the FPL game.
    
    Returns:
        List[Dict]: List of players with their details
    """
    try:
        # Get bootstrap-static data
        bootstrap_data = FPLService.get_bootstrap_static()
        
        # Return the players list
        return bootstrap_data.get("elements", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{player_id}",
    summary="Get Player Details",
    description="Retrieve detailed information about a specific player",
    response_description="Detailed information about the specified player"
)
async def get_player(
    player_id: int = Path(..., description="The player ID", example=1)
):
    """
    Get a specific player by ID.
    
    Args:
        player_id (int): The player ID
        
    Returns:
        Dict: Player details
    """
    try:
        # Get bootstrap-static data
        bootstrap_data = FPLService.get_bootstrap_static()
        
        # Find the player with the given ID
        players = bootstrap_data.get("elements", [])
        player = next((p for p in players if p["id"] == player_id), None)
        
        # If player not found, return 404
        if not player:
            raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")
        
        return player
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{player_id}/summary",
    summary="Get Player Summary",
    description="Retrieve summary information for a specific player including recent form",
    response_description="Summary information about the specified player"
)
async def get_player_summary(
    player_id: int = Path(..., description="The player ID", example=1)
):
    """
    Get summary information for a specific player.
    
    Args:
        player_id (int): The player ID
        
    Returns:
        Dict: Player summary information
    """
    try:
        return FPLService.get_player_summary(player_id)
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/by-team/{team_id}",
    summary="Get Players by Team",
    description="Retrieve all players from a specific team",
    response_description="List of players from the specified team"
)
async def get_players_by_team(
    team_id: int = Path(..., description="The team ID", example=1),
    position: Optional[int] = Query(None, description="Filter by position (1-4)", example=1)
):
    """
    Get all players from a specific team.
    
    Args:
        team_id (int): The team ID
        position (int, optional): Filter by position (1: GKP, 2: DEF, 3: MID, 4: FWD)
        
    Returns:
        List[Dict]: List of players from the specified team
    """
    try:
        # Get bootstrap-static data
        bootstrap_data = FPLService.get_bootstrap_static()
        
        # Filter players by team ID
        players = bootstrap_data.get("elements", [])
        team_players = [p for p in players if p["team"] == team_id]
        
        # Further filter by position if specified
        if position is not None:
            team_players = [p for p in team_players if p["element_type"] == position]
        
        # If no players found, return empty list
        if not team_players:
            return []
        
        return team_players
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{player_id}/history",
    summary="Get Player History",
    description="Retrieve historical performance data for a specific player",
    response_description="Historical performance data for the specified player"
)
async def get_player_history(
    player_id: int = Path(..., description="The player ID", example=1)
):
    """
    Get historical performance data for a specific player.
    
    Args:
        player_id (int): The player ID
        
    Returns:
        Dict: Player history data
    """
    try:
        return FPLService.get_player_history(player_id)
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail=f"History for player with ID {player_id} not found")
        raise HTTPException(status_code=500, detail=str(e)) 