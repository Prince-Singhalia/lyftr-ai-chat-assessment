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

