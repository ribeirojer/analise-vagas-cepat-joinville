#!/usr/bin/env python3
"""
Atualiza o dashboard com as listas mais recentes do CEPAT.

Fluxo:
1. Lê a página oficial de 2026 e descobre os PDFs publicados.
2. Baixa para pdfs/2026 os que ainda não existem (nome AAAA-MM-DD.pdf).
3. Roda o pipeline para regenerar os resumos.
4. Sincroniza os JSONs com o frontend (opcional).

Uso:
    python3 pipeline/update.py
    python3 pipeline/update.py --dry-run
    python3 pipeline/update.py --download-only
    python3 pipeline/update.py --build

O download não sobrescreve arquivos existentes, a menos que --force seja usado.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE_URL = (
    "https://www.joinville.sc.gov.br/publicacoes/"
    "listas-de-vagas-de-emprego-2026/"
)
PDF_DIR = ROOT / "pdfs" / "2026"
OUT_DIR = ROOT / "out"
FRONTEND = ROOT.parent / "frontend-vagas-cepat-joinville"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/135.0 Safari/537.36"
)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def date_from_url(url: str) -> dt.date | None:
    name = url.rsplit("/", 1)[-1].removesuffix(".pdf")
    name = re.sub(r"^Lista-de-[Vv]agas-de-Emprego-", "", name)
    name = re.sub(r"^vagas-divulgacao-CEPAT-", "", name)
    name = re.sub(r"-1$", "", name)
    patterns = [
        r"^(\d{2})(\d{2})(\d{4})$",
        r"^(\d{2})[-.](\d{2})[-.](\d{4})$",
        r"^(\d{2})[-.](\d{2})[-.](\d{2})$",
    ]
    for pattern in patterns:
        match = re.match(pattern, name)
        if not match:
            continue
        day, month, year = match.groups()
        if len(year) == 2:
            year = "20" + year
        try:
            return dt.date(int(year), int(month), int(day))
        except ValueError:
            return None
    return None


def discover_pdfs() -> list[tuple[dt.date, str]]:
    html = fetch(PAGE_URL).decode("utf-8", "ignore")
    urls = set(
        re.findall(
            r"https://www\.joinville\.sc\.gov\.br/wp-content/uploads/2026/"
            r"[^\"']+?\.pdf",
            html,
            re.I,
        )
    )
    found: dict[dt.date, str] = {}
    for url in sorted(urls):
        date = date_from_url(url)
        if not date:
            continue
        # Prefere o arquivo "Lista-de-Vagas" ao "vagas-divulgacao" quando
        # houver os dois para a mesma data.
        if date in found and "vagas-divulgacao" in url:
            continue
        found[date] = url
    return sorted(found.items())


def download(date: dt.date, url: str, force: bool = False) -> bool:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    dest = PDF_DIR / f"{date.isoformat()}.pdf"
    if dest.exists() and not force:
        return False
    print(f"  baixando {date.isoformat()} <- {url.rsplit('/', 1)[-1]}")
    content = fetch(url)
    if len(content) < 10_000 or not content.startswith(b"%PDF"):
        raise RuntimeError(f"Download inválido para {url} ({len(content)} bytes)")
    with tempfile.NamedTemporaryFile(
        dir=PDF_DIR, suffix=".pdf", delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(dest)
    return True


def run_pipeline() -> None:
    print("\nRodando pipeline...")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "pipeline" / "pipeline.py"),
            "--pdfs",
            str(PDF_DIR),
            "--out",
            str(OUT_DIR),
        ],
        check=True,
        cwd=ROOT,
    )


def sync_frontend() -> None:
    script = ROOT / "pipeline" / "sync_frontend.sh"
    if not script.exists() or not FRONTEND.exists():
        return
    print("\nSincronizando frontend...")
    subprocess.run([str(script), str(OUT_DIR), str(FRONTEND)], check=True)


def build_frontend() -> None:
    if not FRONTEND.exists():
        return
    print("\nBuild do frontend...")
    subprocess.run(["npm", "run", "build"], check=True, cwd=FRONTEND)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="só lista o que falta")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--force", action="store_true", help="rebaixa todos")
    parser.add_argument("--no-sync", action="store_true")
    parser.add_argument("--build", action="store_true", help="roda npm run build")
    args = parser.parse_args()

    print("Consultando lista oficial de 2026...")
    items = discover_pdfs()
    if not items:
        print("Nenhum PDF encontrado na página.", file=sys.stderr)
        return 1

    have = {p.stem for p in PDF_DIR.glob("*.pdf")} if PDF_DIR.exists() else set()
    missing = [
        (date, url)
        for date, url in items
        if args.force or date.isoformat() not in have
    ]
    print(f"{len(items)} listas no site; {len(have)} já em {PDF_DIR}")
    if not missing:
        print("Nenhuma lista nova.")
    else:
        print(f"{len(missing)} lista(s) para baixar:")
        for date, _ in missing:
            print(f"  {date.isoformat()}")
        if args.dry_run:
            return 0
        for date, url in missing:
            download(date, url, force=args.force)

    if args.dry_run or args.download_only:
        return 0

    run_pipeline()
    if not args.no_sync:
        sync_frontend()
    if args.build:
        build_frontend()
    print("\nAtualização concluída.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
