import requests
import logging
from typing import List, Dict, Any, Tuple
from statistics import mean
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants
API_KEY = os.getenv("ODDS_API_KEY")
API_HOST = "https://api.the-odds-api.com"
API_VERSION = "v4"
SPORT = "soccer_epl"  # Premier League
REGIONS = "uk"  # UK region
ODDS_FORMAT = "decimal"
MARKET = "h2h"  # Head-to-head market

# Set of allowed bookmakers to filter by
ALLOWED_BOOKMAKERS = {
    "betfair", "betfair_ex_uk", "skybet", "paddypower", "williamhill", 
    "bet365", "ladbrokes", "coral", "unibet", "betvictor"
}

def convert_odds_to_probability(odds: float) -> float:
    """
    Convert decimal odds to implied probability.
    
    Args:
        odds (float): Decimal odds
        
    Returns:
        float: Implied probability percentage
    """
    return round((1 / odds) * 100, 2)

def normalize_probabilities(prob1: float, prob2: float) -> Tuple[float, float]:
    """
    Normalize two probabilities to ensure they sum to 100%.
    
    Args:
        prob1 (float): First probability
        prob2 (float): Second probability
        
    Returns:
        Tuple[float, float]: Normalized probabilities
    """
    total = prob1 + prob2
    if total == 0:
        return 0, 0
    
    return round((prob1 / total) * 100, 2), round((prob2 / total) * 100, 2)

def calculate_implied_probabilities(outcomes: List[Dict]) -> List[Dict]:
    """
    Calculate implied probabilities for outcomes based on their odds.
    
    Args:
        outcomes (List[Dict]): List of outcomes with odds
        
    Returns:
        List[Dict]: List of outcomes with implied probabilities
    """
    # Copy the outcomes to avoid modifying the original
    outcomes_with_probs = []
    
    # Sum of raw probabilities for normalization
    sum_probs = 0
    
    # First pass: Calculate raw probabilities
    for outcome in outcomes:
        # Create a copy of the outcome
        outcome_copy = outcome.copy()
        
        # Calculate implied probability
        price = outcome.get("price", 0)
        if price > 0:
            implied_prob = convert_odds_to_probability(price)
            sum_probs += implied_prob
            outcome_copy["implied_probability"] = implied_prob
        else:
            outcome_copy["implied_probability"] = 0
        
        outcomes_with_probs.append(outcome_copy)
    
    # Second pass: Normalize probabilities
    for outcome in outcomes_with_probs:
        if sum_probs > 0:
            outcome["implied_probability"] = round((outcome["implied_probability"] / sum_probs) * 100, 2)
    
    return outcomes_with_probs

def calculate_combined_market_odds(bookmakers: List[Dict]) -> Dict:
    """
    Averages odds across all bookmakers to calculate combined market odds.
    
    Args:
        bookmakers (List[Dict]): List of bookmakers with markets
        
    Returns:
        Dict: Combined market odds with implied probabilities
    """
    # Filter to allowed bookmakers
    filtered_bookmakers = []
    for bookmaker in bookmakers:
        if bookmaker.get("key") in ALLOWED_BOOKMAKERS:
            filtered_bookmakers.append(bookmaker)
    
    # If no allowed bookmakers, use all bookmakers
    if not filtered_bookmakers:
        filtered_bookmakers = bookmakers
    
    # Initialize counters and sums for each outcome
    outcome_data = {}
    
    # Process each bookmaker
    for bookmaker in filtered_bookmakers:
        markets = bookmaker.get("markets", [])
        for market in markets:
            if market.get("key") == "h2h":  # Process head-to-head market
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name", "").lower()
                    price = outcome.get("price", 0)
                    
                    if name not in outcome_data:
                        outcome_data[name] = {"total_price": 0, "count": 0}
                    
                    outcome_data[name]["total_price"] += price
                    outcome_data[name]["count"] += 1
    
    # Calculate average odds for each outcome
    combined_odds = {}
    for name, data in outcome_data.items():
        if data["count"] > 0:
            avg_price = data["total_price"] / data["count"]
            combined_odds[name] = {
                "name": name,
                "price": round(avg_price, 2),
                "implied_probability": convert_odds_to_probability(avg_price)
            }
    
    # Normalize the probabilities
    total_prob = sum(outcome["implied_probability"] for outcome in combined_odds.values())
    if total_prob > 0:
        for outcome in combined_odds.values():
            outcome["implied_probability"] = round((outcome["implied_probability"] / total_prob) * 100, 2)
    
    return combined_odds

