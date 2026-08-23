from fastapi import APIRouter, HTTPException, Path, Query
from app.services.fpl_service import FPLService

router = APIRouter(
    prefix="/entry",
    tags=["entry"],
    responses={
        404: {"description": "Manager not found"},
        500: {"description": "Internal server error"}
    }
)

@router.get(
    "/{manager_id}",
    summary="Get Manager Details",
    description="Retrieve detailed information about a specific FPL manager",
    response_description="Manager details with various information"
)
async def get_manager(
    manager_id: int = Path(..., description="The manager's ID", example=1234567)
):
    """
    Get details for a specific FPL manager.
    
    Args:
        manager_id (int): The manager's ID
        
    Returns:
        Dict: Manager details
    """
    try:
        return FPLService.get_manager(manager_id)
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Manager with ID {manager_id} not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{manager_id}/event/{event_id}/picks",
    summary="Get Manager Picks",
    description="Retrieve a manager's team selection for a specific gameweek",
    response_description="Manager's team selection with details"
)
async def get_manager_picks(
    manager_id: int = Path(..., description="The manager's ID", example=1234567),
    event_id: int = Path(..., description="The gameweek number", example=1)
):
    """
    Get a manager's team picks for a specific gameweek.
    
    Args:
        manager_id (int): The manager's ID
        event_id (int): The gameweek number
        
    Returns:
        Dict: Manager's team selection
    """
    try:
        return FPLService.get_manager_picks(manager_id, event_id)
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Picks not found for manager {manager_id} in gameweek {event_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{manager_id}/history",
    summary="Get Manager History",
    description="Retrieve historical performance data for a specific manager",
    response_description="Manager's historical performance data"
)
async def get_manager_history(
    manager_id: int = Path(..., description="The manager's ID", example=1234567)
):
    """
    Get a manager's historical performance data.
    
    Args:
        manager_id (int): The manager's ID
        
    Returns:
        Dict: Manager's history
    """
    try:
        return FPLService.get_manager_history(manager_id)
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail=f"History not found for manager {manager_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/my-team/{manager_id}/stats",
    summary="Get Team Statistics",
    description="Retrieve performance statistics for a manager's current team",
    response_description="Team statistics with player performances"
)
async def get_team_stats(
    manager_id: int = Path(..., description="The manager's ID", example=1234567),
    event_id: int = Query(None, description="The gameweek number (defaults to current gameweek)", example=1)
):
    """
    Get statistics for a manager's team.
    
    Args:
        manager_id (int): The manager's ID
        event_id (int, optional): The gameweek number
        
    Returns:
        Dict: Team statistics
    """
    try:
        # If event_id is not provided, use the current gameweek
        if not event_id:
            current_event = FPLService.get_current_event()
            event_id = current_event["id"]
            
        # Get manager picks for the specified event
        picks = FPLService.get_manager_picks(manager_id, event_id)
        
        # Get live data for the event
        live_data = FPLService.get_event_live(event_id)
        live_by_id = {e["id"]: e for e in live_data["elements"]}

        # Bootstrap gives player identity (name, team) + season aggregates,
        # which the live event data does not carry.
        bootstrap = FPLService.get_bootstrap_static()
        elements_by_id = {e["id"]: e for e in bootstrap.get("elements", [])}
        team_short_by_id = {t["id"]: t["short_name"] for t in bootstrap.get("teams", [])}

        # Combine picks with live + bootstrap data to get enriched team stats
        team_stats = []
        for pick in picks["picks"]:
            player_id = pick["element"]
            player_data = live_by_id.get(player_id)
            element = elements_by_id.get(player_id, {})

            if player_data:
                team_stats.append({
                    "id": player_id,
                    "position": pick["position"],
                    "is_captain": pick["is_captain"],
                    "is_vice_captain": pick["is_vice_captain"],
                    "multiplier": pick["multiplier"],
                    "stats": player_data["stats"],
                    "web_name": element.get("web_name", f"Player {player_id}"),
                    "team": element.get("team"),
                    "team_short_name": team_short_by_id.get(element.get("team"), ""),
                    "team_code": element.get("team_code"),
                    "points_per_game": element.get("points_per_game", ""),
                    "selected_by_percent": element.get("selected_by_percent", ""),
                })
        
        return {
            "manager_id": manager_id,
            "gameweek": event_id,
            "team_stats": team_stats
        }
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Team stats not found for manager {manager_id}")
        raise HTTPException(status_code=500, detail=str(e)) 