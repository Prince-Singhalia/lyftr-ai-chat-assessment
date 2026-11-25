import time
from fastapi import APIRouter, Header, HTTPException, Request

from ..database import db_reachable, fetch_messages, store_exchange
from ..schemas import ChatRequest, ChatResponse, HistoryResponse
from ..services.llm_gateway import ProvidersUnavailable

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict:
    gateway = request.app.state.gateway
    if not db_reachable() or len(gateway.keys) < 2 or not gateway.cache_initialized:
        raise HTTPException(status_code=503, detail="service unavailable")
    return {"status": "ok", "keys_configured": len(gateway.keys), "cache_enabled": gateway.cache.enabled}


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request, x_simulate_failure: str | None = Header(default=None)) -> ChatResponse:
    existing = fetch_messages(payload.session_id)
    messages: list[dict[str, str]] = []
    if payload.system_prompt:
        messages.append({"role": "system", "content": payload.system_prompt})
    messages.extend({"role": item["role"], "content": item["content"]} for item in existing)
    messages.append({"role": "user", "content": payload.message})
    started = time.perf_counter()
    try:
        result = request.app.state.gateway.complete(messages, x_simulate_failure)
    except ProvidersUnavailable:
        raise HTTPException(status_code=503, detail="all providers unavailable")
    latency_ms = int((time.perf_counter() - started) * 1000)
    metadata = {"resolution_source": result.source, "model": result.model, "latency_ms": latency_ms, "input_tokens": result.input_tokens, "output_tokens": result.output_tokens, "key_id": result.key_id, "fallback_attempts": result.fallback_attempts}
    store_exchange(payload.session_id, payload.message, result.reply, metadata)
    return ChatResponse(session_id=payload.session_id, reply=result.reply, metadata=metadata)


@router.get("/sessions/{session_id}/messages", response_model=HistoryResponse)
def history(session_id: str) -> HistoryResponse:
    messages = fetch_messages(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="session not found")
    return HistoryResponse(session_id=session_id, messages=messages)

