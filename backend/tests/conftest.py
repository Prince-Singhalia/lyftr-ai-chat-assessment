import os
import sys
from pathlib import Path

import json
import pytest
import tempfile

DB_PATH = Path(tempfile.gettempdir()) / f"resilient-ai-chat-{os.getpid()}.db"
sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ.update({"LLM_API_KEYS": "test-one,test-two", "LLM_MODEL": "test-model", "DATABASE_URL": f"sqlite:///{DB_PATH}", "ENABLE_FAILURE_SIMULATION": "true", "LITELLM_CACHE": "true"})

from app.config import get_settings
from app.main import create_app
from app.api.routes import chat as chat_route, health as health_route, history as history_route
from app.schemas import ChatRequest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request


@pytest.fixture(autouse=True)
def clean_db(tmp_path):
    global DB_PATH
    DB_PATH = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
    get_settings.cache_clear()
    yield


@pytest.fixture
def client(monkeypatch):
    app = create_app()
    calls = []
    def fake_call(messages, api_key):
        calls.append((messages, api_key))
        return {"choices": [{"message": {"content": f"reply from {api_key}"}}], "usage": {"prompt_tokens": len(messages) + 10, "completion_tokens": 3}}
    app.state.gateway._call_litellm = fake_call
    app.state.calls = calls

    class SyncASGIClient:
        def _response(self, status, body):
            return type('Response', (), {'status_code': status, 'json': lambda self: body})()
        def get(self, url, **kwargs):
            try:
                if url == '/health': return self._response(200, health_route(type('Request', (), {'app': app})()))
                session_id = url.split('/')[2]
                return self._response(200, history_route(session_id).model_dump())
            except HTTPException as error: return self._response(error.status_code, {'detail': error.detail})
        def post(self, url, **kwargs):
            try:
                raw = json.loads(kwargs.get('content', '{}')) if 'content' in kwargs else kwargs.get('json', {})
                payload = ChatRequest.model_validate(raw)
                headers = kwargs.get('headers', {})
                request = type('Request', (), {'app': app})()
                return self._response(200, chat_route(payload, request, headers.get('X-Simulate-Failure')).model_dump())
            except (ValidationError, json.JSONDecodeError): return self._response(422, {'detail': 'validation error'})
            except HTTPException as error: return self._response(error.status_code, {'detail': error.detail})
    instance = SyncASGIClient()
    instance.app = app
    yield instance

