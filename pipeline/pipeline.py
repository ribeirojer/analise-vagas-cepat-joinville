#!/usr/bin/env python3
"""
Pipeline de extração das listas de vagas do CEPAT/Joinville.

Lê os PDFs semanais, extrai as linhas (com OCR quando o PDF usa fontes Type 3
sem mapa Unicode) e gera os JSONs consumidos pelo dashboard.

Uso:
    python3 pipeline/pipeline.py --pdfs pdfs/2026 --out out

Requisitos:
    - PyMuPDF (pip install pymupdf)
    - Pillow (pip install pillow)
    - Tesseract (opcional; só é usado nos PDFs Type 3/escaneados).
      O script procura em .tools/tesseract/usr/bin/tesseract, no PATH ou em
      TESSERACT_BIN.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import glob
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from unicodedata import normalize

import numpy as np
import pymupdf

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TESS = ROOT / ".tools" / "tesseract"
DPI = 300
SCALE = 72 / DPI

# ---------------------------------------------------------------------------
# Normalização / domínio
# ---------------------------------------------------------------------------

# Bairros de Joinville. Valores fora desta lista viram "Outros".
NEIGHBORHOODS = [
    "Adhemar Garcia",
    "América",
    "Anita Garibaldi",
    "Atiradores",
    "Aventureiro",
    "Boa Vista",
    "Boehmerwald",
    "Bom Retiro",
    "Bucarein",
    "Centro",
    "Comasa",
    "Costa e Silva",
    "Espinheiros",
    "Fátima",
    "Floresta",
    "Glória",
    "Iririú",
    "Itaum",
    "Itinga",
    "Jardim Sofia",
    "Jarivatuba",
    "João Costa",
    "Nova Brasília",
    "Pirabeiraba",
    "Rio Bonito",
    "Saguaçu",
    "Santa Catarina",
    "Santo Antônio",
    "São Marcos",
    "Vila Cubatão",
    "Vila Nova",
    "Zona Industrial Norte",
]

EDUCATION = [
    "Fundamental Completo",
    "Fundamental Incompleto",
    "Ensino Médio Completo",
    "Ensino Médio Incompleto",
    "Superior Completo",
    "Superior Incompleto",
    "Curso Técnico",
    "Curso Técnico/Superior Completo",
    "Curso Técnico/Superior Incompleto",
    "Não exigida",
]

BAIRRO_SPECIAL = {
    "zona industrial norte": "Zona Industrial Norte",
    "zona neustrial": "Zona Industrial Norte",
    "zona neutral": "Zona Industrial Norte",
    "zona ndustrial": "Zona Industrial Norte",
    "industrial norte": "Zona Industrial Norte",
    "zona industrial": "Zona Industrial Norte",
    "costa silva e": "Costa e Silva",
    "costa e silva": "Costa e Silva",
    "iririu": "Iririú",
    "jardim iririu": "Iririú",
    "itaum": "Itaum",
    "taum": "Itaum",
    "nova brasilia": "Nova Brasília",
    "gloria": "Glória",
    "goria": "Glória",
    "sao marcos": "São Marcos",
    "santo antonio": "Santo Antônio",
    "paranaguamiri": "Paranaguamirim",
    "paranaguamirin": "Paranaguamirim",
    "paranagua mirim": "Paranaguamirim",
    "jardim paraiso": "Jardim Paraíso",
    "parque guarani": "Parque Guarani",
    "morro do meio": "Morro do Meio",
    "jardim sofia": "Jardim Sofia",
    "joao costa": "João Costa",
    "vila cubatao": "Vila Cubatão",
    "vila nova": "Vila Nova",
    "boa vista": "Boa Vista",
    "bom retiro": "Bom Retiro",
    "adhemar garcia": "Adhemar Garcia",
    "anita garibaldi": "Anita Garibaldi",
    "boehmerwald": "Boehmerwald",
    "bucarein": "Bucarein",
    "comasa": "Comasa",
    "espinheiros": "Espinheiros",
    "fatima": "Fátima",
    "floresta": "Floresta",
    "guanabara": "Guanabara",
    "itinga": "Itinga",
    "jarivatuba": "Jarivatuba",
    "petropolis": "Petrópolis",
    "pirabeiraba": "Pirabeiraba",
    "profipo": "Profipo",
    "rio bonito": "Rio Bonito",
    "saguacu": "Saguaçu",
    "santa catarina": "Santa Catarina",
    "centro": "Centro",
    "america": "América",
    "aventureiro": "Aventureiro",
    "atiradores": "Atiradores",
}

# Locais que não são bairros de Joinville (ou não têm bairro definido).
OUTROS = {
    "local nao fixo",
    "local nao informado",
    "nao informado",
    "a definir",
    "indefinido",
    "bairro",
    "joinville",
    "joinville e regiao",
    "joinville ou balneario camboriu",
    "estado de santa catarina",
    "stado de santa catarina",
    "serra dona franci",
    "serra dona francisca",
    "dona francisca",
    "araquari",
    "balneario picarras",
    "bombinhas",
    "garuva",
    "barra velha",
    "itajai",
    "sao francisco do sul",
}

EDU_SPECIAL = {
    "nao exigida": "Não exigida",
    "nao a exigida ne": "Não exigida",
    "nao x exigida o": "Não exigida",
    "ensino fundamental": "Fundamental Completo",
    "ensino fundamental completo": "Fundamental Completo",
    "ensino fundamental incompleto": "Fundamental Incompleto",
    "fundamental": "Fundamental Completo",
    "fundamental proprio": "Fundamental Completo",
    "fundamental ompleto": "Fundamental Completo",
    "fundmental completo": "Fundamental Completo",
    "fundmental c": "Fundamental Completo",
    "fundamntal incompleto": "Fundamental Incompleto",
    "compeio": "Fundamental Completo",
    "omleto": "Fundamental Completo",
    "erpleto": "Ensino Médio Completo",
    "erpleto a": "Ensino Médio Completo",
    "ensino medio": "Ensino Médio Completo",
    "ensino medio completa": "Ensino Médio Completo",
    "ensino medio completo ou cursando": "Ensino Médio Completo",
    "estudando no ensino medio ou completado": "Ensino Médio Incompleto",
    "estudando ou completo": "Ensino Médio Incompleto",
    "estudando ou completa": "Ensino Médio Incompleto",
    "insno medio ncompleto": "Ensino Médio Incompleto",
    "curso superior": "Superior Completo",
    "superior vo incompleto": "Superior Incompleto",
    "curso tecnico ou superior completo": "Curso Técnico/Superior Completo",
    "curso tecnico ou superior incompleto": "Curso Técnico/Superior Incompleto",
    "curso tecnico incompleto ou superior incompleto": "Curso Técnico/Superior Incompleto",
    "curso tecnico incompleto/superior incompleto": "Curso Técnico/Superior Incompleto",
    "tecnico ou sup incompleto": "Curso Técnico/Superior Incompleto",
    "curso tecnico incompleto": "Curso Técnico",
    "curso tecnico": "Curso Técnico",
    "curso tecnico ar": "Curso Técnico",
    "curso tecnico us": "Curso Técnico",
    "curso tecnico superior completo": "Curso Técnico/Superior Completo",
    "curso tecnico superior incompleto": "Curso Técnico/Superior Incompleto",
}


def fold(s: str) -> str:
    """Remove acentos e normaliza para comparação."""
    return normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", fold(s))).strip()


def similar(raw: str, options: list[str], cutoff: float = 0.62) -> str | None:
    r = clean(raw)
    if not r:
        return None
    rkey = " ".join(sorted(r.split()))
    best, score = None, 0.0
    for opt in options:
        c = clean(opt)
        ckey = " ".join(sorted(c.split()))
        s = SequenceMatcher(None, r, c).ratio()
        if len(r) >= 4 and len(c) >= 4 and (c in r or r in c):
            s = max(s, 0.9)
        if rkey == ckey:
            s = 1.0
        if s > score:
            best, score = opt, s
    return best if score >= cutoff else None


def normalize_bairro(raw: str) -> str:
    r = clean(raw)
    if not r or r in OUTROS:
        return "Outros"
    if r in BAIRRO_SPECIAL:
        return BAIRRO_SPECIAL[r]
    if r.startswith("zona ") and (
        "industrial" in r or "nq" in r or "ndustrial" in r
        or "neutral" in r or "neutra" in r
    ):
        return "Zona Industrial Norte"
    found = similar(r, NEIGHBORHOODS)
    return found or "Outros"


def normalize_education(raw: str) -> str | None:
    r = clean(raw)
    if not r:
        return None
    if r in EDU_SPECIAL:
        return EDU_SPECIAL[r]
    return similar(r, EDUCATION)


def parse_salary(raw: str | None) -> float | None:
    if not raw:
        return None
    s = str(raw)
    if "informado" in fold(s) or "infomado" in fold(s):
        return None
    low = s.lower()
    hourly = "/h" in low or "hora" in low
    daily = "/dia" in low or "por dia" in low
    numstr = re.sub(r"[^\d,.]", "", low)
    if not numstr:
        return None
    if re.fullmatch(r"\d{1,3}\.\d{5}", numstr):
        # Ex.: "2.11200" (OCR juntou milhar + centavos sem vírgula).
        numstr = numstr.replace(".", "")
    elif "," in numstr:
        numstr = numstr.replace(".", "").replace(",", ".")
    elif "." in numstr:
        parts = numstr.split(".")
        if len(parts[-1]) == 3:
            numstr = numstr.replace(".", "")
    try:
        value = float(numstr)
    except ValueError:
        return None
    if "," not in numstr and "." not in numstr and value > 20000:
        value /= 100
    if hourly or (value < 60 and not daily):
        value *= 198
    elif daily:
        value *= 22
    return round(value, 2)


def brl(value: float) -> str:
    """Formata como R$ 1.234,56 (com espaço não separável, igual ao dashboard)."""
    txt = f"{value:,.2f}"
    txt = txt.replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$\u00a0" + txt


def quantile(sorted_values: list[float], p: float) -> float:
    """Percentil usado no resumo geral (mesma convenção dos JSONs antigos)."""
    return sorted_values[math.floor(len(sorted_values) * p)]


def quantile_linear(sorted_values: list[float], p: float) -> float:
    """Percentil com interpolação linear (usado nos grupos de escolaridade)."""
    n = len(sorted_values)
    h = (n - 1) * p
    lo = math.floor(h)
    hi = math.ceil(h)
    return sorted_values[lo] + (h - lo) * (sorted_values[hi] - sorted_values[lo])


def num(value: float):
    """Mantém inteiros como int no JSON (cosmético)."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------


