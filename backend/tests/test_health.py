def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'keys_configured': 2, 'cache_enabled': True}

