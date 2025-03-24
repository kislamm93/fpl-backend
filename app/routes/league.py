from fastapi import APIRouter, HTTPException, Path, Query
from app.services.fpl_service import FPLService
from typing import Optional

router = APIRouter(
    prefix="/leagues-classic",
    tags=["leagues"],
    responses={
        404: {"description": "League not found"},
        500: {"description": "Internal server error"}
    }
)

@router.get(
    "/{league_id}/standings",
    summary="Get League Standings",
    description="Retrieve the current standings for a classic league",
    response_description="League information and standings"
)
async def get_league_standings(
    league_id: int = Path(..., description="The league ID", example=12345),
    page_standings: int = Query(1, description="Page number for standings", example=1),
    page_new_entries: int = Query(1, description="Page number for new entries", example=1),
    phase: int = Query(1, description="League phase", example=1)
):
    """
    Get standings for a classic league.
    
    Args:
        league_id (int): The league ID
        page_standings (int): Page number for standings
        page_new_entries (int): Page number for new entries
        phase (int): League phase
        
    Returns:
        Dict: League standings
    """
    try:
        return FPLService.get_league_standings(
            league_id, 
            page_standings=page_standings,
            page_new_entries=page_new_entries,
            phase=phase
        )
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail=f"League with ID {league_id} not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{league_id}/participants",
    summary="Get League Participants",
    description="Retrieve detailed information about all participants in a league",
    response_description="List of participants with their history and chips"
)
async def get_league_participants(
    league_id: int = Path(..., description="The league ID", example=12345),
    limit: Optional[int] = Query(None, description="Maximum number of participants to return", example=10)
):
    """
    Get detailed data about all participants in a league.
    
    Args:
        league_id (int): The league ID
        limit (int, optional): Maximum number of participants to return
        
    Returns:
        List[Dict]: League participants with their data
    """
    try:
        # Get league standings
        standings = FPLService.get_league_standings(league_id)
        
        # Extract entries from standings
        entries = standings.get("standings", {}).get("results", [])
        
        # Limit the number of entries if specified
        if limit and limit > 0:
            entries = entries[:limit]
        
        # For each entry, get detailed information
        participants = []
        for entry in entries:
            entry_id = entry.get("entry")
            player_name = entry.get("player_name")
            
            try:
                # Get entry history
                history = FPLService.get_manager_history(entry_id)
                
                # Extract chips used
                chips = history.get("chips", [])
                
                # Extract rank history
                rank_history = history.get("current", [])
                
                # Add to participants list
                participants.append({
                    "manager_id": entry_id,
                    "player_name": player_name,
                    "rank_history": rank_history,
                    "chips": chips
                })
            except Exception as e:
                # Skip this entry if there was an error
                continue
        
        return participants
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail=f"League with ID {league_id} not found")
        raise HTTPException(status_code=500, detail=str(e)) 