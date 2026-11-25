def test_failover_and_all_failures(client):
    result = client.post('/chat', headers={'X-Simulate-Failure': 'key_1=429'}, json={'session_id': 's', 'message': 'try'})
    assert result.status_code == 200
    assert result.json()['metadata']['key_id'] == 'key_2'
    assert result.json()['metadata']['fallback_attempts'] == 1
    failed = client.post('/chat', headers={'X-Simulate-Failure': '*=429'}, json={'session_id': 'fail', 'message': 'nope'})
    assert failed.status_code == 503 and failed.json() == {'detail': 'all providers unavailable'}
    assert client.get('/sessions/fail/messages').status_code == 404


def test_multiple_failures(client):
    result = client.post('/chat', headers={'X-Simulate-Failure': 'key_1=429,key_2=500'}, json={'session_id': 's', 'message': 'try'})
    assert result.status_code == 503

