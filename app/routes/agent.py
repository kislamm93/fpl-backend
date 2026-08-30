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


@router.post(
    "/chat/stream",
    summary="Stream a captaincy chat reply (SSE)",
    description="Server-Sent Events; each message is `data: {\"delta\": \"...\"}`, ending with `data: {\"done\": true}`.",
)
async def chat_stream(req: ChatRequest):
    async def event_gen():
        try:
            async for delta in agent_service.stream_reply(req.user_id, req.session_id, req.message):
                yield f"data: {json.dumps({'delta': delta})}\n\n"
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
        reply = await agent_service.get_reply(req.user_id, req.session_id, req.message)
        return {"reply": reply}
    except Exception as exc:
        logging.error(f"Agent chat error: {exc}", exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc))
