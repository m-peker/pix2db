"""Download the pix2db dataset from the Hub and write plain files: <id>.png + <id>.sql per example.

Usage: python scripts/export_dataset.py --repo musapeker/pix2db-data --split validation --out preview [--per-level 5]
"""
import argparse
import collections
from pathlib import Path

from datasets import load_dataset


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="musapeker/pix2db-data")
    ap.add_argument("--split", default="validation")
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-level", type=int, default=None, help="max examples per level (default: all)")
    args = ap.parse_args()
    ds = load_dataset(args.repo, split=args.split)
    seen = collections.Counter()
    for ex in ds:
        if args.per_level and seen[ex["level"]] >= args.per_level:
            continue
        seen[ex["level"]] += 1
        d = Path(args.out) / args.split / f"L{ex['level']}_{ex['level_name']}"
        d.mkdir(parents=True, exist_ok=True)
        ex["image"].save(d / f"{ex['id']}.png")
        (d / f"{ex['id']}.sql").write_text(ex["sql"] + "\n", encoding="utf-8")
    print(dict(seen))


if __name__ == "__main__":
    main()