def get_upcoming_matches() -> List[Dict[str, Any]]:
    """
    Fetch upcoming matches from The Odds API.
    
    Returns:
        List[Dict[str, Any]]: List of upcoming matches with odds
        
    Raises:
        Exception: If API key is not configured or API request fails
    """
    if not API_KEY:
        logging.error("ODDS_API_KEY not configured")
        raise Exception("ODDS_API_KEY not configured. Please add it to your .env file.")
    
    # Using the direct URL structure as specified
    url = f"{API_HOST}/{API_VERSION}/sports/{SPORT}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "markets": MARKET,
        "oddsFormat": ODDS_FORMAT
    }
    
    try:
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            logging.error(f"API request failed with status {response.status_code}: {response.text}")
            raise Exception(f"API request failed with status {response.status_code}")
        
        data = response.json()
        logging.info(f"Fetched {len(data)} upcoming matches from The Odds API")
        return data
    except requests.RequestException as e:
        logging.error(f"Request error: {str(e)}")
        raise Exception(f"Failed to connect to The Odds API: {str(e)}")

def get_event_btts_odds(event_id: str) -> Dict[str, Any]:
    """
    Fetch Both Teams To Score (BTTS) odds for a specific event by ID.
    
    Args:
        event_id (str): The event ID
        
    Returns:
        Dict[str, Any]: Event with BTTS odds
        
    Raises:
        Exception: If API key is not configured or API request fails
    """
    if not API_KEY:
        logging.error("ODDS_API_KEY not configured")
        raise Exception("ODDS_API_KEY not configured. Please add it to your .env file.")
    
    url = f"{API_HOST}/{API_VERSION}/sports/{SPORT}/events/{event_id}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "markets": "btts",
        "oddsFormat": ODDS_FORMAT
    }
    
    try:
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            logging.error(f"API request failed with status {response.status_code}: {response.text}")
            raise Exception(f"API request failed with status {response.status_code}")
        
        data = response.json()
        
        if not data or not data.get("bookmakers"):
            raise Exception(f"BTTS odds not available for event with ID {event_id}")
        
        logging.info(f"Fetched BTTS odds for event {event_id} from The Odds API")
        return data
    except requests.RequestException as e:
        logging.error(f"Request error: {str(e)}")
        raise Exception(f"Failed to connect to The Odds API: {str(e)}")

def extract_btts_odds(event_data: Dict) -> Tuple[float, float]:
    """
    Extract and average BTTS odds from event data.
    
    Args:
        event_data (Dict): Event data containing bookmakers and markets
        
    Returns:
        Tuple[float, float]: Average Yes and No odds
    """
    yes_odds_list = []
    no_odds_list = []
    
    for bookmaker in event_data.get("bookmakers", []):
        if bookmaker.get("key") not in ALLOWED_BOOKMAKERS and ALLOWED_BOOKMAKERS:
            continue
            
        for market in bookmaker.get("markets", []):
            if market.get("key") == "btts":
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name", "")
                    price = outcome.get("price", 0)
                    
                    if name == "Yes" and price > 0:
                        yes_odds_list.append(price)
                    elif name == "No" and price > 0:
                        no_odds_list.append(price)
    
    if not yes_odds_list or not no_odds_list:
        raise Exception("BTTS odds not available for this event")
    
    avg_yes_odds = sum(yes_odds_list) / len(yes_odds_list)
    avg_no_odds = sum(no_odds_list) / len(no_odds_list)
    
    return round(avg_yes_odds, 2), round(avg_no_odds, 2)

