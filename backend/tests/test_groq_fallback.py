def test_gemini_key_one_failure_falls_back_to_key_two(client):
    def provider(messages, api_key, model=None):
        if api_key == 'test-one':
            error = RuntimeError('temporarily unavailable')
            error.status_code = 503
            raise error
        return {'choices': [{'message': {'content': 'Gemini key two answer'}}], 'usage': {'prompt_tokens': 11, 'completion_tokens': 5}}
    client.app.state.gateway._call_litellm = provider
    response = client.post('/chat', json={'session_id': 'key-two', 'message': 'hello'})
    assert response.status_code == 200
    assert response.json()['metadata']['key_id'] == 'key_2'
    assert response.json()['metadata']['model'] == 'test-model'
    assert response.json()['metadata']['fallback_attempts'] == 1


def test_both_gemini_deployments_fail_then_groq_succeeds(client):
    calls = []
    def provider(messages, api_key, model=None):
        calls.append((api_key, model))
        if api_key != 'test-groq':
            error = RuntimeError('temporarily unavailable')
            error.status_code = 503
            raise error
        return {'choices': [{'message': {'content': 'Groq answer'}}], 'usage': {'prompt_tokens': 27, 'completion_tokens': 8}}
    client.app.state.gateway._call_litellm = provider
    response = client.post('/chat', json={'session_id': 'groq-live', 'message': 'hello'})
    body = response.json()
    assert response.status_code == 200
    assert calls == [('test-one', None), ('test-two', None), ('test-groq', 'groq/openai/gpt-oss-20b')]
    assert body['reply'] == 'Groq answer'
    assert body['metadata']['model'] == 'groq/openai/gpt-oss-20b'
    assert body['metadata']['key_id'] == 'groq'
    assert body['metadata']['fallback_attempts'] == 2
    assert body['metadata']['input_tokens'] == 27
    assert body['metadata']['output_tokens'] == 8
    assert client.get('/sessions/groq-live/messages').status_code == 200


def test_groq_response_cache_retains_model_reply_and_usage_across_sessions(client):
    calls = []
    def provider(messages, api_key, model=None):
        calls.append((api_key, model))
        if api_key != 'test-groq':
            error = RuntimeError('temporarily unavailable')
            error.status_code = 503
            raise error
        return {'choices': [{'message': {'content': 'Cached Groq answer'}}], 'usage': {'prompt_tokens': 33, 'completion_tokens': 9}}
    client.app.state.gateway._call_litellm = provider
    live = client.post('/chat', json={'session_id': 'first-groq', 'message': 'same prompt'}).json()
    cached = client.post('/chat', json={'session_id': 'second-groq', 'message': 'same prompt'}).json()
    assert cached['reply'] == live['reply']
    assert cached['metadata']['resolution_source'] == 'LLM_CACHE'
    assert cached['metadata']['model'] == 'groq/openai/gpt-oss-20b'
    assert cached['metadata']['key_id'] is None
    assert cached['metadata']['fallback_attempts'] == 0
    assert cached['metadata']['input_tokens'] == 33
    assert cached['metadata']['output_tokens'] == 9
    assert len(calls) == 3


def test_groq_failure_simulation_bypasses_cache(client):
    first = client.post('/chat', json={'session_id': 'seed', 'message': 'same prompt'})
    assert first.status_code == 200
    failed = client.post('/chat', headers={'X-Simulate-Failure': 'key_1=503,key_2=503,groq=503'}, json={'session_id': 'failed', 'message': 'same prompt'})
    assert failed.status_code == 503
    assert client.get('/sessions/failed/messages').status_code == 404


def test_groq_disabled_or_unconfigured_keeps_gemini_only(client):
    gateway = client.app.state.gateway
    gateway.settings.groq_api_key = ''
    result = client.post('/chat', headers={'X-Simulate-Failure': 'key_1=503,key_2=503'}, json={'session_id': 'gemini-only', 'message': 'hello'})
    assert result.status_code == 503
    assert client.get('/sessions/gemini-only/messages').status_code == 404

