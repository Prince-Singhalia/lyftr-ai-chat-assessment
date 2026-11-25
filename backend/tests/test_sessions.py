def test_assistant_metadata_is_stored(client):
    response = client.post('/chat', json={'session_id': 's', 'message': 'hello'})
    history = client.get('/sessions/s/messages').json()
    assert history['messages'][1]['metadata']['output_tokens'] == response.json()['metadata']['output_tokens']

