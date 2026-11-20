# Pipeline CEPAT 2026

Extrai as listas semanais de vagas do CEPAT (PDFs) e gera os JSONs usados pelo
dashboard.

## O que ele faz

1. Lê cada PDF em `pdfs/2026` (nome no formato `AAAA-MM-DD.pdf`).
2. Usa a camada de texto quando o PDF tem fontes com mapa Unicode.
3. Nos PDFs com fontes Type 3 (jan–abr/2026) ou escaneados (24/08/2026),
   renderiza a página e roda OCR com Tesseract.
4. Identifica as seções:
   - lista principal;
   - `VAGAS DISPONÍVEIS PARA JOVEM APRENDIZ`;
   - `EXCLUSIVAS PARA PESSOAS COM DEFICIÊNCIA (PCD)`.
5. Lê a coluna de vagas duas vezes (tabela + coluna isolada) e confirma na
   célula quando há divergência.
6. Normaliza bairros, escolaridade e salários.
7. Gera um JSON por semana no mesmo formato de `JobAnalysisResult` do
   frontend, mais o acumulado.

## Requisitos

- Python 3.10+
- `pymupdf`, `numpy`
- Tesseract com o idioma `por` (só para os PDFs Type 3/escaneados)

```bash
python3 -m pip install -r pipeline/requirements.txt
```

O script procura o Tesseract em:

1. `--tesseract /caminho/do/tesseract`
2. `TESSERACT_BIN`
3. `.tools/tesseract/usr/bin/tesseract`
4. `tesseract` no `PATH`

Nesta máquina o Tesseract portátil já está em `.tools/tesseract` (ignorado pelo
git). Para recriar em outra máquina Ubuntu:

```bash
mkdir -p .tools/tesseract
cd /tmp
apt-get download tesseract-ocr tesseract-ocr-por libtesseract5 liblept5
for deb in tesseract-ocr_*.deb tesseract-ocr-por_*.deb libtesseract5_*.deb liblept5_*.deb; do
  dpkg-deb -x "$deb" /caminho/para/analise-vagas-cepat-joinville/.tools/tesseract
done
```

Ou instale pelo sistema: `sudo apt install tesseract-ocr tesseract-ocr-por`.

## Uso

```bash
cd analise-vagas-cepat-joinville
python3 pipeline/pipeline.py --pdfs pdfs/2026 --out out
```

Opções:

- `--pdfs`: pasta dos PDFs (padrão `pdfs/2026`)
- `--out`: pasta de saída (padrão `out`)
- `--cache`: cache dos TSVs de OCR (padrão `.cache/ocr`)
- `--tesseract`: caminho do binário
- `--skip-ocr`: pula PDFs que precisam de OCR

## Saídas

Em `out/`:

- `summary-Lista-de-Vagas-de-Emprego-DDMMAAAA.json` — um por semana
- `summary-all.json` — acumulado de todas as semanas
- `summaries-2026.json` — mapa `{ "DD/MM/AAAA": resultado, "acumulado": resultado }`
  pronto para o frontend
- `occupations-2026.json` — top 20 cargos (CBO) por semana e no acumulado,
  com vagas, anúncios e salário mediano/médio
- `rows-2026.json` — dataset compacto por linha, usado pelos filtros
  interativos do frontend (carregado sob demanda)
- `vagas-2026.csv` — todas as linhas extraídas (auditoria)
- `report.json` — totais do PDF x totais extraídos, avisos e diferenças

## PDFs escaneados

O PDF de 24/08/2026 não tem camada de texto nem vetores. Nesse caso o pipeline
detecta as linhas da tabela na imagem renderizada e faz OCR célula a célula na
coluna de vagas. Os demais PDFs Type 3 usam OCR da página inteira + leitura da
coluna de vagas.

Os totais impressos no rodapé de alguns PDFs não batem com a soma das linhas
(ex.: 18/02/2026 e 24/08/2026). O pipeline prioriza as linhas da tabela e
registra a diferença em `report.json`.

## Regras de normalização

- **Salário por hora**: multiplicado por 198 (44h × 4,5 semanas), mesma regra
  dos JSONs antigos.
- **Salário por dia**: multiplicado por 22 (dias úteis).
- **Bairros**: lista fixa de bairros de Joinville usada pelo dashboard; o que
  não está na lista vira `Outros`.
- **Escolaridade**: categorias canônicas do dashboard; a seção dedicada de
  Jovem Aprendiz não entra nas estatísticas por escolaridade (mesma convenção
  dos dados antigos).
- **Vagas PCD**: soma da seção PCD.
- **Vagas Jovem Aprendiz**: soma da seção dedicada; quando não há seção
  dedicada, soma as linhas com “Jovem Aprendiz” no nome.

## Validação

As quatro semanas de janeiro/2026 foram comparadas com os JSONs que já estavam
no frontend e batem exatamente (totais, distribuições, quartis, faixas e
outliers).

## Integração com o frontend

```bash
./pipeline/sync_frontend.sh
```

O script copia os JSONs semanais, o `summary-all.json`, o
`summaries-2026.json` e o `occupations-2026.json` para
`../frontend-vagas-cepat-joinville/data/`, e o `rows-2026.json` para
`../frontend-vagas-cepat-joinville/public/data/`. O `lib/data.ts` do frontend
lê os mapas; os arquivos semanais ficam em `data/` apenas para histórico e o
dataset por linha é buscado sob demanda.
