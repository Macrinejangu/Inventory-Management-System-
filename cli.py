import argparse
import json
import os
import sys

import requests


def build_parser():
    parser = argparse.ArgumentParser(description="Inventory management CLI")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("INVENTORY_API_URL", "http://127.0.0.1:5555"),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list")

    show = commands.add_parser("show")
    show.add_argument("id", type=int)

    add = commands.add_parser("add")
    add.add_argument("--name", required=True)
    add.add_argument("--price", required=True)
    add.add_argument("--stock", type=int, required=True)
    add.add_argument("--barcode")
    add.add_argument("--brands")
    add.add_argument("--ingredients")

    update = commands.add_parser("update")
    update.add_argument("id", type=int)
    update.add_argument("--name")
    update.add_argument("--price")
    update.add_argument("--stock", type=int)

    delete = commands.add_parser("delete")
    delete.add_argument("id", type=int)

    search = commands.add_parser("search")
    search.add_argument("name")

    barcode = commands.add_parser("barcode")
    barcode.add_argument("code")

    import_item = commands.add_parser("import")
    import_item.add_argument("barcode")
    import_item.add_argument("--price", required=True)
    import_item.add_argument("--stock", type=int, required=True)
    import_item.add_argument("--name")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = None

    if args.command == "list":
        method, path = "GET", "/inventory"
    elif args.command == "show":
        method, path = "GET", f"/inventory/{args.id}"
    elif args.command == "add":
        method, path = "POST", "/inventory"
        payload = {
            "product_name": args.name,
            "price": args.price,
            "stock": args.stock,
        }
        for argument, field in (
            ("barcode", "barcode"),
            ("brands", "brands"),
            ("ingredients", "ingredients_text"),
        ):
            value = getattr(args, argument)
            if value is not None:
                payload[field] = value
    elif args.command == "update":
        method, path = "PATCH", f"/inventory/{args.id}"
        payload = {}
        for argument, field in (
            ("name", "product_name"),
            ("price", "price"),
            ("stock", "stock"),
        ):
            value = getattr(args, argument)
            if value is not None:
                payload[field] = value
        if not payload:
            parser.error("Provide --name, --price, or --stock.")
    elif args.command == "delete":
        method, path = "DELETE", f"/inventory/{args.id}"
    elif args.command == "search":
        method, path = "GET", "/products/search"
    elif args.command == "barcode":
        method, path = "GET", f"/products/barcode/{args.code}"
    else:
        method, path = "POST", "/inventory/import"
        payload = {
            "barcode": args.barcode,
            "price": args.price,
            "stock": args.stock,
        }
        if args.name is not None:
            payload["product_name"] = args.name

    params = {"name": args.name} if args.command == "search" else None

    try:
        response = requests.request(
            method,
            f"{args.base_url.rstrip('/')}{path}",
            json=payload,
            params=params,
            timeout=20,
        )
    except requests.RequestException as error:
        print(f"Unable to reach inventory API: {error}", file=sys.stderr)
        return 1

    if response.status_code == 204:
        print("Item deleted.")
        return 0

    try:
        result = response.json()
    except ValueError:
        print("Inventory API returned invalid JSON.", file=sys.stderr)
        return 1

    if not 200 <= response.status_code < 300:
        print(
            f"Request failed ({response.status_code}): "
            f"{json.dumps(result)}",
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())