class Ocr:
    def __init__(self, explicit: str | None = None):
        self.bin = self._find(explicit)
        self.env = dict(os.environ)
        if self.bin:
            # .tools/tesseract/usr/bin/tesseract -> .tools/tesseract
            prefix = Path(self.bin).resolve().parents[2]
            lib = prefix / "usr" / "lib" / "x86_64-linux-gnu"
            data = prefix / "usr" / "share" / "tesseract-ocr" / "5" / "tessdata"
            if lib.exists():
                self.env["LD_LIBRARY_PATH"] = str(lib) + (
                    ":" + self.env["LD_LIBRARY_PATH"]
                    if self.env.get("LD_LIBRARY_PATH")
                    else ""
                )
            if data.exists():
                self.env["TESSDATA_PREFIX"] = str(data)

    @staticmethod
    def _find(explicit: str | None) -> str | None:
        candidates = [
            explicit,
            os.environ.get("TESSERACT_BIN"),
            str(DEFAULT_TESS / "usr" / "bin" / "tesseract"),
            shutil.which("tesseract"),
        ]
        for c in candidates:
            if c and Path(c).exists():
                return str(c)
        return None

    def run(
        self,
        image: bytes,
        psm: int = 4,
        whitelist: str | None = None,
        tsv: bool = False,
    ) -> str:
        if not self.bin:
            raise RuntimeError(
                "Tesseract não encontrado. Rode scripts/setup_tesseract.sh ou "
                "instale tesseract-ocr e tesseract-ocr-por."
            )
        cmd = [self.bin, "stdin", "stdout", "-l", "por", "--psm", str(psm)]
        if whitelist:
            cmd += ["-c", f"tessedit_char_whitelist={whitelist}"]
        if tsv:
            cmd.append("tsv")
        proc = subprocess.run(
            cmd, input=image, capture_output=True, env=self.env, check=False
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", "ignore")[:500])
        return proc.stdout.decode("utf-8", "ignore")


# ---------------------------------------------------------------------------
# Geometria e extração
# ---------------------------------------------------------------------------


def uniq(values: list[float], tol: float = 1.0) -> list[float]:
    out: list[float] = []
    for v in sorted(values):
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def vertical_lines(page: pymupdf.Page) -> list[float]:
    xs: list[float] = []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] == "l":
                a, b = item[1], item[2]
                if abs(a.x - b.x) < 0.8 and abs(a.y - b.y) > 50:
                    xs.append(a.x)
            elif item[0] == "re":
                r = item[1]
                if r.width < 1.5 and r.height > 50:
                    xs.append(r.x0)
    return uniq(xs)


