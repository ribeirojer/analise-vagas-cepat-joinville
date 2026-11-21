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
if [ -f "$OUT/segments-2026.json" ]; then
  cp "$OUT/segments-2026.json" "$FRONT/data/"
fi
if [ -f "$OUT/report.json" ]; then
  cp "$OUT/report.json" "$FRONT/data/report-2026.json"
fi
if [ -f "$OUT/rows-2026.json" ]; then
  mkdir -p "$FRONT/public/data"
  cp "$OUT/rows-2026.json" "$FRONT/public/data/rows-2026.json"
fi

echo "Dados copiados para $FRONT/data"
