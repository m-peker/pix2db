"""Dataset helpers."""
from __future__ import annotations

import json
from pathlib import Path


def load_meta(data_dir: str | Path) -> list[dict]:
    """Read meta.jsonl or all meta_*.jsonl shards of a generated set, sorted by id."""
    d = Path(data_dir)
    files = [d / "meta.jsonl"] if (d / "meta.jsonl").exists() else sorted(d.glob("meta_*.jsonl"))
    items = [json.loads(l) for f in files for l in f.open(encoding="utf-8") if l.strip()]
    return sorted(items, key=lambda x: x["id"])
