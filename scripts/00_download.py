
"""CLI wrapper around Step 0 of 00_data_preprocessing_validation.ipynb.

The download logic lives in the notebook (the cell tagged "download"), so there is a
single implementation. This script executes that cell and calls download_all().

    python3 scripts/00_download.py              # everything (~11 GB)
    python3 scripts/00_download.py --only ibge  # only the IBGE meshes

Use ELECTIONS_DATA=/path/to/data to target another location.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "00_data_preprocessing_validation.ipynb"


def load_step0() -> dict:
    nb = nbformat.read(str(NOTEBOOK), as_version=4)
    cells = [c for c in nb.cells
             if c.cell_type == "code" and "download" in (c.metadata.get("tags") or [])]
    if not cells:
        raise SystemExit(f"no download cell found in {NOTEBOOK.name}")
    src = cells[0].source.replace("AUTO_DOWNLOAD = True", "AUTO_DOWNLOAD = False")
    ns: dict = {"__name__": "__step0__"}
    exec(compile(src, str(NOTEBOOK), "exec"), ns)
    return ns


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=["tse", "ibge"], help="download only one group")
    args = ap.parse_args()

    ns = load_step0()
    ns["download_all"](only=args.only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
