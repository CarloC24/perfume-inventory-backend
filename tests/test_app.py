"""Tests for the app wiring in src/main.py."""

from src.config import settings


def test_hello(client):
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_app_title_comes_from_settings(client):
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == settings.APP_TITLE


def test_the_perfumes_router_is_mounted(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths) >= {"/perfumes", "/perfumes/{perfume_id}"}


def test_unknown_paths_404(client):
    assert client.get("/nope").status_code == 404
