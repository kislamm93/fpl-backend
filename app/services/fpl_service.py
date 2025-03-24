import requests
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class FPLService:
    """Service class for interacting with the Fantasy Premier League API."""
    
    BASE_URL = "https://fantasy.premierleague.com/api"
    
    @classmethod
    def get_bootstrap_static(cls) -> Dict[str, Any]:
        """
        Get bootstrap-static data from the FPL API.
        
        Returns:
            Dict: Bootstrap static data
        """
        url = f"{cls.BASE_URL}/bootstrap-static/"
        response = requests.get(url)
        if response.status_code != 200:
            logging.error(f"Failed to get bootstrap-static data. Status: {response.status_code}")
            return {}
        return response.json()
    
    @classmethod
    def get_current_event(cls) -> Dict[str, Any]:
        """
        Get the current gameweek.
        
        Returns:
            Dict: Current gameweek data
        """
        bootstrap_data = cls.get_bootstrap_static()
        events = bootstrap_data.get("events", [])
        
        # Find the current event
        current_event = next((e for e in events if e.get("is_current")), None)
        
        if not current_event:
            # If no current event, return the next event
            current_event = next((e for e in events if e.get("is_next")), None)
        
        return current_event or {}
    
    @classmethod
    def get_events(cls) -> List[Dict[str, Any]]:
        """
        Get all gameweeks (events) for the current season.
        
        Returns:
            List[Dict]: List of gameweeks
        """
        bootstrap_data = cls.get_bootstrap_static()
        return bootstrap_data.get("events", [])
    
    @classmethod
    def get_event(cls, event_id: int) -> Dict[str, Any]:
        """
        Get a specific gameweek by ID.
        
        Args:
            event_id (int): The gameweek ID
            
        Returns:
            Dict: Gameweek details
            
        Raises:
            Exception: If gameweek not found
        """
        events = cls.get_events()
        event = next((e for e in events if e["id"] == event_id), None)
        
        if not event:
            raise Exception(f"Gameweek with ID {event_id} not found")
            
        return event
    
    @classmethod
    def get_event_live(cls, event_id: int) -> Dict[str, Any]:
        """
        Get live data for a specific gameweek.
        
        Args:
            event_id (int): The gameweek ID
            
        Returns:
            Dict: Live gameweek data
            
        Raises:
            Exception: If API request fails
        """
        url = f"{cls.BASE_URL}/event/{event_id}/live/"
        response = requests.get(url)
        
        if response.status_code != 200:
            logging.error(f"Failed to get event live data. Status: {response.status_code}")
            raise Exception(f"Failed to get live data for gameweek {event_id}")
            
        return response.json()
    
    @classmethod
    def get_fixtures(cls) -> List[Dict[str, Any]]:
        """
        Get all fixtures for the current season.
        
        Returns:
            List[Dict]: List of fixtures
            
        Raises:
            Exception: If API request fails
        """
        url = f"{cls.BASE_URL}/fixtures/"
        response = requests.get(url)
        
        if response.status_code != 200:
            logging.error(f"Failed to get fixtures. Status: {response.status_code}")
            raise Exception("Failed to get fixtures")
            
        return response.json()
    
    @classmethod
    def get_fixtures_by_event(cls, event_id: int) -> List[Dict[str, Any]]:
        """
        Get fixtures for a specific gameweek.
        
        Args:
            event_id (int): The gameweek ID
            
        Returns:
            List[Dict]: List of fixtures for the specified gameweek
            
        Raises:
            Exception: If API request fails
        """
        all_fixtures = cls.get_fixtures()
        return [f for f in all_fixtures if f.get("event") == event_id]
    
    @classmethod
    def get_fixture(cls, fixture_id: int) -> Dict[str, Any]:
        """
        Get a specific fixture by ID.
        
        Args:
            fixture_id (int): The fixture ID
            
        Returns:
            Dict: Fixture details
            
        Raises:
            Exception: If fixture not found
        """
        fixtures = cls.get_fixtures()
        fixture = next((f for f in fixtures if f["id"] == fixture_id), None)
        
        if not fixture:
            raise Exception(f"Fixture with ID {fixture_id} not found")
            
        return fixture
    
    @classmethod
    def get_manager(cls, manager_id: int) -> Dict[str, Any]:
        """
        Get details for a specific FPL manager.
        
        Args:
            manager_id (int): The manager ID
            
        Returns:
            Dict: Manager details
            
        Raises:
            Exception: If API request fails
        """
        url = f"{cls.BASE_URL}/entry/{manager_id}/"
        response = requests.get(url)
        
        if response.status_code != 200:
            logging.error(f"Failed to get manager data. Status: {response.status_code}")
            raise Exception(f"Failed to get data for manager {manager_id}. Status: {response.status_code}")
            
        return response.json()
    
    @classmethod
    def get_manager_picks(cls, manager_id: int, event_id: int) -> Dict[str, Any]:
        """
        Get a manager's team picks for a specific gameweek.
        
        Args:
            manager_id (int): The manager ID
            event_id (int): The gameweek ID
            
        Returns:
            Dict: Manager's team selection
            
        Raises:
            Exception: If API request fails
        """
        url = f"{cls.BASE_URL}/entry/{manager_id}/event/{event_id}/picks/"
        response = requests.get(url)
        
        if response.status_code != 200:
            logging.error(f"Failed to get manager picks. Status: {response.status_code}")
            raise Exception(f"Failed to get picks for manager {manager_id} in gameweek {event_id}")
            
        return response.json()
    
    @classmethod
    def get_manager_history(cls, manager_id: int) -> Dict[str, Any]:
        """
        Get a manager's historical performance data.
        
        Args:
            manager_id (int): The manager ID
            
        Returns:
            Dict: Manager's history
            
        Raises:
            Exception: If API request fails
        """
        url = f"{cls.BASE_URL}/entry/{manager_id}/history/"
        response = requests.get(url)
        
        if response.status_code != 200:
            logging.error(f"Failed to get manager history. Status: {response.status_code}")
            raise Exception(f"Failed to get history for manager {manager_id}")
            
        return response.json()
    
    @classmethod
    def get_league_standings(cls, league_id: int, page_standings: int = 1, page_new_entries: int = 1, phase: int = 1) -> Dict[str, Any]:
        """
        Get standings for a classic league.
        
        Args:
            league_id (int): The league ID
            page_standings (int): Page number for standings
            page_new_entries (int): Page number for new entries
            phase (int): League phase
            
        Returns:
            Dict: League standings
            
        Raises:
            Exception: If API request fails
        """
        url = f"{cls.BASE_URL}/leagues-classic/{league_id}/standings/"
        params = {
            "page_standings": page_standings,
            "page_new_entries": page_new_entries,
            "phase": phase
        }
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            logging.error(f"Failed to get league standings. Status: {response.status_code}")
            raise Exception(f"Failed to get standings for league {league_id}")
            
        return response.json()
    
    @classmethod
    def get_player_summary(cls, player_id: int) -> Dict[str, Any]:
        """
        Get summary information for a specific player.
        
        Args:
            player_id (int): The player ID
            
        Returns:
            Dict: Player summary information
            
        Raises:
            Exception: If API request fails
        """
        url = f"{cls.BASE_URL}/element-summary/{player_id}/"
        response = requests.get(url)
        
        if response.status_code != 200:
            logging.error(f"Failed to get player summary. Status: {response.status_code}")
            raise Exception(f"Failed to get summary for player {player_id}")
            
        return response.json()
    
    @classmethod
    def get_player_history(cls, player_id: int) -> Dict[str, Any]:
        """
        Get historical performance data for a specific player.
        
        Args:
            player_id (int): The player ID
            
        Returns:
            Dict: Player history data
            
        Raises:
            Exception: If API request fails
        """
        # Player history is available in the player summary
        return cls.get_player_summary(player_id) 