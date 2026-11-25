def test_first_and_second_turn(client):
    first = client.post('/chat', json={'session_id': 's1', 'message': 'Hello'})
    assert first.status_code == 200
    assert first.json()['metadata']['resolution_source'] == 'LIVE_INFERENCE'
    second = client.post('/chat', json={'session_id': 's1', 'message': 'Follow up'})
    assert second.status_code == 200
    assert len(client.app.state.calls) == 2
    assert [m['content'] for m in client.app.state.calls[-1][0]] == ['Hello', 'reply from test-one', 'Follow up']


def test_sessions_are_isolated_and_history_hides_system(client):
    client.post('/chat', json={'session_id': 's1', 'message': 'Hi', 'system_prompt': 'secret'})
    client.post('/chat', json={'session_id': 's2', 'message': 'Hi'})
    history = client.get('/sessions/s1/messages').json()
    assert [m['role'] for m in history['messages']] == ['user', 'assistant']
    assert all('secret' not in m['content'] for m in history['messages'])
    assert client.get('/sessions/unknown/messages').status_code == 404


def test_validation(client):
    assert client.post('/chat', json={'message': 'x'}).status_code == 422
    assert client.post('/chat', json={'session_id': '', 'message': 'x'}).status_code == 422
    assert client.post('/chat', json={'session_id': 's'}).status_code == 422
    assert client.post('/chat', json={'session_id': 's', 'message': ''}).status_code == 422
    assert client.post('/chat', json={'session_id': ' ', 'message': 'x'}).status_code == 422
    assert client.post('/chat', json={'session_id': 's', 'message': ' '}).status_code == 422
    assert client.post('/chat', json={'session_id': 's', 'message': 'x' * 4001}).status_code == 422
    assert client.post('/chat', content='{bad json', headers={'content-type': 'application/json'}).status_code == 422


def test_history_is_oldest_first_and_system_prompt_is_not_exposed(client):
    client.post('/chat', json={'session_id': 'ordered', 'message': 'first', 'system_prompt': 'private system text'})
    client.post('/chat', json={'session_id': 'ordered', 'message': 'second'})
    history = client.get('/sessions/ordered/messages').json()['messages']
    assert [item['content'] for item in history] == ['first', 'reply from test-one', 'second', 'reply from test-one']
    assert all('private system text' not in item['content'] for item in history)

