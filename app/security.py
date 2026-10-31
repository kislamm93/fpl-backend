"""Admin gate for the few endpoints that cost money to call.

Reads are always open — they serve a cached snapshot and spend nothing. Only
actions that hit a metered upstream (the Odds API free tier is 500 credits a
month) sit behind this, so the cost of an open endpoint is capped at zero.
"""
import logging
import os

from fastapi import Header, HTTPException
from dotenv import load_dotenv

load_dotenv()

ADMIN_KEY = os.getenv("ADMIN_KEY")


async def require_admin(x_admin_key: str = Header(None, alias="X-Admin-Key")) -> None:
    """Reject the request unless it carries the configured admin key.

    A missing ADMIN_KEY fails closed. Leaving the key unset would otherwise
    make every protected endpoint public, which is the opposite of what an
    unset secret should mean.
    """
    if not ADMIN_KEY:
        logging.error("ADMIN_KEY is not configured; refusing admin request")
        raise HTTPException(status_code=503, detail="Admin key not configured on the server")
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key")
