"""Adapter to the captaincy agent, selected by AGENT_PROVIDER.

The frontend never talks to the agent directly. This module proxies to whichever
provider is configured and normalizes the response so callers only ever see clean
text (the raw ADK /run_sse stream is a huge event trace — tool calls, tool
payloads, reasoning signatures — none of which a chat client should handle).

Why the reply is buffered rather than streamed through: token-by-token streaming
makes the model commit to prose before its tool results land, so it writes a
player name from training data and cannot take it back — that is where
recommendations for players who left the league come from. Buffering costs no
real time (the total wait is identical) and lets the name guard inspect the
finished reply. What the client gets instead of live typing is the tool trace,
which is better progress information anyway: "reading goalscorer odds" says more
than a half-formed sentence.

Providers:
  gcp   -> the ADK agent on Cloud Run   (GCP_AGENT_URL)      [default]
  local -> a local `adk api_server`      (LOCAL_AGENT_URL)
"""
import json
import logging
import os

import httpx
from dotenv import load_dotenv

from app.services import name_guard

load_dotenv()

logger = logging.getLogger(__name__)

AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "gcp").lower()
# Defaults to the deployed Cloud Run agent so prod works without extra config;
# override via env for a different deployment.
GCP_AGENT_URL = os.getenv("GCP_AGENT_URL", "https://fpl-agent-44q5brj2va-uc.a.run.app").rstrip("/")
LOCAL_AGENT_URL = os.getenv("LOCAL_AGENT_URL", "http://127.0.0.1:8080").rstrip("/")

APP_NAME = os.getenv("AGENT_APP_NAME", "fpl_agent")

# The agent does tool calls (odds + player fetches) before the first token, so
# give it room; read timeout is disabled so a long stream is never cut off.
_TIMEOUT = httpx.Timeout(180.0, connect=10.0, read=None)

# Human-readable progress labels, so the client can say what's happening rather
# than spinning. Unknown tools fall back to the raw name.
TOOL_LABELS = {
    "current_gameweek": "checking the gameweek",
    "goalscorer_odds": "reading goalscorer odds",
    "clean_sheet_odds": "reading clean-sheet odds",
    "match_odds": "reading match odds",
    "fixture_difficulty": "checking fixture difficulty",
    "players": "looking up players",
    "manager_squad": "reading your squad",
    "league": "reading league standings",
    "manager": "reading manager history",
    "player_detail": "reading player history",
}


def agent_base_url() -> str:
    """Resolve the configured provider to an ADK HTTP base URL."""
    if AGENT_PROVIDER == "gcp":
        if not GCP_AGENT_URL:
            raise RuntimeError("AGENT_PROVIDER=gcp but GCP_AGENT_URL is not set")
        return GCP_AGENT_URL
    if AGENT_PROVIDER == "local":
        return LOCAL_AGENT_URL
    raise RuntimeError(f"Unsupported AGENT_PROVIDER: {AGENT_PROVIDER!r}")


def _text_of(event: dict) -> str:
    """The concatenated text of an ADK event (empty for tool-call events)."""
    parts = (event.get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts if p.get("text"))


def _tool_payloads(event: dict) -> list:
    """Tool response payloads in this event, for the name guard's allow-list."""
    parts = (event.get("content") or {}).get("parts") or []
    out = []
    for p in parts:
        resp = p.get("functionResponse") or p.get("function_response")
        if isinstance(resp, dict) and resp.get("response") is not None:
            out.append(resp["response"])
    return out


def _tool_names(event: dict) -> list[str]:
    """Tool names invoked in this event. ADK serialises them as functionCall."""
    parts = (event.get("content") or {}).get("parts") or []
    out = []
    for p in parts:
        call = p.get("functionCall") or p.get("function_call")
        if isinstance(call, dict) and call.get("name"):
            out.append(call["name"])
    return out


async def _ensure_session(client: httpx.AsyncClient, base: str, user_id: str, session_id: str) -> None:
    """Create the ADK session if it doesn't exist.

    A follow-up message reuses the same session_id, so the create call comes back
    "already exists" — ADK signals that with 409 (and some builds 400). Both mean
    the session is there, which is all we need, so treat them as success.
    """
    url = f"{base}/apps/{APP_NAME}/users/{user_id}/sessions/{session_id}"
    resp = await client.post(url, json={})
    if resp.status_code not in (200, 400, 409):
        resp.raise_for_status()


async def run(user_id: str, session_id: str, message: str, context: str | None = None):
    """Yield progress events, then one validated reply.

    Events are dicts the route serialises as SSE:
      {"tool": name, "label": human text}  — each distinct tool, as it is called
      {"reply": text, "tools": [...], "warning": str|None}  — the finished answer
    """
    base = agent_base_url()
    # Page context rides with the message rather than in the system prompt, so
    # it reflects where the user actually is when they ask.
    text = f"[Context: {context}]\n\n{message}" if context else message
    payload = {
        "app_name": APP_NAME,
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": text}]},
        "streaming": True,
    }

    seen: list[str] = []
    final_text = ""
    # Everything the tools actually returned. The agent is only allowed to name
    # what it fetched, so this is what the reply gets checked against.
    allow: set[str] = set()

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        await _ensure_session(client, base, user_id, session_id)
        async with client.stream("POST", f"{base}/run_sse", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if not data:
                    continue
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue

                for payload in _tool_payloads(event):
                    allow |= name_guard.tokens_in(payload)

                for name in _tool_names(event):
                    # ADK repeats a functionCall across partial and final
                    # events, so only the first sighting is progress.
                    if name not in seen:
                        seen.append(name)
                        yield {"tool": name, "label": TOOL_LABELS.get(name, name)}

                # Non-partial events carry the whole answer so far; partials are
                # fragments of it. Keeping only the last non-partial text avoids
                # the duplicated narration that concatenating every round gave.
                if not event.get("partial"):
                    chunk = _text_of(event)
                    if chunk:
                        final_text = chunk

    if not final_text.strip():
        # An upstream model failure (no access to the configured model, quota,
        # a safety block) ends the ADK stream without ever emitting text.
        # Returning "" made that indistinguishable from a blank answer, so the
        # client got silence instead of a reason.
        raise RuntimeError(
            "The agent returned no text. Check the agent logs — usually the "
            "configured model is unavailable to the project, or quota is exhausted."
        )

    bad = name_guard.check(final_text, allow)
    warning = None
    if bad:
        logger.warning(f"Name guard flagged {bad} in agent reply (tools: {seen})")
        warning = (
            "Heads up: " + ", ".join(bad) + " could not be matched to a current "
            "Premier League player, so treat that part as unreliable."
        )
    yield {"reply": final_text, "tools": seen, "warning": warning}


async def get_reply(user_id: str, session_id: str, message: str, context: str | None = None) -> str:
    """Non-streaming convenience: just the validated answer text."""
    async for event in run(user_id, session_id, message, context):
        if "reply" in event:
            return event["reply"]
    return ""
