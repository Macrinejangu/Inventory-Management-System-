from copy import deepcopy
from decimal import Decimal, InvalidOperation
from itertools import count

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException


def validate_item(data, partial=False):
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")

    allowed = {
        "barcode", "product_name", "brands",
        "ingredients_text", "price", "stock",
    }
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(
            f"Unknown fields: {', '.join(sorted(unknown))}"
        )

    if not partial:
        missing = {"product_name", "price", "stock"} - set(data)
        if missing:
            raise ValueError(
                f"Missing fields: {', '.join(sorted(missing))}"
            )
    elif not data:
        raise ValueError("Provide at least one field to update.")

    result = {}

    for field in ("barcode", "product_name", "brands", "ingredients_text"):
        if field in data:
            value = data[field]
            if not isinstance(value, str):
                raise ValueError(f"{field} must be a string.")
            value = value.strip()
            if field == "product_name" and not value:
                raise ValueError("product_name must not be blank.")
            result[field] = value

    if "stock" in data:
        stock = data["stock"]
        if type(stock) is not int or stock < 0:
            raise ValueError("stock must be a non-negative integer.")
        result["stock"] = stock

    if "price" in data:
        price = data["price"]
        if isinstance(price, bool) or not isinstance(
            price, (int, float, str)
        ):
            raise ValueError("price must be a non-negative number.")

        try:
            number = Decimal(str(price))
        except InvalidOperation:
            raise ValueError("price must be a non-negative number.")

        if not number.is_finite() or number < 0:
            raise ValueError("price must be a finite non-negative number.")
        if number > Decimal("999999999.99"):
            raise ValueError("price exceeds the supported maximum.")
        if number != number.quantize(Decimal("0.01")):
            raise ValueError("price must have at most two decimal places.")

        result["price"] = float(number)

    return result


def create_app(initial_inventory=None):
    app = Flask(__name__)

    inventory = deepcopy(initial_inventory or [])
    ids = count(max((item["id"] for item in inventory), default=0) + 1)

    app.config["INVENTORY"] = inventory

    def find_item(item_id):
        return next(
            (item for item in inventory if item["id"] == item_id),
            None,
        )

    @app.errorhandler(ValueError)
    def invalid_input(error):
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify({"error": error.description}), error.code

    @app.get("/")
    def home():
        return jsonify({"message": "Inventory Management API"}), 200

    @app.get("/inventory")
    def list_inventory():
        return jsonify(inventory), 200

    @app.get("/inventory/<int:item_id>")
    def show_item(item_id):
        item = find_item(item_id)
        if item is None:
            return jsonify({"error": "Inventory item not found."}), 404
        return jsonify(item), 200

    @app.post("/inventory")
    def create_item():
        data = validate_item(request.get_json())
        item = {
            "id": next(ids),
            "barcode": "",
            "brands": "",
            "ingredients_text": "",
            **data,
        }
        inventory.append(item)
        return jsonify(item), 201

    @app.patch("/inventory/<int:item_id>")
    def update_item(item_id):
        item = find_item(item_id)
        if item is None:
            return jsonify({"error": "Inventory item not found."}), 404

        changes = validate_item(request.get_json(), partial=True)
        item.update(changes)
        return jsonify(item), 200

    @app.delete("/inventory/<int:item_id>")
    def delete_item(item_id):
        item = find_item(item_id)
        if item is None:
            return jsonify({"error": "Inventory item not found."}), 404

        inventory.remove(item)
        return "", 204

    return app


app = create_app()


if __name__ == "__main__":
    app.run(port=5555, debug=True)