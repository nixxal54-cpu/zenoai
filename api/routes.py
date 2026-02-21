from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.db.database import create_session
from app.services.orchestrator import orchestrator
from app.core.rate_limit import check_rate_limit
import json

router = APIRouter()

class ChatRequest(BaseModel):
    session_id: str
    message: str

@router.get("/health")
async def health():
    return {"status": "operational", "system": "ZenoAi"}

@router.post("/session/new")
async def new_session():
    sid = await create_session()
    return {"session_id": sid}

@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    check_rate_limit(request.client.host)
    
    async def event_generator():
        try:
            async for chunk in orchestrator.process_chat_stream(req.session_id, req.message):
                # Check for client disconnect
                if await request.is_disconnected():
                    break
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': 'Internal system error', 'detail': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
