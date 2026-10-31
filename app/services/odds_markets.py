"""Betting markets for FPL decisions: fetch on demand, serve from a snapshot.

Why a snapshot rather than fetch-per-request: the Odds API free tier is 500
credits a month, and credits are charged per market per region — per *event*
for anything outside h2h/spreads/totals. A full pull of everything useful for
one gameweek is ~33 credits, so a page that fetched live would exhaust the
month in about fifteen views. `refresh()` is therefore admin-only and explicit;
every read here is free and comes out of `_snapshot`.

The snapshot lives in memory, so a redeploy clears it. That is acceptable
because the backend is kept warm by an external pinger, so restarts are days
apart, and `last_updated` is surfaced to the UI so stale data is visible rather
than silent.
"""
import json
import logging
import os
import re
import threading
import unicodedata
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from app.services.fpl_service import FPLService
from app.services import odds_api_service as odds_api

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_KEY = os.getenv("ODDS_API_KEY")
API_BASE = "https://api.the-odds-api.com/v4/sports/soccer_epl"

# Region per market family: EPL player props are only priced by US books, while
# BTTS is far better covered in the UK (10 books vs none).
REGION_TEAM = "uk"
REGION_PLAYER = "us"

# Markets the bulk /odds endpoint accepts. Everything else is per-event, which
# is why the player markets dominate the credit cost.
BULK_MARKETS = "h2h,totals,spreads"
EVENT_TEAM_MARKETS = "btts"
EVENT_PLAYER_MARKETS = "player_goal_scorer_anytime,player_shots_on_target"

_ALIAS_PATH = Path(__file__).resolve().parent.parent / "data" / "player_aliases.json"

_lock = threading.Lock()
_snapshot: Dict[str, Any] = {
    "last_updated": None,
    "gameweek": None,
    "credits_used": None,
    "matches": [],
    "goalscorers": [],
    "unmatched_players": [],
    "unmatched_teams": [],
}


