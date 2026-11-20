# analise-vagas-cepat-joinville

## Pipeline 2026 (Python)

As listas de 2026 (PDFs em `pdfs/2026`) são processadas pelo pipeline em
`pipeline/`:

```bash
python3 pipeline/pipeline.py --pdfs pdfs/2026 --out out
```

Ele gera os resumos semanais, o acumulado e o mapa `summaries-2026.json` usado
pelo frontend. Veja `pipeline/README.md` para requisitos, OCR e detalhes.

---

## Análise 2025 (Bun/TypeScript)

To install dependencies:

```bash
bun install
```

To run:

```bash
bun run index.ts
```

This project was created using `bun init` in bun v1.2.9. [Bun](https://bun.sh) is a fast all-in-one JavaScript runtime.
