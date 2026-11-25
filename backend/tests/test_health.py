def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'keys_configured': 2, 'cache_enabled': True}


def test_health_reports_database_unavailable(client, monkeypatch):
    import app.api.routes as routes
    monkeypatch.setattr(routes, 'db_reachable', lambda: False)
    response = client.get('/health')
    assert response.status_code == 503
    assert response.json() == {'detail': 'service unavailable'}