def horizontal_lines(page: pymupdf.Page) -> list[float]:
    ys: list[float] = []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] == "l":
                a, b = item[1], item[2]
                if abs(a.y - b.y) < 0.8 and abs(a.x - b.x) > 100:
                    ys.append(a.y)
            elif item[0] == "re":
                r = item[1]
                if r.height < 1.5 and r.width > 100:
                    ys.append(r.y0)
    return uniq(ys)


def _group_pixels(indices: np.ndarray, gap: int = 3) -> list[int]:
    if len(indices) == 0:
        return []
    groups = [[int(indices[0])]]
    for idx in indices[1:]:
        if int(idx) - groups[-1][-1] <= gap:
            groups[-1].append(int(idx))
        else:
            groups.append([int(idx)])
    return [sum(g) // len(g) for g in groups]


def image_geometry(
    page: pymupdf.Page, dpi: int = 220, top_pt: float | None = None
) -> tuple[list[float], list[float]]:
    """Detecta linhas de tabela em PDFs escaneados (sem vetores)."""
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    dark = arr < 160
    h, w = dark.shape
    top = int((top_pt + 10) * dpi / 72) if top_pt is not None else int(h * 0.08)
    top = max(0, min(top, int(h * 0.5)))
    bottom = int(h * 0.97)
    region = dark[top:bottom, :]
    col_counts = region.sum(axis=0)
    xs_px = _group_pixels(np.where(col_counts > 0.55 * region.shape[0])[0])
    if len(xs_px) < 2:
        # Tenta um limiar mais baixo para tabelas curtas.
        xs_px = _group_pixels(np.where(col_counts > 0.25 * region.shape[0])[0])
        if len(xs_px) > 12:
            # Mantém as colunas com maior cobertura (as linhas da tabela).
            scores = [(int(col_counts[x]), x) for x in xs_px]
            keep = sorted(sorted(scores, reverse=True)[:10], key=lambda s: s[1])
            xs_px = [x for _, x in keep]
    if len(xs_px) < 2:
        return [], []
    x0, x1 = xs_px[0], xs_px[-1]
    row_counts = dark[:, x0:x1 + 1].sum(axis=1)
    ys_px = _group_pixels(np.where(row_counts > 0.45 * (x1 - x0 + 1))[0])
    return (
        [x * 72 / dpi for x in xs_px],
        [y * 72 / dpi for y in ys_px],
    )


def geometry(page: pymupdf.Page) -> tuple[list[float], list[float]]:
    xs = vertical_lines(page)
    ys = horizontal_lines(page)
    if len(xs) >= 2 and len(ys) >= 2:
        return xs, ys
    bar = image_header_bar(page)
    ix, iy = image_geometry(page, top_pt=bar[1] if bar else None)
    return (ix or xs), (iy or ys)


def image_header_bar(page: pymupdf.Page, dpi: int = 150) -> tuple[str, float] | None:
    """Detecta a barra azul/verde do título em páginas escaneadas."""
    pix = page.get_pixmap(dpi=dpi)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    rgb = arr[:, :, :3].astype(float)
    h, w, _ = rgb.shape
    top, bottom = int(h * 0.10), int(h * 0.32)
    band = rgb[top:bottom, int(w * 0.05):int(w * 0.95), :]
    blue = (band[:, :, 2] > 120) & (band[:, :, 2] > band[:, :, 0] * 1.5) & (
        band[:, :, 2] > band[:, :, 1] * 1.2
    )
    green = (band[:, :, 1] > 80) & (band[:, :, 1] > band[:, :, 0] * 1.4) & (
        band[:, :, 1] > band[:, :, 2] * 1.2
    )
    for mask, kind in ((green, "pcd"), (blue, "main")):
        rows = np.where(mask.sum(axis=1) > band.shape[1] * 0.5)[0]
        if len(rows):
            return kind, (top + int(rows[0])) * 72 / dpi
    return None


def page_needs_ocr(page: pymupdf.Page) -> bool:
    fonts = page.get_fonts(full=True)
    if any(f[2] == "Type3" for f in fonts):
        return True
    if not fonts and not page.get_text("text").strip():
        return True
    return False


def page_words(
    page: pymupdf.Page, ocr: Ocr | None, cache_file: Path | None = None
) -> list[tuple[float, float, float, float, str]]:
    if page_needs_ocr(page):
        if ocr is None:
            raise RuntimeError("PDF precisa de OCR, mas o Tesseract não foi encontrado.")
        if cache_file and cache_file.exists() and cache_file.stat().st_size > 100:
            words = []
            with cache_file.open() as fh:
                for row in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
                    if len(row) < 12 or row[0] != "5" or not row[11].strip():
                        continue
                    try:
                        conf = float(row[10])
                    except ValueError:
                        continue
                    if conf < 0:
                        continue
                    x0 = float(row[6]) * SCALE
                    y0 = float(row[7]) * SCALE
                    x1 = (float(row[6]) + float(row[8])) * SCALE
                    y1 = (float(row[7]) + float(row[9])) * SCALE
                    words.append((x0, y0, x1, y1, row[11]))
            return words
        image = page.get_pixmap(dpi=DPI).tobytes("png")
        text = ocr.run(image, psm=4, tsv=True)
        if cache_file:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(text)
        words = []
        reader = csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
        for r in reader:
            if r.get("level") != "5" or not r.get("text", "").strip():
                continue
            try:
                conf = float(r.get("conf", "-1"))
            except ValueError:
                continue
            if conf < 0:
                continue
            x0 = float(r["left"]) * SCALE
            y0 = float(r["top"]) * SCALE
            x1 = (float(r["left"]) + float(r["width"])) * SCALE
            y1 = (float(r["top"]) + float(r["height"])) * SCALE
            words.append((x0, y0, x1, y1, r["text"]))
        return words
    return [tuple(w[:5]) for w in page.get_text("words")]


def header_bar(page: pymupdf.Page) -> tuple[str, float] | None:
    """Detecta a barra colorida do título: azul (main/JA) ou verde (PCD)."""
    for drawing in page.get_drawings():
        fill = drawing.get("fill")
        rect = drawing.get("rect")
        if not fill or not rect:
            continue
        if rect.width < 300 or not (8 < rect.height < 50) or rect.y0 > 300:
            continue
        r, g, b = fill[:3]
        if g > 0.4 and g > r * 1.5 and g > b * 1.5:
            return "pcd", rect.y0
        if b > 0.5 and b > r * 1.5 and b > g * 1.2:
            return "main", rect.y0
    return image_header_bar(page)


def is_ja_title(words: list[tuple[float, float, float, float, str]]) -> bool:
    for w in words:
        if "APRENDIZ" not in fold(w[4]).upper() or w[1] > 320:
            continue
        for v in words:
            if "VAGAS" not in fold(v[4]).upper():
                continue
            if abs(v[1] - w[1]) < 8 and abs(v[0] - w[0]) < 260:
                return True
    return False


def find_header(
    page: pymupdf.Page,
    words: list[tuple[float, float, float, float, str]],
    ncols: int,
) -> tuple[str, float] | None:
    """Retorna (seção, y do título) para títulos de PCD/JA na página."""
    bar = header_bar(page)
    if bar:
        section, y = bar
        if section == "pcd":
            return "pcd", y
        if ncols == 7 or is_ja_title(words):
            return "ja", y
        return "main", y

    # Fallback (PDFs escaneados ou sem barra vetorial):
    page_text = fold(" ".join(w[4] for w in words))
    pcd = [w for w in words if "PCD" in w[4].upper()]
    if not pcd and ("exclusivas" in page_text or "vagas em aberto" in page_text):
        pcd = [w for w in words if "DEFICI" in fold(w[4]).upper()]
    if pcd:
        return "pcd", min(w[1] for w in pcd)
    if is_ja_title(words):
        for w in words:
            if "APRENDIZ" in fold(w[4]).upper():
                return "ja", w[1]
    return None


def build_bands(
    words: list[tuple[float, float, float, float, str]],
    xs: list[float],
    ys: list[float],
) -> list[tuple[int, list[str]]]:
    cells: dict[tuple[int, int], list[tuple[float, float, str]]] = defaultdict(list)
    for x0, y0, x1, y1, text in words:
        if re.fullmatch(r"[|\-–—_.]+", text):
            continue
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ci = next((i for i in range(len(xs) - 1) if xs[i] <= cx < xs[i + 1]), None)
        ri = next((i for i in range(len(ys) - 1) if ys[i] <= cy < ys[i + 1]), None)
        if ci is None or ri is None:
            continue
        cells[(ri, ci)].append((x0, y0, text))
    out = []
    for ri in sorted({k[0] for k in cells}):
        row = []
        for ci in range(len(xs) - 1):
            ws = cells.get((ri, ci), [])
            ws.sort(key=lambda a: (round(a[1] / 4), a[0]))
            row.append(" ".join(w[2] for w in ws).strip())
        out.append((ri, row))
    return out


def ocr_column_numbers(
    page: pymupdf.Page,
    xs: list[float],
    ys: list[float],
    ci: int,
    ocr: Ocr,
    dpi: int = DPI,
) -> dict[int, int]:
    """Lê uma coluna numérica inteira (ex.: vagas) e mapeia por faixa."""
    if ocr is None or ci < 0 or ci + 1 >= len(xs) or len(ys) < 2:
        return {}
    x0, x1 = xs[ci] + 1, xs[ci + 1] - 1
    y0, y1 = ys[0] + 1, ys[-1] - 1
    if x1 - x0 < 1 or y1 - y0 < 1:
        return {}
    pix = page.get_pixmap(dpi=dpi, clip=pymupdf.Rect(x0, y0, x1, y1))
    text = ocr.run(
        pix.tobytes("png"), psm=6, whitelist="0123456789", tsv=True
    )
    grouped: dict[int, list[str]] = defaultdict(list)
    reader = csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
    for r in reader:
        if r.get("level") != "5" or not r.get("text", "").strip():
            continue
        try:
            conf = float(r.get("conf", "-1"))
        except ValueError:
            continue
        if conf < 0:
            continue
        y = y0 + (
            float(r["top"]) + float(r["height"]) / 2
        ) * SCALE
        ri = next((i for i in range(len(ys) - 1) if ys[i] <= y < ys[i + 1]), None)
        if ri is not None:
            grouped[ri].append(r["text"].strip())
    out = {}
    for ri, parts in grouped.items():
        digits = re.sub(r"\D", "", "".join(parts))
        if digits:
            out[ri] = int(digits)
    return out


def recover_cell(
    page: pymupdf.Page,
    xs: list[float],
    ys: list[float],
    ri: int,
    ci: int,
    ocr: Ocr,
    whitelist: str,
) -> str:
    if not ocr or ci + 1 >= len(xs) or ri + 1 >= len(ys):
        return ""
    x0, x1 = xs[ci] + 2, xs[ci + 1] - 2
    y0, y1 = ys[ri] + 2, ys[ri + 1] - 2
    if x1 - x0 < 1 or y1 - y0 < 1:
        return ""
    pix = page.get_pixmap(dpi=DPI, clip=pymupdf.Rect(x0, y0, x1, y1))
    image = pix.tobytes("png")
    text = ocr.run(image, psm=7, whitelist=whitelist).strip()
    return re.sub(r"\s+", "", text)


@dataclasses.dataclass
class Row:
    date: str
    page: int
    section: str
    code: str
    cbo: str
    name: str
    vagas: int
    vagas_raw: str
    education_raw: str
    salary_raw: str
    bairro_raw: str
    education: str | None = None
    salary: float | None = None
    bairro: str = "Outros"
    ja_name: bool = False


def parse_pdf(
    pdf_path: Path,
    ocr: Ocr | None,
    cache_dir: Path,
    date_label: str,
) -> tuple[list[Row], dict]:
    doc = pymupdf.open(pdf_path)
    rows: list[Row] = []
    report = {"file": pdf_path.name, "pages": doc.page_count, "warnings": []}
    section = "main"
    page_cache = cache_dir / pdf_path.stem

    for pno, page in enumerate(doc, start=1):
        xs, ys = geometry(page)
        words = page_words(page, ocr, page_cache / f"p{pno}.tsv")

        if len(xs) < 2 or len(ys) < 2:
            report["warnings"].append(
                f"p{pno}: sem geometria de tabela (xs={len(xs)}, ys={len(ys)})"
            )
            continue

        ncols = len(xs) - 1
        prev_section = section
        header = find_header(page, words, ncols)
        header_y = header[1] if header else None
        if header:
            section = header[0]

        if ncols == 7:
            # JA clássico: código, CBO, idade, nome, vagas, escolaridade, bairro
            colmap = {
                "code": 0,
                "cbo": 1,
                "age": 2,
                "name": 3,
                "vagas": 4,
                "education": 5,
                "bairro": 6,
            }
        elif ncols >= 8:
            # Layout padrão: código, CBO, nome, vagas, escolaridade, exp,
            # salário, bairro. (JA com 8 colunas usa o mesmo layout.)
            colmap = {
                "code": 0,
                "cbo": 1,
                "name": 2,
                "vagas": 3,
                "education": 4,
                "exp": 5,
                "salary": 6,
                "bairro": 7,
            }
        else:
            report["warnings"].append(f"p{pno}: layout com {ncols} colunas")
            continue

        is_scanned = not page.get_drawings()
        col_vagas = {}
        if page_needs_ocr(page) and ocr and not is_scanned:
            col_vagas = ocr_column_numbers(
                page, xs, ys, colmap["vagas"], ocr
            )

        for ri, cells in build_bands(words, xs, ys):
            if len(cells) <= max(colmap.values()):
                continue
            row_section = section
            if header_y is not None and ys[ri] < header_y - 1:
                row_section = prev_section
            joined = fold(" ".join(cells))
            if any(
                bad in joined
                for bad in (
                    "total de vagas",
                    "total geral",
                    "codigo cbo",
                    "nome da vaga",
                    "vagas disponiveis",
                    "vagas em aberto",
                    "exclusivas para pessoas",
                )
            ):
                continue

            def cell(key: str) -> str:
                idx = colmap.get(key)
                return cells[idx] if idx is not None else ""

            code = cell("code")
            digits = re.sub(r"\D", "", code)
            vagas_raw = cell("vagas")
            vmatch = re.search(r"\d+", vagas_raw)
            vagas = int(vmatch.group()) if vmatch else 0

            # Em PDFs escaneados a coluna inteira costuma desalinhar; nesse
            # caso lê cada célula de vagas individualmente.
            if is_scanned and ocr:
                cell_vagas = recover_cell(
                    page, xs, ys, ri, colmap["vagas"], ocr, "0123456789"
                )
                if cell_vagas.isdigit():
                    vagas = int(cell_vagas)
                    vagas_raw = cell_vagas

            # Nos PDFs vetoriais, a leitura da coluna inteira costuma ser mais
            # confiável que a leitura da célula isolada. Em caso de
            # divergência, confirma na célula.
            ocr_vagas = col_vagas.get(ri)
            if ocr_vagas is not None:
                if vagas and ocr_vagas != vagas:
                    cell_vagas = recover_cell(
                        page, xs, ys, ri, colmap["vagas"], ocr, "0123456789"
                    )
                    if cell_vagas.isdigit():
                        vagas = int(cell_vagas)
                    else:
                        vagas = ocr_vagas
                else:
                    vagas = ocr_vagas
                vagas_raw = str(vagas)
            elif vagas == 0 and page_needs_ocr(page) and ocr:
                recovered = recover_cell(
                    page, xs, ys, ri, colmap["vagas"], ocr, "0123456789"
                )
                if recovered.isdigit():
                    vagas = int(recovered)
                    vagas_raw = recovered

            if len(digits) < 5 and page_needs_ocr(page) and ocr:
                recovered_code = recover_cell(
                    page, xs, ys, ri, colmap["code"], ocr, "0123456789"
                )
                if len(recovered_code) >= 5:
                    code = recovered_code
                    digits = recovered_code
            if len(digits) < 5:
                if (
                    (vagas or cells[colmap["education"]])
                    and not any(
                        noise in joined
                        for noise in (
                            "joinville",
                            "interessados",
                            "cepat",
                            "atendimento",
                            "prefeitura",
                        )
                    )
                ):
                    report["warnings"].append(
                        f"p{pno}: linha sem código ignorada ({cells[:3]})"
                    )
                continue

            name = cell("name")
            education_raw = cell("education")
            salary_raw = cell("salary")
            bairro_raw = cell("bairro")
            row = Row(
                date=date_label,
                page=pno,
                section=row_section,
                code=code,
                cbo=cell("cbo"),
                name=name,
                vagas=vagas,
                vagas_raw=vagas_raw,
                education_raw=education_raw,
                salary_raw=salary_raw,
                bairro_raw=bairro_raw,
                bairro=normalize_bairro(bairro_raw),
                ja_name="jovem" in fold(name),
            )
            row.salary = parse_salary(salary_raw) if salary_raw else None
            row.education = normalize_education(education_raw)
            rows.append(row)

    # Totais declarados no PDF (para conferência)
    text = "\n".join(page.get_text() for page in doc)
    if any(page_needs_ocr(page) for page in doc) and ocr:
        text = "\n".join(
            " ".join(w[4] for w in page_words(page, ocr, page_cache / f"p{p}.tsv"))
            for p, page in enumerate(doc, start=1)
        )
    footer = {}
    flat = fold(text).upper()

    def number(s: str) -> int:
        return int(re.sub(r"\D", "", s))

    # O primeiro "TOTAL DE VAGAS:" é o da lista principal; se houver um
    # segundo, é o total da seção de Jovem Aprendiz.
    main_totals = re.findall(r"TOTAL DE VAGAS:\s*([\d.]+)", flat, re.I)
    if main_totals:
        footer["main_total"] = number(main_totals[0])
        if len(main_totals) > 1:
            footer["ja_total"] = number(main_totals[-1])

    for label, pattern in (
        ("pcd_total", r"TOTAL GERAL DE VAGAS EXCLUSIVAS PCD\s*([\d.]+)"),
        ("ja_total", r"TOTAL DE VAGAS JOVEM APRENDIZ\s*([\d.]+)"),
        ("overall_total", r"TOTAL GERAL DE VAGAS:\s*([\d.]+)"),
    ):
        found = re.findall(pattern, flat, re.I)
        if found:
            footer[label] = number(found[-1])
    report["footer"] = footer
    return rows, report


# ---------------------------------------------------------------------------
# Estatísticas / saída
# ---------------------------------------------------------------------------


def salary_block(values: list[float], total_anuncios: int) -> dict:
    if not values:
        return {
            "totalWithSalary": 0,
            "pctWithSalary": 0,
            "min": 0,
            "max": 0,
            "avg": 0,
            "median": 0,
            "q1": 0,
            "q3": 0,
            "iqr": 0,
            "stdDev": 0,
            "dynamicRanges": {"ranges": []},
            "medianCenteredRanges": {"ranges": []},
            "quartileRanges": {"ranges": []},
            "topSalaries": [],
            "outliers": {"low": [], "high": [], "extreme": []},
        }

    vals = sorted(values)
    n = len(vals)
    q1 = quantile(vals, 0.25)
    median = quantile(vals, 0.5)
    q3 = quantile(vals, 0.75)
    iqr = q3 - q1
    avg = sum(vals) / n
    std = math.sqrt(sum((v - avg) ** 2 for v in vals) / n)
    original_order = list(values)

    # Faixas dinâmicas: 5 faixas + acima da última
    span = vals[-1] - vals[0]
    step = math.ceil(span / 6) if span > 0 else 1
    dynamic = []
    for i in range(5):
        a = vals[0] + i * step
        b = a + step - 1
        count = sum(1 for v in vals if a <= v <= b)
        dynamic.append(
            {
                "label": f"{brl(a)} – {brl(b)}",
                "count": count,
                "pct": num(round(count / n * 100, 2)),
            }
        )
    limit = vals[0] + 5 * step
    count = sum(1 for v in vals if v > limit)
    dynamic.append(
        {
            "label": f"Acima de {brl(limit)}",
            "count": count,
            "pct": num(round(count / n * 100, 2)),
        }
    )

    # Faixas centradas na mediana (passo fixo de R$ 500)
    step_m = 500
    centered = [
        (None, median - step_m, f"Até {brl(median - step_m)}"),
        (median - step_m + 1, median, f"{brl(median - step_m + 1)} – {brl(median)}"),
        (median + 1, median + step_m, f"{brl(median + 1)} – {brl(median + step_m)}"),
        (median + step_m + 1, None, f"Acima de {brl(median + step_m)}"),
    ]
    median_ranges = []
    for a, b, label in centered:
        count = sum(
            1 for v in vals if (a is None or v >= a) and (b is None or v <= b)
        )
        median_ranges.append(
            {"label": label, "count": count, "pct": num(round(count / n * 100, 2))}
        )

    # Faixas por quartis
    quartile = [
        (None, q1, f"Até {brl(q1)} (25%)"),
        (q1, median, f"{brl(q1)} – {brl(median)}"),
        (median, q3, f"{brl(median)} – {brl(q3)}"),
        (q3, None, f"Acima de {brl(q3)}"),
    ]
    quartile_ranges = []
    for a, b, label in quartile:
        count = sum(
            1 for v in vals if (a is None or v > a) and (b is None or v <= b)
        )
        quartile_ranges.append(
            {"label": label, "count": count, "pct": num(round(count / n * 100, 2))}
        )

    top = [
        {
            "salario": num(v),
            "acimaDaMedianaPct": num(round((v / median - 1) * 100, 1)),
        }
        for v in list(reversed(vals))[:10]
    ]

    low_lim = q1 - 1.5 * iqr
    high_lim = q3 + 1.5 * iqr
    extreme_lim = q3 + 3 * iqr
    # Preserva a ordem original das linhas (igual aos JSONs antigos).
    outliers = {
        "low": [num(v) for v in original_order if v < low_lim],
        "high": [num(v) for v in original_order if high_lim < v <= extreme_lim],
        "extreme": [num(v) for v in original_order if v > extreme_lim],
    }

    return {
        "totalWithSalary": n,
        "pctWithSalary": n / total_anuncios * 100 if total_anuncios else 0,
        "min": num(vals[0]),
        "max": num(vals[-1]),
        "avg": avg,
        "median": num(median),
        "q1": num(q1),
        "q3": num(q3),
        "iqr": iqr,
        "stdDev": std,
        "dynamicRanges": {"ranges": dynamic},
        "medianCenteredRanges": {"ranges": median_ranges},
        "quartileRanges": {"ranges": quartile_ranges},
        "topSalaries": top,
        "outliers": outliers,
    }


def grouped_stats(
    pairs: list[tuple[str, float]], with_quartiles: bool
) -> list[dict]:
    groups: dict[str, list[float]] = defaultdict(list)
    for label, value in pairs:
        groups[label].append(value)
    out = []
    for label, values in groups.items():
        values.sort()
        n = len(values)
        if with_quartiles and n < 2:
            # Evita grupos de uma única observação no gráfico de escolaridade.
            continue
        item = {
            "label": label,
            "count": n,
            "min": num(values[0]),
            "max": num(values[-1]),
        }
        if with_quartiles:
            item["q1"] = num(quantile_linear(values, 0.25))
            item["median"] = num(quantile_linear(values, 0.5))
            item["q3"] = num(quantile_linear(values, 0.75))
            item["_sort"] = (item["median"], item["q1"], n)
        else:
            item["avg"] = round(sum(values) / n, 2)
            item["_sort"] = item["avg"]
        out.append(item)

    out.sort(key=lambda d: d["_sort"], reverse=True)
    for item in out:
        item.pop("_sort", None)
    return out


def summarize(rows: list[Row]) -> dict:
    total_anuncios = len(rows)
    total_vagas = sum(r.vagas for r in rows)

    pcd_rows = [r for r in rows if r.section == "pcd"]
    ja_rows = [r for r in rows if r.section == "ja"]
    vagas_pcd = sum(r.vagas for r in pcd_rows)
    if ja_rows:
        vagas_ja = sum(r.vagas for r in ja_rows)
    else:
        # Sem seção dedicada: conta as vagas de Jovem Aprendiz na lista principal.
        vagas_ja = sum(r.vagas for r in rows if r.ja_name)

    by_neighborhood: dict[str, int] = defaultdict(int)
    by_education: dict[str, int] = defaultdict(int)
    for r in rows:
        by_neighborhood[r.bairro] += r.vagas
        # A seção dedicada de Jovem Aprendiz não entra na distribuição por
        # escolaridade (mesma convenção dos JSONs antigos).
        if r.section != "ja" and r.education:
            by_education[r.education] += r.vagas

    salary_rows = [r for r in rows if r.section != "ja" and r.salary is not None]
    salary_values = [r.salary for r in salary_rows]

    neighborhood_pairs = [(r.bairro, r.salary) for r in salary_rows]
    education_pairs = [(r.education, r.salary) for r in salary_rows if r.education]

    return {
        "overviewStats": {
            "totalAnuncios": total_anuncios,
            "totalVagas": total_vagas,
            "mediaVagasPorAnuncio": total_vagas / total_anuncios
            if total_anuncios
            else 0,
            "vagasPCD": vagas_pcd,
            "vagasJovemAprendiz": vagas_ja,
            "distributions": {
                "byNeighborhood": dict(
                    sorted(by_neighborhood.items(), key=lambda kv: -kv[1])
                ),
                "byEducation": dict(
                    sorted(by_education.items(), key=lambda kv: -kv[1])
                ),
            },
        },
        "salaryStats": salary_block(salary_values, total_anuncios),
        "neighborhoodStats": grouped_stats(neighborhood_pairs, False),
        "educationStats": grouped_stats(education_pairs, True),
    }


def occupations_summary(rows: list[Row]) -> list[dict]:
    """Top ocupações (CBO) por vagas, com salário mediano/médio."""
    groups: dict[str, dict] = {}
    for row in rows:
        code = re.sub(r"\D", "", row.cbo or "")
        key = code if code else clean(row.name)[:80]
        if not key:
            continue
        group = groups.setdefault(
            key, {"vagas": 0, "count": 0, "names": {}, "salaries": []}
        )
        group["vagas"] += row.vagas
        group["count"] += 1
        name = " ".join((row.name or "").split())
        if name:
            group["names"][name] = group["names"].get(name, 0) + 1
        if row.section != "ja" and row.salary is not None:
            group["salaries"].append(row.salary)

    out = []
    for key, group in groups.items():
        names = group["names"]
        name = (
            max(names, key=names.get)
            if names
            else (f"CBO {key}" if key.isdigit() else key)
        )
        item = {
            "cbo": key,
            "name": name,
            "vagas": group["vagas"],
            "count": group["count"],
        }
        salaries = sorted(group["salaries"])
        if salaries:
            item["min"] = num(salaries[0])
            item["max"] = num(salaries[-1])
            item["median"] = num(round(quantile_linear(salaries, 0.5), 2))
            item["avg"] = round(sum(salaries) / len(salaries), 2)
        out.append(item)

    out.sort(key=lambda item: (-item["vagas"], -item["count"], item["name"]))
    return out[:20]


def date_label_from_path(path: Path) -> str:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", path.stem)
    if m:
        y, mo, d = m.groups()
        return f"{d}/{mo}/{y}"
    raise ValueError(f"Não consegui extrair a data de {path.name}")


def write_outputs(
    rows_by_date: dict[str, list[Row]],
    reports: list[dict],
    out_dir: Path,
    source: str,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    dates = sorted(rows_by_date, key=lambda d: datetime.strptime(d, "%d/%m/%Y"))
    summaries = {}
    for date in dates:
        summary = summarize(rows_by_date[date])
        summaries[date] = summary
        dd, mm, yyyy = date.split("/")
        filename = f"summary-Lista-de-Vagas-de-Emprego-{dd}{mm}{yyyy}.json"
        (out_dir / filename).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
        )

    all_rows = [r for d in dates for r in rows_by_date[d]]
    all_summary = summarize(all_rows)
    # O total acumulado de Jovem Aprendiz é a soma dos totais semanais:
    # semanas sem seção dedicada contam as linhas com "Jovem Aprendiz" no nome.
    all_summary["overviewStats"]["vagasJovemAprendiz"] = sum(
        summaries[d]["overviewStats"]["vagasJovemAprendiz"] for d in dates
    )
    (out_dir / "summary-all.json").write_text(
        json.dumps(all_summary, ensure_ascii=False, indent=2) + "\n"
    )
    summaries["acumulado"] = all_summary
    (out_dir / "summaries-2026.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2) + "\n"
    )

    occupations = {
        date: occupations_summary(rows_by_date[date]) for date in dates
    }
    occupations["acumulado"] = occupations_summary(all_rows)
    (out_dir / "occupations-2026.json").write_text(
        json.dumps(occupations, ensure_ascii=False, indent=2) + "\n"
    )

    with (out_dir / "vagas-2026.csv").open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "data", "pagina", "secao", "codigo", "cbo", "nome", "vagas",
                "escolaridade_raw", "escolaridade", "salario_raw", "salario",
                "bairro_raw", "bairro",
            ]
        )
        for date in dates:
            for r in rows_by_date[date]:
                writer.writerow(
                    [
                        date, r.page, r.section, r.code, r.cbo, r.name, r.vagas,
                        r.education_raw, r.education or "", r.salary_raw,
                        r.salary if r.salary is not None else "", r.bairro_raw,
                        r.bairro,
                    ]
                )

    # Relatório de conferência: totais do PDF x totais extraídos.
    for rep in reports:
        date = rep.get("date")
        if not date:
            continue
        summary = summaries.get(date)
        if not summary:
            continue
        rep["parsed"] = {
            "anuncios": summary["overviewStats"]["totalAnuncios"],
            "vagas": summary["overviewStats"]["totalVagas"],
            "pcd": summary["overviewStats"]["vagasPCD"],
            "ja": summary["overviewStats"]["vagasJovemAprendiz"],
        }
        footer = rep.get("footer", {})
        diff = {}
        if "overall_total" in footer:
            diff["overall"] = rep["parsed"]["vagas"] - footer["overall_total"]
        if "pcd_total" in footer:
            diff["pcd"] = rep["parsed"]["pcd"] - footer["pcd_total"]
        if "ja_total" in footer:
            diff["ja"] = rep["parsed"]["ja"] - footer["ja_total"]
        rep["diff"] = diff
    (out_dir / "report.json").write_text(
        json.dumps({"source": source, "files": reports}, ensure_ascii=False, indent=2)
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdfs", default="pdfs/2026", help="pasta com os PDFs")
    parser.add_argument("--out", default="out", help="pasta de saída")
    parser.add_argument("--cache", default=".cache/ocr", help="cache do OCR")
    parser.add_argument("--tesseract", default=None, help="caminho do tesseract")
    parser.add_argument(
        "--skip-ocr", action="store_true", help="pula PDFs que precisam de OCR"
    )
    args = parser.parse_args()

    pdfs = sorted(glob.glob(os.path.join(args.pdfs, "*.pdf")))
    if not pdfs:
        print(f"Nenhum PDF em {args.pdfs}", file=sys.stderr)
        return 1

    ocr = Ocr(args.tesseract)
    if ocr.bin:
        print(f"OCR: {ocr.bin}")
    else:
        print("OCR: não encontrado (PDFs Type 3 serão pulados com --skip-ocr)")

    rows_by_date: dict[str, list[Row]] = {}
    reports = []
    for pdf in pdfs:
        path = Path(pdf)
        date = date_label_from_path(path)
        doc = pymupdf.open(path)
        needs = any(page_needs_ocr(page) for page in doc)
        if needs and not ocr.bin:
            msg = f"{path.name}: precisa de OCR e o tesseract não foi encontrado"
            print(msg, file=sys.stderr)
            if args.skip_ocr:
                continue
            return 1
        print(f"Processando {path.name} ({date})...", flush=True)
        rows, report = parse_pdf(path, ocr, Path(args.cache), date)
        report["date"] = date
        rows_by_date[date] = rows
        reports.append(report)
        main = sum(r.vagas for r in rows if r.section == "main")
        pcd = sum(r.vagas for r in rows if r.section == "pcd")
        ja = sum(r.vagas for r in rows if r.section == "ja")
        print(
            f"  {len(rows)} anúncios | {main + pcd + ja} vagas "
            f"(main {main}, pcd {pcd}, ja {ja})"
        )
        if report["warnings"]:
            for w in report["warnings"][:5]:
                print(f"  aviso: {w}")

    write_outputs(rows_by_date, reports, Path(args.out), args.pdfs)
    print(f"\nSaída em {args.out}")
    print(f"  {len(rows_by_date)} semanas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