# --------------------------------------------------------------------------
# name resolution
# --------------------------------------------------------------------------
def _norm(s: str) -> str:
    """Lowercase, fold accents, drop punctuation, collapse whitespace.

    The two feeds disagree on diacritics constantly — the books write "Fabian
    Schar", "Enzo Le Fee", "Bafode Diakite" where FPL has "Schär", "Le Fée",
    "Diakité" — so both sides get decomposed and stripped of combining marks.
    A few ligatures don't decompose and need spelling out.
    """
    s = (s or "").lower()
    for a, b in (("ø", "o"), ("æ", "ae"), ("ß", "ss"), ("đ", "d"), ("ł", "l"), ("ð", "d"), ("þ", "th")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _load_aliases() -> Dict[str, str]:
    """Manual odds-name -> FPL web_name overrides for names we can't match."""
    try:
        raw = json.loads(_ALIAS_PATH.read_text())
        # Underscore keys are notes to whoever edits the file, not aliases.
        return {_norm(k): v for k, v in raw.items() if not k.startswith("_")}
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        logging.error(f"Could not read player aliases: {exc}")
        return {}


# FPL's `name` is already a short display form ("Man City", "Nott'm Forest",
# "Spurs"), so a token test against the bookmaker's full name fails on exactly
# the clubs that matter most. These are the cases no amount of string logic
# gets right, because the two feeds don't share a word.
_TEAM_ALIASES = {
    "manchester city": "MCI",
    "manchester united": "MUN",
    "tottenham hotspur": "TOT",
    "tottenham": "TOT",
    "nottingham forest": "NFO",
    "wolverhampton wanderers": "WOL",
    "sheffield united": "SHU",
    "west bromwich albion": "WBA",
    "brighton and hove albion": "BHA",
}


def resolve_team(name: str, teams: List[dict]) -> Optional[dict]:
    """Map an odds-API team name ("Manchester City") to an FPL team.

    Curated alias first, then exact normalised match, then a token-subset test
    (which covers "Leeds United" vs "Leeds", "Hull City" vs "Hull"). No fuzzy
    scoring: a near-miss would attribute a whole fixture's odds to the wrong
    club, and difflib happily scores "Barcelona" against Arsenal at 0.625.
    """
    n = _norm(name)
    by_short = {t["short_name"]: t for t in teams}
    if n in _TEAM_ALIASES and _TEAM_ALIASES[n] in by_short:
        return by_short[_TEAM_ALIASES[n]]
    by_norm = {_norm(t["name"]): t for t in teams}
    if n in by_norm:
        return by_norm[n]
    n_tokens = set(n.split())
    for norm_name, t in by_norm.items():
        t_tokens = set(norm_name.split())
        if t_tokens <= n_tokens or n_tokens <= t_tokens:
            return t
    return None


def resolve_player(
    odds_name: str, candidates: List[dict], aliases: Dict[str, str]
) -> Optional[dict]:
    """Map a bookmaker's player name to an FPL element.

    `candidates` must be only the players of the two clubs in the fixture. That
    restriction is what makes this tractable: the bookmaker writes full legal
    names ("Erling Braut Haaland", "Iliman-Cheikh Ndiaye") while FPL stores a
    short `web_name`, so matching is inherently loose — but across ~50 players
    rather than 700 it stays unambiguous, and it removes the duplicate-surname
    trap entirely (the two Hendersons play for different clubs).

    Returns None rather than guessing. A wrong match is worse than no match: it
    silently attaches one player's goalscoring odds to another.
    """
    n = _norm(odds_name)
    if not n:
        return None

    if n in aliases:
        target = _norm(aliases[n])
        hit = next((p for p in candidates if _norm(p["web_name"]) == target), None)
        if hit:
            return hit

    tokens = set(n.split())
    for p in candidates:
        full = _norm(f"{p.get('first_name','')} {p.get('second_name','')}")
        if n == full or n == _norm(p["web_name"]):
            return p

    # All of the FPL name's tokens appear in the bookmaker's name — catches the
    # extra middle names books carry ("Erling Braut Haaland" vs "Erling Haaland").
    for p in candidates:
        fpl_tokens = set(_norm(f"{p.get('first_name','')} {p.get('second_name','')}").split())
        if fpl_tokens and fpl_tokens <= tokens:
            return p

    # Unique surname within the fixture.
    surname_hits = [
        p for p in candidates
        if _norm(p.get("second_name", "")).split()
        and _norm(p["second_name"]).split()[-1] in tokens
    ]
    if len(surname_hits) == 1:
        return surname_hits[0]

    web_hits = [p for p in candidates if _norm(p["web_name"]) in tokens]
    return web_hits[0] if len(web_hits) == 1 else None


# --------------------------------------------------------------------------
# odds helpers
# --------------------------------------------------------------------------
def _implied(price: float) -> float:
    return round(100.0 / price, 1) if price and price > 0 else 0.0


def _consensus(prices: List[float]) -> float:
    """Average implied probability across books, so one outlier can't set it."""
    probs = [100.0 / p for p in prices if p and p > 0]
    return round(sum(probs) / len(probs), 1) if probs else 0.0


def _get(url: str, params: dict) -> Tuple[Any, int]:
    """GET with credit accounting. Returns (json, credits_used_total)."""
    r = requests.get(url, params=params, timeout=30)
    used = int(r.headers.get("x-requests-used") or 0)
    if r.status_code != 200:
        logging.error(f"Odds API {r.status_code} for {url}: {r.text[:200]}")
        raise Exception(f"Odds API returned {r.status_code}")
    return r.json(), used


# --------------------------------------------------------------------------
# refresh
# --------------------------------------------------------------------------
def refresh() -> Dict[str, Any]:
    """Pull every market we use for the upcoming gameweek and store a snapshot.

    Spend is bounded and predictable: one bulk call for h2h/totals/spreads
    across all fixtures, then two per-event calls (BTTS on UK books, player
    markets on US books) for the upcoming gameweek's fixtures only.
    """
    if not API_KEY:
        raise Exception("ODDS_API_KEY not configured")

    bootstrap = FPLService.get_bootstrap_static()
    teams = bootstrap.get("teams", [])
    elements = bootstrap.get("elements", [])
    positions = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
    aliases = _load_aliases()
    gw = (FPLService.get_upcoming_event() or {}).get("id")

    by_team: Dict[int, List[dict]] = {}
    for p in elements:
        by_team.setdefault(p["team"], []).append(p)

    credits_before = None

    # 1. Bulk team markets — one charge covers every fixture.
    bulk, used = _get(
        f"{API_BASE}/odds",
        {"apiKey": API_KEY, "regions": REGION_TEAM, "markets": BULK_MARKETS, "oddsFormat": "decimal"},
    )
    credits_before = used

    # Only the upcoming gameweek's fixtures get per-event calls; that is where
    # the cost lives (one credit per market per region per event).
    fixtures = [f for f in FPLService.get_fixtures() if f.get("event") == gw]
    fixture_pairs = {
        tuple(sorted((f["team_h"], f["team_a"]))) for f in fixtures
    }
    # Official FDR per team for this gameweek. Attached to every row below so
    # nothing downstream has to cross-reference a 20-row table and pick a side —
    # the agent was quoting the opponent's difficulty instead of the player's.
    difficulty: Dict[int, int] = {}
    for f in fixtures:
        difficulty[f["team_h"]] = f["team_h_difficulty"]
        difficulty[f["team_a"]] = f["team_a_difficulty"]

    matches: List[dict] = []
    goalscorers: List[dict] = []
    unmatched: List[str] = []
    unmatched_teams: List[str] = []

    for ev in bulk:
        home = resolve_team(ev.get("home_team", ""), teams)
        away = resolve_team(ev.get("away_team", ""), teams)
        if not home or not away:
            unmatched_teams.append(f"{ev.get('home_team')} v {ev.get('away_team')}")
            continue
        if tuple(sorted((home["id"], away["id"]))) not in fixture_pairs:
            continue  # a later gameweek; keep it out of the per-event spend

        combined = odds_api.calculate_combined_market_odds(ev.get("bookmakers", []))
        row = {
            "event_id": ev["id"],
            "kickoff": ev.get("commence_time"),
            "home": home["short_name"],
            "away": away["short_name"],
            "home_name": home["name"],
            "away_name": away["name"],
            "home_win_pct": combined.get(ev["home_team"].lower(), {}).get("implied_probability"),
            "away_win_pct": combined.get(ev["away_team"].lower(), {}).get("implied_probability"),
            "draw_pct": combined.get("draw", {}).get("implied_probability"),
            "over_2_5_pct": None,
            "under_2_5_pct": None,
            "handicap": None,
            "btts_yes_pct": None,
            "btts_no_pct": None,
            "home_cs_pct": None,
            "away_cs_pct": None,
            "home_difficulty": difficulty.get(home["id"]),
            "away_difficulty": difficulty.get(away["id"]),
        }

        over, under, handicaps = [], [], []
        for b in ev.get("bookmakers", []):
            for m in b.get("markets", []):
                if m["key"] == "totals":
                    for o in m.get("outcomes", []):
                        if o.get("point") == 2.5 and o["name"].lower() == "over":
                            over.append(o["price"])
                        elif o.get("point") == 2.5 and o["name"].lower() == "under":
                            under.append(o["price"])
                elif m["key"] == "spreads":
                    for o in m.get("outcomes", []):
                        if o["name"] == ev["home_team"] and o.get("point") is not None:
                            handicaps.append(o["point"])
        row["over_2_5_pct"] = _consensus(over)
        row["under_2_5_pct"] = _consensus(under)
        if handicaps:
            row["handicap"] = round(sum(handicaps) / len(handicaps), 2)

        # 2. BTTS (UK books) -> clean-sheet probabilities.
        try:
            btts_ev, used = _get(
                f"{API_BASE}/events/{ev['id']}/odds",
                {"apiKey": API_KEY, "regions": REGION_TEAM, "markets": EVENT_TEAM_MARKETS,
                 "oddsFormat": "decimal"},
            )
            yes, no = [], []
            for b in btts_ev.get("bookmakers", []):
                for m in b.get("markets", []):
                    if m["key"] != "btts":
                        continue
                    for o in m.get("outcomes", []):
                        (yes if o["name"].lower() == "yes" else no).append(o["price"])
            row["btts_yes_pct"] = _consensus(yes)
            row["btts_no_pct"] = _consensus(no)
            # A clean sheet for one side means the other failed to score, so
            # split "no BTTS" by relative team strength rather than halving it.
            hw = row["home_win_pct"] or 50.0
            aw = row["away_win_pct"] or 50.0
            no_btts = row["btts_no_pct"] or 0.0
            if hw + aw > 0:
                row["home_cs_pct"] = round(no_btts * hw / (hw + aw), 1)
                row["away_cs_pct"] = round(no_btts * aw / (hw + aw), 1)
        except Exception as exc:
            logging.warning(f"BTTS fetch failed for {row['home']} v {row['away']}: {exc}")

        # 3. Player markets (US books).
        candidates = by_team.get(home["id"], []) + by_team.get(away["id"], [])
        try:
            prop_ev, used = _get(
                f"{API_BASE}/events/{ev['id']}/odds",
                {"apiKey": API_KEY, "regions": REGION_PLAYER, "markets": EVENT_PLAYER_MARKETS,
                 "oddsFormat": "decimal"},
            )
            scorer: Dict[str, List[float]] = {}
            sot: Dict[str, List[float]] = {}
            for b in prop_ev.get("bookmakers", []):
                for m in b.get("markets", []):
                    for o in m.get("outcomes", []):
                        who = o.get("description") or o.get("name")
                        if m["key"] == "player_goal_scorer_anytime":
                            # Books list a "No Goalscorer" outcome alongside the
                            # players; it is a market option, not a person.
                            if (o.get("name") or "").lower() == "no" or _norm(who) in (
                                "no scorer", "no goalscorer", "none"
                            ):
                                continue
                            scorer.setdefault(who, []).append(o["price"])
                        elif m["key"] == "player_shots_on_target":
                            if o.get("point") == 0.5 and (o.get("name") or "").lower() == "over":
                                sot.setdefault(who, []).append(o["price"])

            for who, prices in scorer.items():
                el = resolve_player(who, candidates, aliases)
                if not el:
                    unmatched.append(who)
                    continue
                team = home if el["team"] == home["id"] else away
                goalscorers.append({
                    "event_id": ev["id"],
                    "player_id": el["id"],
                    "name": el["web_name"],
                    "odds_name": who,
                    "team": team["short_name"],
                    "opponent": (away if team is home else home)["short_name"],
                    "is_home": team is home,
                    "difficulty": difficulty.get(team["id"]),
                    "position": positions.get(el["element_type"], "?"),
                    "price": round(el["now_cost"] / 10, 1),
                    "owned_pct": float(el.get("selected_by_percent") or 0),
                    "anytime_pct": _consensus(prices),
                    "books": len(prices),
                    "sot_over_0_5_pct": _consensus(sot.get(who, [])),
                    "xgi_per_90": float(el.get("expected_goal_involvements_per_90") or 0),
                    "starts_per_90": float(el.get("starts_per_90") or 0),
                    "doubt": el.get("news") or None,
                })
        except Exception as exc:
            logging.warning(f"Player props failed for {row['home']} v {row['away']}: {exc}")

        matches.append(row)

    goalscorers.sort(key=lambda r: r["anytime_pct"], reverse=True)
    matches.sort(key=lambda r: r.get("kickoff") or "")

    snap = {
        "last_updated": time.time(),
        "gameweek": gw,
        "credits_used": used,
        "credits_spent_this_refresh": (used - credits_before) if credits_before is not None else None,
        "matches": matches,
        "goalscorers": goalscorers,
        "unmatched_players": sorted(set(unmatched)),
        "unmatched_teams": sorted(set(unmatched_teams)),
    }
    with _lock:
        _snapshot.clear()
        _snapshot.update(snap)
    logging.info(
        f"Odds snapshot refreshed: GW{gw}, {len(matches)} matches, "
        f"{len(goalscorers)} scorers, {len(snap['unmatched_players'])} unmatched players, "
        f"{len(snap['unmatched_teams'])} unmatched teams, "
        f"{snap['credits_spent_this_refresh']} credits"
    )
    return snap


def get_snapshot() -> Dict[str, Any]:
    """The current snapshot. Free — never calls the Odds API."""
    with _lock:
        return dict(_snapshot)
