from fastapi import APIRouter, HTTPException
from app.services.fpl_service import FPLService

router = APIRouter(prefix="/event", tags=["events"])

@router.get("/{gameweek}/live")
async def get_event_live(gameweek: int):
    try:
        return FPLService.get_event_live(gameweek)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{event}/fixtures")
async def get_fixtures(event: int):
    try:
        return FPLService.get_fixtures(event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 