# FPL API Backend

A FastAPI-based backend service that provides a clean interface to the Fantasy Premier League API.

## Features

- Entry management (manager details, picks, history)
- League management (standings, participants)
- Event management (live scores, fixtures)
- Bootstrap static data
- Health check endpoint

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
# For production
python -m app.main

# For development (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at `http://localhost:8000`

## Development

### Auto-reload Setup

For development, you can use uvicorn's built-in reload feature which will automatically restart the server when you make changes to your code:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Additional development options:
- `--reload-dir app`: Only watch the app directory for changes
- `--reload-delay 2`: Add a delay before reloading (in seconds)
- `--reload-includes "*.py"`: Only watch Python files

Example with all options:
```bash
uvicorn app.main:app --reload --reload-dir app --reload-delay 2 --reload-includes "*.py" --host 0.0.0.0 --port 8000
```

### Development Tools

1. **API Documentation**
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

2. **Postman Collection**
   - Import the collection from `docs/fpl-api.postman_collection.json`
   - Import the environment from `docs/fpl-api.postman_environment.json`

3. **Debug Mode**
   - The `--reload` flag enables debug mode automatically
   - You'll see detailed error messages and stack traces

## API Documentation

Once the server is running, you can access:
- Interactive API docs (Swagger UI): `http://localhost:8000/docs`
- Alternative API docs (ReDoc): `http://localhost:8000/redoc`

## Endpoints

### Entry
- `GET /entry/{manager_id}` - Get manager details
- `GET /entry/{manager_id}/event/{gameweek}/picks` - Get manager's picks for a gameweek
- `GET /entry/{manager_id}/history` - Get manager's history
- `GET /entry/my-team/{manager_id}/stats` - Get current team stats for a manager

### League
- `GET /leagues-classic/{league_id}/standings` - Get league standings
- `GET /leagues-classic/{league_id}/participants` - Get detailed participant information

### Event
- `GET /event/{gameweek}/live` - Get live scores for a gameweek
- `GET /event/{event}/fixtures` - Get fixtures for an event

### General
- `GET /bootstrap-static` - Get static bootstrap data
- `GET /heartbeat` - Health check endpoint

## Deployment

### Option 1: Render (Recommended)

1. Create a Render account at https://render.com
2. Connect your GitHub repository
3. Create a new Web Service
4. Select your repository
5. Configure the service:
   - Name: fpl-api (or your preferred name)
   - Environment: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Plan: Free

### Option 2: Railway

1. Create a Railway account at https://railway.app
2. Connect your GitHub repository
3. Create a new project
4. Select your repository
5. Railway will automatically detect the Python application and deploy it

### Option 3: Heroku

1. Create a Heroku account at https://heroku.com
2. Install Heroku CLI
3. Login to Heroku:
```bash
heroku login
```
4. Create a new app:
```bash
heroku create fpl-api
```
5. Deploy:
```bash
git push heroku main
```

## Environment Variables

For deployment, you might want to set these environment variables:
- `PORT`: The port the application should listen on (automatically set by platforms)
- `CORS_ORIGINS`: Comma-separated list of allowed origins (e.g., "https://your-frontend.com")

## Project Structure

The project follows a modular approach:
- `app/routes/` - API route handlers
- `app/services/` - Business logic and external API calls
- `app/dto/` - Data Transfer Objects and models
- `app/core/` - Core functionality and configurations
- `docs/` - API documentation and Postman collection

## Error Handling

The API includes proper error handling and will return appropriate HTTP status codes:
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

## Development

The project structure follows a modular approach:
- `app/routes/` - API route handlers
- `app/services/` - Business logic and external API calls
- `app/dto/` - Data Transfer Objects and models
- `app/core/` - Core functionality and configurations 