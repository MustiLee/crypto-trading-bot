#!/usr/bin/env bash
set -euo pipefail

# Generate TypeScript types from the exported OpenAPI schema.
# Requires `openapi-typescript` to be available (via npx or local install).

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OPENAPI_JSON="$ROOT_DIR/openapi/openapi.json"
OUT_D_TS="$ROOT_DIR/TraderMobile/src/types/api.d.ts"

if [ ! -f "$OPENAPI_JSON" ]; then
  echo "OpenAPI JSON not found at $OPENAPI_JSON. Exporting..."
  python3 "$ROOT_DIR/scripts/export_openapi.py" --out "$OPENAPI_JSON"
fi

echo "Generating TypeScript types to $OUT_D_TS"

if command -v npx >/dev/null 2>&1; then
  npx --yes openapi-typescript "$OPENAPI_JSON" -o "$OUT_D_TS"
else
  echo "npx not found. Please install openapi-typescript (e.g., 'npm i -D openapi-typescript') and re-run."
  exit 1
fi

echo "✅ Type definitions generated: $OUT_D_TS"

