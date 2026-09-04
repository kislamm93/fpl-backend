from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.services.odds_api_service import (
    get_upcoming_matches,
    get_event_btts_odds,
    calculate_combined_market_odds,
    convert_odds_to_probability,
    normalize_probabilities,
    extract_btts_odds,
    calculate_clean_sheet_probabilities
)
from app.services.fpl_service import FPLService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def _parse_iso(value: str) -> datetime:
    """Parse an FPL/Odds-API ISO timestamp (trailing 'Z') into an aware datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _upcoming_gameweek_window():
    """(start, end) datetimes bounding the next gameweek's matches.

    The Odds API lists several gameweeks ahead; FPL's deadlines tell us where one
    gameweek ends and the next begins. A GW's matches fall between its own
    deadline and the following GW's deadline, so that pair is our filter window.
    `end` is None for the final gameweek (keep everything after `start`).
    Returns (None, None) if FPL data is unavailable, so callers fall back to
    showing all matches rather than an empty page.
    """
    events = FPLService.get_events()
    if not events:
        return None, None
    events = sorted(events, key=lambda e: e["id"])
    target = next((e for e in events if not e.get("finished")), None)
    if not target:
        return None, None
    start = _parse_iso(target["deadline_time"])
    following = next((e for e in events if e["id"] == target["id"] + 1), None)
    end = _parse_iso(following["deadline_time"]) if following else None
    return start, end

# Create router
router = APIRouter(
    prefix="/odds",
    tags=["odds"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

@router.get(
    "/upcoming",
    summary="Get Upcoming Odds",
    description="Retrieve odds for upcoming Premier League matches",
    response_description="Odds data for upcoming matches"
)
async def get_upcoming_odds():
    """
    Get odds for upcoming Premier League matches.
    
    Returns:
        Dict: Odds data for upcoming matches
    """
    try:
        # Get upcoming matches from The Odds API
        matches = get_upcoming_matches()

        # Keep only the next gameweek's matches (the Odds API returns several
        # gameweeks ahead). Falls back to all matches if the window can't be
        # determined or a timestamp is missing/unparseable.
        start, end = _upcoming_gameweek_window()
        if start is not None:
            def _in_window(match) -> bool:
                ct = match.get("commence_time")
                if not ct:
                    return False
                try:
                    commence = _parse_iso(ct)
                except ValueError:
                    return False
                if commence < start:
                    return False
                return end is None or commence < end

            matches = [m for m in matches if _in_window(m)]

        # Process the response to include combined market odds
        processed_matches = []
        for match in matches:
            # Calculate combined market odds
            combined_market_odds = calculate_combined_market_odds(match.get("bookmakers", []))

            # Create processed match
            processed_match = {
                "id": match.get("id"),
                "sport_key": match.get("sport_key"),
                "sport_title": match.get("sport_title"),
                "commence_time": match.get("commence_time"),
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "combined_market_odds": combined_market_odds
            }
            
            processed_matches.append(processed_match)
        
        return processed_matches
    except Exception as e:
        logging.error(f"Error retrieving upcoming odds: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{betting_event_id}/clean-sheets",
    summary="Get Clean Sheets Odds",
    description="Retrieve odds for clean sheets in a specific match",
    response_description="Clean sheets odds data for the specified event"
)
async def get_event_clean_sheets_odds(betting_event_id: str):
    """
    Get clean sheets odds for a specific event by ID.
    
    Args:
        betting_event_id (str): The event ID
        
    Returns:
        Dict: Clean sheets odds data for the specified event
    """
    try:
        # Get BTTS odds from The Odds API
        event_data = get_event_btts_odds(betting_event_id)
        
        # Extract and calculate average BTTS odds
        avg_yes_odds, avg_no_odds = extract_btts_odds(event_data)
        
        # Convert odds to probabilities
        yes_prob = convert_odds_to_probability(avg_yes_odds)
        no_prob = convert_odds_to_probability(avg_no_odds)
        
        # For clean sheets calculation:
        # BTTS "No" is the same as "at least one team keeps a clean sheet"
        # BTTS "Yes" is the same as "no clean sheets"
        either_clean_sheet_raw_prob = no_prob
        no_clean_sheets_raw_prob = yes_prob
        
        # Normalize probabilities to ensure they sum to 100%
        either_clean_sheet_prob, no_clean_sheet_prob = normalize_probabilities(
            either_clean_sheet_raw_prob, 
            no_clean_sheets_raw_prob
        )
        
        # Calculate clean sheet probabilities using the service function
        clean_sheets_data = calculate_clean_sheet_probabilities(
            event_data,
            either_clean_sheet_prob,
            avg_yes_odds,
            avg_no_odds
        )
        
        # Create processed response
        processed_response = {
            "id": event_data.get("id"),
            "sport_key": event_data.get("sport_key"),
            "sport_title": event_data.get("sport_title"),
            "commence_time": event_data.get("commence_time"),
            "home_team": event_data.get("home_team"),
            "away_team": event_data.get("away_team"),
            "clean_sheets": clean_sheets_data
        }
        
        logging.info(f"Successfully fetched clean sheets odds for event {betting_event_id}")
        return processed_response
    except Exception as e:
        logging.error(f"Error retrieving clean sheets odds for event {betting_event_id}: {str(e)}")
        if "404" in str(e):
            raise HTTPException(status_code=404, detail=f"Event with ID {betting_event_id} not found")
        raise HTTPException(status_code=500, detail=str(e)) 