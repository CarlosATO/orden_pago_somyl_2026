import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    return app

def test_health_endpoint(client, app):
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('status') == 'ok'
