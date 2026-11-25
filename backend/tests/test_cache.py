def test_cross_session_cache_and_token_retention(client):
    first = client.post('/chat', json={'session_id': 'one', 'message': 'same'})
    second = client.post('/chat', json={'session_id': 'two', 'message': 'same'})
    assert second.json()['reply'] == first.json()['reply']
    assert second.json()['metadata']['resolution_source'] == 'LLM_CACHE'
    assert second.json()['metadata']['key_id'] is None
    assert second.json()['metadata']['input_tokens'] == first.json()['metadata']['input_tokens']
    assert len(client.app.state.calls) == 1


def test_different_prompt_and_history_miss(client):
    client.post('/chat', json={'session_id': 'one', 'message': 'one'})
    client.post('/chat', json={'session_id': 'two', 'message': 'two'})
    client.post('/chat', json={'session_id': 'one', 'message': 'next'})
    assert len(client.app.state.calls) == 3


def test_different_model_does_not_reuse_cached_answer(client):
    gateway = client.app.state.gateway
    first = client.post('/chat', json={'session_id': 'model-a', 'message': 'same prompt'})
    gateway.settings.llm_model = 'another-model'
    second = client.post('/chat', json={'session_id': 'model-b', 'message': 'same prompt'})
    assert first.json()['metadata']['resolution_source'] == 'LIVE_INFERENCE'
    assert second.json()['metadata']['resolution_source'] == 'LIVE_INFERENCE'
    assert len(client.app.state.calls) == 2

