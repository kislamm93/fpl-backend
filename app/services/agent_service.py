"""Adapter to the captaincy agent, selected by AGENT_PROVIDER.

The frontend never talks to the agent directly. This module proxies to whichever
provider is configured and normalizes the response so callers only ever see clean
text (the raw ADK /run_sse stream is a huge event trace — tool calls, tool
payloads, reasoning signatures — none of which a chat client should handle).

Providers:
  gcp   -> the ADK agent on Cloud Run   (GCP_AGENT_URL)      [default]
  local -> a local `adk api_server`      (LOCAL_AGENT_URL)
  aws   -> Bedrock AgentCore             (not wired yet — kept for revival)

Both gcp and local speak the same ADK HTTP API, so they differ only by base URL.
"""
import json
import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "gcp").lower()
# Defaults to the deployed Cloud Run agent so prod works without extra config;
# override via env for a different deployment.
GCP_AGENT_URL = os.getenv("GCP_AGENT_URL", "https://fpl-agent-44q5brj2va-uc.a.run.app").rstrip("/")
LOCAL_AGENT_URL = os.getenv("LOCAL_AGENT_URL", "http://127.0.0.1:8080").rstrip("/")
AWS_AGENT_RUNTIME_ARN = os.getenv("AWS_AGENT_RUNTIME_ARN", "")  # future

APP_NAME = os.getenv("AGENT_APP_NAME", "fpl_agent")

# The agent does tool calls (odds + player fetches) before the first token, so
# give it room; read timeout is disabled so a long stream is never cut off.
_TIMEOUT = httpx.Timeout(180.0, connect=10.0, read=None)


def agent_base_url() -> str:
    """Resolve the configured provider to an ADK HTTP base URL."""
    if AGENT_PROVIDER == "gcp":
        if not GCP_AGENT_URL:
            raise RuntimeError("AGENT_PROVIDER=gcp but GCP_AGENT_URL is not set")
        return GCP_AGENT_URL
    if AGENT_PROVIDER == "local":
        return LOCAL_AGENT_URL
    if AGENT_PROVIDER == "aws":
        raise RuntimeError("AGENT_PROVIDER=aws is not implemented yet")
    raise RuntimeError(f"Unsupported AGENT_PROVIDER: {AGENT_PROVIDER!r}")


def _text_of(event: dict) -> str:
    """The concatenated text of an ADK event (empty for tool-call events)."""
    parts = (event.get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts if p.get("text"))


async def _ensure_session(client: httpx.AsyncClient, base: str, user_id: str, session_id: str) -> None:
    """Create the ADK session if it doesn't exist. A 400 means it already does."""
    url = f"{base}/apps/{APP_NAME}/users/{user_id}/sessions/{session_id}"
    resp = await client.post(url, json={})
    if resp.status_code not in (200, 400):
        resp.raise_for_status()


async def stream_reply(user_id: str, session_id: str, message: str):
    """Yield the agent's answer as text deltas, hiding the tool-call trace.

    Uses ADK streaming: partial events carry incremental text; the final
    (non-partial) event repeats the whole answer, so we emit partials as they
    arrive and fall back to the final text only if nothing streamed.
    """
    base = agent_base_url()
    payload = {
        "app_name": APP_NAME,
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": message}]},
        "streaming": True,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        await _ensure_session(client, base, user_id, session_id)
        streamed_any = False
        final_text = ""
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
                text = _text_of(event)
                if not text:
                    continue
                if event.get("partial"):
                    streamed_any = True
                    yield text
                else:
                    final_text = text
        if not streamed_any and final_text:
            yield final_text


async def get_reply(user_id: str, session_id: str, message: str) -> str:
    """Non-streaming convenience: collect the whole answer into one string."""
    chunks = [delta async for delta in stream_reply(user_id, session_id, message)]
    return "".join(chunks)
