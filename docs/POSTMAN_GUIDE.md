# FPL API Postman Collection Guide

This guide explains how to use the Postman collection to interact with the Fantasy Premier League (FPL) API.

## Getting Started

1. **Import the Collection**:
   - Open Postman
   - Click "Import" in the top left
   - Select the `FPL_API_Postman_Collection.json` file
   - The collection will be imported with all endpoints

2. **Import the Environment**:
   - Click "Import" again
   - Select the `FPL Local.postman_environment.json` file
   - The environment variables will be imported

3. **Select the Environment**:
   - In the top right of Postman, select "FPL Local" from the environment dropdown

## Environment Variables

The environment includes the following variables you can customize:

- `base_url`: Base URL for the API (default: http://localhost:8000)
- `manager_id`: Your FPL manager ID (default: 654925)
- `league_id`: A league ID to test (default: 497674)
- `gameweek`: Current gameweek number (default: 29)
- `event`: Event/gameweek ID (default: 29)
- `team_id`: A team ID for testing (default: 1)
- `player_id`: A player ID for testing (default: 123)
- `betting_event_id`: Betting event ID for odds endpoints (default: a6151a5362fb6365b776880f17a142cc)

## Collection Overview

The collection is organized into the following categories:

### Root Endpoints
- Welcome (GET `/`)
- Heartbeat (GET `/heartbeat`)
- Bootstrap Static (GET `/bootstrap-static`)

### Manager Endpoints
- Get Manager Details (GET `/entry/{manager_id}`)
- Get Manager Picks (GET `/entry/{manager_id}/event/{gameweek}/picks`)
- Get Manager History (GET `/entry/{manager_id}/history`)
- Get Manager Team Stats (GET `/entry/my-team/{manager_id}/stats`)

### League Endpoints
- Get League Standings (GET `/leagues-classic/{league_id}/standings`)
- Get League Participants (GET `/leagues-classic/{league_id}/participants`)

### Fixtures Endpoints
- Get All Fixtures (GET `/fixtures`)
- Get Gameweek Fixtures (GET `/fixtures?event={gameweek}`)

### Teams Endpoints
- Get All Teams (GET `/teams`)
- Get Team Details (GET `/teams/{team_id}`)
- Get Team Fixtures (GET `/teams/{team_id}/fixtures`)

### Players Endpoints
- Get All Players (GET `/players`)
- Get Player Details (GET `/players/{player_id}`)
- Get Player History (GET `/players/{player_id}/history`)

### Events (Gameweeks) Endpoints
- Get All Gameweeks (GET `/events`)
- Get Specific Gameweek (GET `/events/{event}`)
- Get Live Gameweek Data (GET `/events/{event}/live`)

### Odds Endpoints
- Get Upcoming Odds (GET `/odds/upcoming`)
- Get Event Odds (GET `/odds/{betting_event_id}`)
- Get Clean Sheets Odds (GET `/odds/{betting_event_id}/clean-sheets`)

## Usage Tips

1. **Finding Your Manager ID**:
   - Log in to the Fantasy Premier League website
   - Go to the "Points" tab
   - Your manager ID is in the URL (e.g., https://fantasy.premierleague.com/entry/123456/event/1)

2. **Finding League IDs**:
   - Go to your league on the FPL website
   - The league ID is in the URL (e.g., https://fantasy.premierleague.com/leagues/123456/standings/c)

3. **Running the API Locally**:
   - Make sure your API is running on the specified port (default: 8000)
   - Execute requests from Postman to test each endpoint

4. **Updating Environment Variables**:
   - Click on the eye icon next to the environment selector
   - Edit the current values to match your test data
   - Save your changes

## Troubleshooting

If you encounter issues:

1. Check that your API is running and accessible
2. Verify that your environment variables are correct
3. Check the response status codes and error messages
4. Ensure you're using valid IDs for players, teams, and managers 