"""Fixture Ticker using the OFFICIAL FPL fixture difficulty ratings (FDR).

Each fixture from the public FPL API carries `team_h_difficulty` and
`team_a_difficulty` (1-5, higher = harder). A team's difficulty in a fixture is
the home value if it plays at home, else the away value. No admin input, no DB.
"""
from typing import Dict

from fastapi import APIRouter, HTTPException, Query

from app.services.fpl_service import FPLService

router = APIRouter(prefix="/fixture-ticker", tags=["fixture-ticker"])


@router.get("/", summary="Official FDR ticker, sortable easy->hard over a GW range")
async def get_ticker(
    from_gw: int = Query(..., ge=1, le=38, description="First gameweek (inclusive)"),
    to_gw: int = Query(..., ge=1, le=38, description="Last gameweek (inclusive)"),
):
    if to_gw < from_gw:
        raise HTTPException(status_code=400, detail="to_gw must be >= from_gw")

    bootstrap = FPLService.get_bootstrap_static()
    teams = bootstrap.get("teams", [])
    team_by_id: Dict[int, dict] = {t["id"]: t for t in teams}

    gameweeks = list(range(from_gw, to_gw + 1))
    gw_set = set(gameweeks)
    fixtures = [f for f in FPLService.get_fixtures() if f.get("event") in gw_set]

    rows = []
    for t in teams:
        tid = t["id"]
        cells: Dict[str, list] = {}
        total = 0
        count = 0
        for f in fixtures:
            is_home = tid == f["team_h"]
            is_away = tid == f["team_a"]
            if not (is_home or is_away):
                continue
            opponent_id = f["team_a"] if is_home else f["team_h"]
            difficulty = f["team_h_difficulty"] if is_home else f["team_a_difficulty"]
            cells.setdefault(str(f["event"]), []).append(
                {
                    "opponent_id": opponent_id,
                    "opponent_short": team_by_id.get(opponent_id, {}).get("short_name", "?"),
                    "is_home": is_home,
                    "difficulty": difficulty,
                }
            )
            total += difficulty
            count += 1
        rows.append(
            {
                "team_id": tid,
                "name": t["name"],
                "short_name": t["short_name"],
                "total": total,
                "fixture_count": count,
                "cells": cells,
            }
        )

    rows.sort(key=lambda r: (r["total"], -r["fixture_count"]))
    return {"from_gw": from_gw, "to_gw": to_gw, "gameweeks": gameweeks, "rows": rows}
