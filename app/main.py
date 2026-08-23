from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from app.routes import (
    root,
    players,
    teams,
    events,
    fixtures,
    entry,
    league,
    odds,
    ticker,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create FastAPI app
app = FastAPI(
    title="FPL API",
    description="A RESTful API for Fantasy Premier League data",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(root.router)
app.include_router(players.router)
app.include_router(teams.router)
app.include_router(events.router)
app.include_router(fixtures.router)
app.include_router(entry.router)
app.include_router(league.router)
app.include_router(odds.router)
app.include_router(ticker.router)


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logging.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

# Error handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

@app.get("/")
async def root():
    """
    Welcome message and heartbeat.
    """
    return {
        "status": "alive",
        "timestamp": time.time()
    }

@app.get("/bootstrap-static")
async def get_bootstrap_static():
    from app.services.fpl_service import FPLService
    return FPLService.get_bootstrap_static()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 