def calculate_clean_sheet_probabilities(
    event_data: Dict, 
    either_clean_sheet_prob: float, 
    avg_yes_odds: float, 
    avg_no_odds: float
) -> Dict:
    """
    Calculate probabilities for clean sheets, including individual team probabilities.
    
    Args:
        event_data (Dict): Event data containing teams and other info
        either_clean_sheet_prob (float): Probability that at least one team keeps a clean sheet
        avg_yes_odds (float): Average odds for BTTS Yes
        avg_no_odds (float): Average odds for BTTS No
        
    Returns:
        Dict: Clean sheet probabilities and odds for different scenarios
    """
    # Get upcoming matches to find match odds if available
    try:
        betting_event_id = event_data.get("id")
        upcoming_matches = get_upcoming_matches()
        match_data = next((match for match in upcoming_matches 
                          if match.get("id") == betting_event_id), None)
        
        if match_data:
            # Calculate combined market odds to estimate team strength
            combined_odds = calculate_combined_market_odds(match_data.get("bookmakers", []))
            
            # Extract home win, away win and draw probabilities
            home_win_prob = combined_odds.get(event_data.get("home_team", "").lower(), {}).get("implied_probability", 40)
            away_win_prob = combined_odds.get(event_data.get("away_team", "").lower(), {}).get("implied_probability", 30)
            draw_prob = combined_odds.get("draw", {}).get("implied_probability", 30)
            
            # Use these probabilities to distribute the clean sheet probability
            # Home team is more likely to keep a clean sheet if they're stronger
            strength_ratio = home_win_prob / (home_win_prob + away_win_prob) if (home_win_prob + away_win_prob) > 0 else 0.5
            
            # Assume 30% of the either_clean_sheet probability is for both teams keeping clean sheets (0-0 result)
            both_clean_sheets_prob = either_clean_sheet_prob * 0.3 * (draw_prob / 100)
            remaining_clean_sheet_prob = either_clean_sheet_prob - both_clean_sheets_prob
            
            # Distribute the remaining probability based on team strength
            home_clean_sheet_prob = (remaining_clean_sheet_prob * strength_ratio) + both_clean_sheets_prob
            away_clean_sheet_prob = (remaining_clean_sheet_prob * (1 - strength_ratio)) + both_clean_sheets_prob
        else:
            # If match not found in upcoming matches, use a simpler distribution
            # Typical home advantage gives ~60% of clean sheets to home team
            home_clean_sheet_prob = either_clean_sheet_prob * 0.6
            away_clean_sheet_prob = either_clean_sheet_prob * 0.4
    except Exception:
        # If we can't get the upcoming matches, use a default distribution
        home_clean_sheet_prob = either_clean_sheet_prob * 0.6
        away_clean_sheet_prob = either_clean_sheet_prob * 0.4
    
    # Round the probabilities to 2 decimal places
    home_clean_sheet_prob = round(home_clean_sheet_prob, 2)
    away_clean_sheet_prob = round(away_clean_sheet_prob, 2)
    
    # Convert probabilities back to odds
    home_clean_sheet_odds = round(100 / home_clean_sheet_prob, 2) if home_clean_sheet_prob > 0 else 0
    away_clean_sheet_odds = round(100 / away_clean_sheet_prob, 2) if away_clean_sheet_prob > 0 else 0
    
    # Calculate probability that neither team keeps a clean sheet (BTTS Yes)
    no_clean_sheets_prob = 100 - either_clean_sheet_prob
    
    # Return probabilities and odds
    return {
        "either_team": {
            "probability": either_clean_sheet_prob,
            "odds": avg_no_odds
        },
        "no_clean_sheets": {
            "probability": no_clean_sheets_prob,
            "odds": avg_yes_odds
        },
        "home_team": {
            "name": event_data.get("home_team"),
            "probability": home_clean_sheet_prob,
            "odds": home_clean_sheet_odds
        },
        "away_team": {
            "name": event_data.get("away_team"),
            "probability": away_clean_sheet_prob,
            "odds": away_clean_sheet_odds
        }
    } 