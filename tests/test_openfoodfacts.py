from unittest.mock import Mock, patch

import pytest
import requests

from openfoodfacts import (
    ExternalAPIError,
    ProductNotFound,
    lookup_barcode,
    search_products,
)


@patch("openfoodfacts.requests.get")
def test_barcode_lookup(mock_get):
    mock_get.return_value = Mock(
        status_code=200,
        json=Mock(return_value={
            "product": {
                "code": "123456789",
                "product_name": "Almond Milk",
                "brands": "Example",
            }
        }),
    )

    product = lookup_barcode("123456789")

    assert product["product_name"] == "Almond Milk"
    assert product["ingredients_text"] == ""
    assert mock_get.call_args.kwargs["timeout"] == 15


@patch("openfoodfacts.requests.get")
def test_name_search(mock_get):
    mock_get.return_value = Mock(
        status_code=200,
        json=Mock(return_value={
            "products": [{"code": "123", "product_name": "Milk"}]
        }),
    )

    assert search_products("milk")[0]["barcode"] == "123"
    assert mock_get.call_args.kwargs["params"]["search_terms"] == "milk"


@patch("openfoodfacts.requests.get")
def test_missing_product(mock_get):
    mock_get.return_value = Mock(status_code=404)

    with pytest.raises(ProductNotFound):
        lookup_barcode("123")


@patch("openfoodfacts.requests.get", side_effect=requests.Timeout)
def test_timeout(mock_get):
    with pytest.raises(ExternalAPIError):
        lookup_barcode("123")


@patch("openfoodfacts.requests.get")
def test_invalid_json(mock_get):
    mock_get.return_value = Mock(
        status_code=200,
        json=Mock(side_effect=ValueError),
    )

    with pytest.raises(ExternalAPIError):
        lookup_barcode("123")