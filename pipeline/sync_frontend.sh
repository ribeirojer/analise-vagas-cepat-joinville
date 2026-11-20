#!/usr/bin/env bash
# Copia os resultados do pipeline para o projeto do frontend.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
OUT="${1:-$ROOT/out}"
FRONT="${2:-$ROOT/../frontend-vagas-cepat-joinville}"

if [ ! -d "$OUT" ]; then
  echo "Pasta de saída não encontrada: $OUT" >&2
  exit 1
fi
if [ ! -d "$FRONT/data" ]; then
  echo "Pasta data do frontend não encontrada: $FRONT/data" >&2
  exit 1
fi

cp "$OUT"/summary-*.json "$FRONT/data/"
cp "$OUT/summaries-2026.json" "$FRONT/data/"
if [ -f "$OUT/occupations-2026.json" ]; then
  cp "$OUT/occupations-2026.json" "$FRONT/data/"
fi

echo "Dados copiados para $FRONT/data"
