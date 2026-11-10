import pytest
from fastapi.testclient import TestClient

from app.main import app, reset_storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_storage():
    reset_storage()


def create(name="Ноутбук", price=100.0):
    return client.post("/api/items", json={"name": name, "description": "опис", "price": price})


def test_list_empty():
    response = client.get("/api/items")
    assert response.status_code == 200
    assert response.json() == []


def test_create_item():
    response = create()
    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "Ноутбук", "description": "опис", "price": 100.0}


def test_get_item():
    create()
    response = client.get("/api/items/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Ноутбук"


def test_get_missing_item_returns_404():
    assert client.get("/api/items/42").status_code == 404


def test_update_item():
    create()
    response = client.put("/api/items/1", json={"name": "Телефон", "price": 50})
    assert response.status_code == 200
    assert response.json()["name"] == "Телефон"


def test_delete_item():
    create()
    assert client.delete("/api/items/1").status_code == 204
    assert client.get("/api/items/1").status_code == 404


def test_invalid_item_returns_422():
    response = client.post("/api/items", json={"name": "", "price": -1})
    assert response.status_code == 422


def test_openapi_available():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/items" in response.json()["paths"]
