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
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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