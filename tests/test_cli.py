from unittest.mock import Mock, patch

import pytest
import requests

from cli import main


@pytest.mark.parametrize("arguments, method, path, payload, params", [
    (["list"], "GET", "/inventory", None, None),
    (["show", "1"], "GET", "/inventory/1", None, None),
    (
        ["add", "--name", "Milk", "--price", "250", "--stock", "10"],
        "POST", "/inventory",
        {"product_name": "Milk", "price": "250", "stock": 10},
        None,
    ),
    (
        ["update", "1", "--stock", "0"],
        "PATCH", "/inventory/1", {"stock": 0}, None,
    ),
    (["delete", "1"], "DELETE", "/inventory/1", None, None),
    (
        ["search", "almond milk"],
        "GET", "/products/search", None, {"name": "almond milk"},
    ),
    (["barcode", "123"], "GET", "/products/barcode/123", None, None),
    (
        ["import", "123", "--price", "250", "--stock", "10"],
        "POST", "/inventory/import",
        {"barcode": "123", "price": "250", "stock": 10},
        None,
    ),
])
def test_commands(arguments, method, path, payload, params):
    response = Mock(status_code=200)
    response.json.return_value = {"message": "Success"}

    with patch("cli.requests.request", return_value=response) as request:
        assert main(arguments) == 0

    request.assert_called_once_with(
        method,
        f"http://127.0.0.1:5555{path}",
        json=payload,
        params=params,
        timeout=20,
    )


def test_delete_without_json(capsys):
    response = Mock(status_code=204)

    with patch("cli.requests.request", return_value=response):
        assert main(["delete", "1"]) == 0

    response.json.assert_not_called()
    assert "Item deleted" in capsys.readouterr().out


def test_connection_failure(capsys):
    with patch(
        "cli.requests.request",
        side_effect=requests.ConnectionError("Server offline"),
    ):
        assert main(["list"]) == 1

    assert "Unable to reach" in capsys.readouterr().err


def test_server_error(capsys):
    response = Mock(status_code=404)
    response.json.return_value = {"error": "Item not found"}

    with patch("cli.requests.request", return_value=response):
        assert main(["show", "999"]) == 1

    assert "404" in capsys.readouterr().err


def test_invalid_response():
    response = Mock(status_code=200)
    response.json.side_effect = ValueError

    with patch("cli.requests.request", return_value=response):
        assert main(["list"]) == 1


def test_empty_update():
    with patch("cli.requests.request") as request:
        with pytest.raises(SystemExit) as error:
            main(["update", "1"])

    assert error.value.code == 2
    request.assert_not_called()


def test_invalid_stock():
    with pytest.raises(SystemExit) as error:
        main(["add", "--name", "Milk", "--price", "250", "--stock", "abc"])

    assert error.value.code == 2