import pytest

from app import create_app


@pytest.fixture
def client():
    application = create_app()
    application.config["TESTING"] = True
    return application.test_client()


def add_item(client):
    response = client.post("/inventory", json={
        "product_name": "Almond Milk",
        "price": 250,
        "stock": 10,
    })
    assert response.status_code == 201
    return response.get_json()


def test_empty_inventory(client):
    response = client.get("/inventory")
    assert response.status_code == 200
    assert response.get_json() == []


def test_create_and_read(client):
    item = add_item(client)

    assert item["id"] > 0
    assert item["product_name"] == "Almond Milk"
    assert client.get("/inventory").get_json() == [item]
    assert client.get(
        f"/inventory/{item['id']}"
    ).get_json() == item


def test_patch_preserves_other_fields(client):
    item = add_item(client)
    response = client.patch(
        f"/inventory/{item['id']}",
        json={"price": 0, "stock": 0},
    )

    assert response.status_code == 200
    updated = response.get_json()
    assert updated["price"] == 0
    assert updated["stock"] == 0
    assert updated["product_name"] == item["product_name"]


def test_invalid_patch_preserves_item(client):
    item = add_item(client)
    response = client.patch(
        f"/inventory/{item['id']}",
        json={"product_name": "Changed", "stock": -1},
    )

    assert response.status_code == 400
    assert client.get(
        f"/inventory/{item['id']}"
    ).get_json() == item


def test_delete_and_id_reuse(client):
    first = add_item(client)
    response = client.delete(f"/inventory/{first['id']}")

    assert response.status_code == 204
    assert response.data == b""
    assert client.get("/inventory").get_json() == []

    second = add_item(client)
    assert second["id"] > first["id"]


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_missing_item(client, method):
    kwargs = {"json": {"stock": 1}} if method == "patch" else {}
    response = getattr(client, method)("/inventory/999", **kwargs)
    assert response.status_code == 404


@pytest.mark.parametrize("body", [
    {},
    [],
    {"product_name": "", "price": 10, "stock": 1},
    {"product_name": " ", "price": 10, "stock": 1},
    {"product_name": "Milk", "price": -1, "stock": 1},
    {"product_name": "Milk", "price": "NaN", "stock": 1},
    {"product_name": "Milk", "price": "Infinity", "stock": 1},
    {"product_name": "Milk", "price": "1.001", "stock": 1},
    {"product_name": "Milk", "price": True, "stock": 1},
    {"product_name": "Milk", "price": 10, "stock": -1},
    {"product_name": "Milk", "price": 10, "stock": True},
    {"product_name": "Milk", "price": 10, "stock": 1.5},
    {"product_name": "Milk", "price": 10, "stock": 1, "id": 99},
])
def test_invalid_creation(client, body):
    response = client.post("/inventory", json=body)

    assert response.status_code == 400
    assert client.get("/inventory").get_json() == []


def test_malformed_json(client):
    response = client.post(
        "/inventory",
        data="{",
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.is_json


def test_empty_patch(client):
    item = add_item(client)
    response = client.patch(
        f"/inventory/{item['id']}",
        json={},
    )
    assert response.status_code == 400


def test_app_instances_are_isolated():
    first = create_app().test_client()
    second = create_app().test_client()

    add_item(first)

    assert second.get("/inventory").get_json() == []