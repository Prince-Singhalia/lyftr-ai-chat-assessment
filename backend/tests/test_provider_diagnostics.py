import logging
import sys
import types

import pytest

from app.services.llm_gateway import LLMGateway, _error_category
from app.config import Settings


def test_key_pool_trims_and_keeps_order():
    assert Settings(llm_api_keys="  alpha , beta  ,, ").api_keys == ["alpha", "beta"]


def test_explicit_gemini_api_key_forwarding(client, monkeypatch):
    captured = []
    fake = types.ModuleType("litellm")
    fake.cache = object()
    fake.completion = lambda **kwargs: captured.append(kwargs) or {"choices": [{"message": {"content": "ok"}}]}
    fake.Cache = lambda: object()
    monkeypatch.setitem(sys.modules, "litellm", fake)
    gateway = client.app.state.gateway
    gateway.settings.llm_model = "gemini/gemini-3.8-flash"
    LLMGateway._call_litellm(gateway, [{"role": "user", "content": "hello"}], "individual-key")
    assert captured[0]["model"] == "gemini/gemini-3.8-flash"
    assert captured[0]["api_key"] == "individual-key"
    assert "cache" not in captured[0]


def test_diagnostic_checks_each_key_independently(client):
    calls = []
    def probe(model, api_key, prompt):
        calls.append((model, api_key, prompt))
        if api_key == "test-one":
            raise RuntimeError("invalid api key")
        return {"choices": [{"message": {"content": "Gemini connection successful."}}]}
    client.app.state.gateway._diagnostic_completion = probe
    result = client.app.state.gateway.diagnose_keys(model="gemini/gemini-3.8-flash")
    assert [call[1] for call in calls] == ["test-one", "test-two"]
    assert all(call[0] == "gemini/gemini-3.8-flash" for call in calls)
    assert calls[0][2] == "Reply with exactly: Gemini connection successful."
    assert result == [
        {"key_id": "key_1", "success": False, "model": "gemini/gemini-3.8-flash", "error_category": "authentication", "http_status": None},
        {"key_id": "key_2", "success": True, "model": "gemini/gemini-3.8-flash", "error_category": None, "http_status": None},
    ]
    assert "test-one" not in str(result) and "test-two" not in str(result)


@pytest.mark.parametrize(("status", "message", "expected"), [
    (401, "invalid key", "authentication"),
    (429, "rate limited", "rate_limit"),
    (404, "model not found", "model_not_found"),
    (None, "request timed out", "timeout"),
])
def test_provider_error_categories(status, message, expected):
    error = RuntimeError(message)
    error.status_code = status
    assert _error_category(error) == expected


def test_failover_logs_sanitized_and_returns_real_second_key_answer(client, caplog):
    secret_one, secret_two = client.app.state.gateway.keys
    def fail_first(messages, api_key):
        if api_key == secret_one:
            error = RuntimeError(f"invalid api key={secret_one} Authorization: Bearer {secret_one}")
            error.status_code = 401
            raise error
        return {"choices": [{"message": {"content": "real Gemini response"}}], "usage": {"prompt_tokens": 7, "completion_tokens": 4}}
    client.app.state.gateway._call_litellm = fail_first
    with caplog.at_level(logging.WARNING):
        response = client.post('/chat', json={'session_id': 'provider', 'message': 'probe'})
    assert response.status_code == 200
    assert response.json()['reply'] == 'real Gemini response'
    assert response.json()['metadata']['key_id'] == 'key_2'
    assert response.json()['metadata']['fallback_attempts'] == 1
    assert secret_one not in caplog.text and secret_two not in caplog.text
    assert 'key_id=key_1' in caplog.text and 'status=401' in caplog.text and 'authentication' in caplog.text


def test_all_provider_failures_leave_history_empty(client):
    def fail(messages, api_key):
        raise TimeoutError("network timed out")
    client.app.state.gateway._call_litellm = fail
    response = client.post('/chat', json={'session_id': 'all-failed', 'message': 'hello'})
    assert response.status_code == 503
    assert response.json() == {'detail': 'all providers unavailable'}
    assert client.get('/sessions/all-failed/messages').status_code == 404


def test_simulated_failover_bypasses_cache(client):
    client.post('/chat', json={'session_id': 'cache-seed', 'message': 'same prompt'})
    result = client.post('/chat', headers={'X-Simulate-Failure': 'key_1=429'}, json={'session_id': 'new-session', 'message': 'same prompt'})
    assert result.status_code == 200
    assert result.json()['metadata']['resolution_source'] == 'LIVE_INFERENCE'
    assert result.json()['metadata']['key_id'] == 'key_2'
    assert result.json()['metadata']['fallback_attempts'] == 1
    assert len(client.app.state.calls) == 2

