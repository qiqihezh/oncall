from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
FORBIDDEN_CHARS = set("*?[]{}")


def read_file(fname: str) -> str:
    if not fname or Path(fname).name != fname:
        raise ValueError("readFile only accepts a plain file name")
    if any(char in fname for char in FORBIDDEN_CHARS):
        raise ValueError("readFile does not accept wildcards or patterns")

    target = (DATA_DIR / fname).resolve()
    data_root = DATA_DIR.resolve()
    if data_root not in target.parents and target != data_root:
        raise ValueError("readFile cannot access files outside data/")
    if not target.is_file():
        raise FileNotFoundError(fname)

    return target.read_text(encoding="utf-8")
