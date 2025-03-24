# API Documentation

This folder contains the API documentation and testing resources for the FPL API Backend.

## Postman Collection and Environment

The folder contains two files for Postman setup:
1. `fpl-api.postman_collection.json` - Collection of all API endpoints
2. `fpl-api.postman_environment.json` - Environment variables for testing

### How to Use

1. Open Postman
2. Import the collection:
   - Click "Import" button
   - Select the `fpl-api.postman_collection.json` file
   - Click "Import"
3. Import the environment:
   - Click "Import" button
   - Select the `fpl-api.postman_environment.json` file
   - Click "Import"

### Environment Variables

The environment file includes the following variables:
- `base_url`: API base URL (default: http://localhost:8000)
- `manager_id`: Your FPL manager ID (default: 123456)
- `league_id`: Your FPL league ID (default: 123456)
- `gameweek`: Current gameweek number (default: 29)
- `event`: Current event number (default: 29)

To update these values:
1. In Postman, click "Environments"
2. Select "FPL Local"
3. Update the values as needed

### Available Endpoints

#### Entry
- `GET /entry/{manager_id}` - Get manager details
- `GET /entry/{manager_id}/event/{gameweek}/picks` - Get manager's picks for a gameweek
- `GET /entry/{manager_id}/history` - Get manager's history
- `GET /entry/my-team/{manager_id}/stats` - Get current team stats for a manager

#### League
- `GET /leagues-classic/{league_id}/standings` - Get league standings
- `GET /leagues-classic/{league_id}/participants` - Get detailed participant information

#### Event
- `GET /event/{gameweek}/live` - Get live scores for a gameweek
- `GET /event/{event}/fixtures` - Get fixtures for an event

#### General
- `GET /bootstrap-static` - Get static bootstrap data
- `GET /heartbeat` - Health check endpoint

### Testing

1. Make sure your FastAPI server is running (`python -m app.main`)
2. In Postman:
   - Select the "FPL Local" environment
   - Update the environment variables with your actual FPL IDs
   - You can now test any endpoint from the collection

### Response Examples

All endpoints return JSON responses. The collection includes example responses for each endpoint. 