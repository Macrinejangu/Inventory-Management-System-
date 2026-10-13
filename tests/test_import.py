from unittest.mock import patch

import pytest

from app import create_app
from openfoodfacts import ExternalAPIError, ProductNotFound


@pytest.fixture
def client():
    application = create_app()
    application.config["TESTING"] = True
    return application.test_client()


@pytest.fixture
def product():
    return {
        "barcode": "123",
        "product_name": "Almond Milk",
        "brands": "Example",
        "ingredients_text": "Water, almonds",
    }


def test_barcode_route(client, product):
    with patch("app.lookup_barcode", return_value=product):
        response = client.get("/products/barcode/123")

    assert response.status_code == 200
    assert response.get_json()["barcode"] == "123"
    assert client.get("/inventory").get_json() == []


def test_search_route(client, product):
    with patch("app.search_products", return_value=[product]) as search:
        response = client.get("/products/search?name=almond")

    assert response.status_code == 200
    assert len(response.get_json()) == 1
    search.assert_called_once_with("almond")


def test_import_product(client, product):
    with patch("app.lookup_barcode", return_value=product):
        response = client.post("/inventory/import", json={
            "barcode": "123",
            "price": 250,
            "stock": 10,
        })

    assert response.status_code == 201
    item = response.get_json()
    assert item["product_name"] == "Almond Milk"
    assert item["price"] == 250
    assert item["stock"] == 10
    assert client.get("/inventory").get_json() == [item]


def test_invalid_import_does_not_call_service(client):
    with patch("app.lookup_barcode") as lookup:
        response = client.post("/inventory/import", json={
            "barcode": "123",
            "price": 250,
            "stock": -1,
        })

    assert response.status_code == 400
    lookup.assert_not_called()
    assert client.get("/inventory").get_json() == []


@pytest.mark.parametrize("error, expected_status", [
    (ProductNotFound("Product not found."), 404),
    (ExternalAPIError("Service unavailable."), 502),
])
def test_import_failure_preserves_inventory(client, error, expected_status):
    with patch("app.lookup_barcode", side_effect=error):
        response = client.post("/inventory/import", json={
            "barcode": "123",
            "price": 250,
            "stock": 10,
        })

    assert response.status_code == expected_status
    assert client.get("/inventory").get_json() == []