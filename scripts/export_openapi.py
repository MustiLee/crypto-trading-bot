#!/usr/bin/env python3
"""
Export FastAPI OpenAPI schema to a JSON file for TypeScript type generation.

Usage:
  python scripts/export_openapi.py [--out openapi/openapi.json]

Notes:
  - This imports the FastAPI app via TradingDashboardServer but does not start the server.
  - No network calls are made during schema generation.
"""

import argparse
import json
from pathlib import Path

from src.realtime.web_server import TradingDashboardServer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default="openapi/openapi.json",
        help="Output path for the OpenAPI JSON",
    )
    args = parser.parse_args()

    # Initialize app (no network operations here)
    server = TradingDashboardServer()
    app = server.app

    schema = app.openapi()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")

    print(f"✅ OpenAPI schema exported to {out_path}")


if __name__ == "__main__":
    main()

