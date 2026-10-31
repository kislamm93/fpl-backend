"""Chat proxy to the captaincy agent.

The browser hits these routes; they stream from / call the cloud agent (via
app.services.agent_service) and return only clean text — never the raw ADK
event trace. Provider is chosen by AGENT_PROVIDER (see agent_service).
"""
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services import agent_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    responses={502: {"description": "Agent upstream error"}},
)


class ChatRequest(BaseModel):
    message: str
    # No auth: the client supplies a stable user_id (its FPL manager id or a
    # persisted anonymous uuid) and a per-conversation session_id.
    user_id: str
    session_id: str
    # What the user is looking at ("Market Odds / Goalscorers tab, GW9"), so
    # "who's the best differential here?" resolves without them spelling it out.
    context: str | None = None


@router.post(
    "/chat/stream",
    summary="Stream a captaincy chat reply (SSE)",
    description=(
        "Server-Sent Events. Progress first — `data: {\"tool\": \"goalscorer_odds\", "
        "\"label\": \"reading goalscorer odds\"}` per tool — then one "
        "`data: {\"reply\": \"...\", \"tools\": [...], \"warning\": null}`, then "
        "`data: {\"done\": true}`. The reply is buffered and name-checked before it is "
        "sent, so no unverified player name ever reaches the client."
    ),
)
async def chat_stream(req: ChatRequest):
    async def event_gen():
        try:
            async for event in agent_service.run(
                req.user_id, req.session_id, req.message, req.context
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # surface upstream failures to the client stream
            logging.error(f"Agent stream error: {exc}", exc_info=True)
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/chat",
    summary="Get a captaincy chat reply (non-streaming)",
    description="Returns the whole answer as {\"reply\": \"...\"}. Use /chat/stream for live typing.",
)
async def chat(req: ChatRequest):
    try:
        reply = await agent_service.get_reply(
            req.user_id, req.session_id, req.message, req.context
        )
        return {"reply": reply}
    except Exception as exc:
        logging.error(f"Agent chat error: {exc}", exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc))
