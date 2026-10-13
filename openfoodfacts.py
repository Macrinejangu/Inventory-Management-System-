import requests


BASE_URL = "https://world.openfoodfacts.org"
HEADERS = {
    "User-Agent": (
        "InventoryManagementLab/1.0 "
        "(https://github.com/Macrinejangu/Inventory-Management-System-)"
    )
}
FIELDS = "code,product_name,brands,ingredients_text"


class ProductNotFound(Exception):
    pass


class ExternalAPIError(Exception):
    pass


def request_data(path, params=None):
    try:
        response = requests.get(
            f"{BASE_URL}{path}",
            params=params,
            headers=HEADERS,
            timeout=15,
        )

        if response.status_code == 404:
            raise ProductNotFound("Product not found.")

        response.raise_for_status()
        data = response.json()
    except requests.Timeout as error:
        raise ExternalAPIError("Product lookup timed out.") from error
    except requests.RequestException as error:
        raise ExternalAPIError("Product service is unavailable.") from error
    except ValueError as error:
        raise ExternalAPIError("Product service returned invalid JSON.") from error

    if not isinstance(data, dict):
        raise ExternalAPIError("Unexpected product service response.")

    return data


def normalize_product(product):
    if not isinstance(product, dict):
        raise ExternalAPIError("Invalid product data.")

    def text(field):
        value = product.get(field)
        return value.strip() if isinstance(value, str) else ""

    return {
        "barcode": text("code"),
        "product_name": text("product_name"),
        "brands": text("brands"),
        "ingredients_text": text("ingredients_text"),
    }


def lookup_barcode(barcode):
    if not isinstance(barcode, str):
        raise ValueError("barcode must be a string.")

    barcode = barcode.strip()
    if not barcode.isascii() or not barcode.isdigit():
        raise ValueError("barcode must contain digits only.")

    data = request_data(
        f"/api/v3.6/product/{barcode}.json",
        params={"fields": FIELDS},
    )

    if data.get("status") == 0 or data.get("product") is None:
        raise ProductNotFound("Product not found.")

    product = normalize_product(data["product"])
    product["barcode"] = product["barcode"] or barcode
    return product


def search_products(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Provide a product name.")

    data = request_data(
        "/cgi/search.pl",
        params={
            "search_terms": name.strip(),
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 10,
            "fields": FIELDS,
        },
    )

    products = data.get("products")
    if not isinstance(products, list):
        raise ExternalAPIError("Unexpected search response.")

    return [normalize_product(product) for product in products]