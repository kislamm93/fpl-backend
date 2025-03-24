import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(
    title="FPL API Backend",
    description="A backend service for Fantasy Premier League API",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change this in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Middleware to log request processing time
@app.middleware("http")
async def log_request_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    end_time = time.time()
    
    elapsed_time = round(end_time - start_time, 3)  # Time in seconds
    logging.info(f"Processed {request.method} {request.url.path} in {elapsed_time}s")
    
    return response 