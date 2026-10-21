"""Restore generated splits from the Hub into the local layout (images/<id>.png + meta.jsonl).

Usage: python scripts/pull_data.py --repo musapeker/pix2db-data --out data
"""
import argparse
import json
from pathlib import Path

from datasets import load_dataset

DIRS = {"train": "train", "validation": "val", "test": "test",
        "real_pubtabnet": "real_pubtabnet", "real_cord": "real_cord"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="musapeker/pix2db-data")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    for split, d in DIRS.items():
        ds = load_dataset(args.repo, split=split)
        out = Path(args.out) / d
        (out / "images").mkdir(parents=True, exist_ok=True)
        with (out / "meta.jsonl").open("w", encoding="utf-8") as f:
            for ex in ds:
                ex["image"].save(out / "images" / f"{ex['id']}.png")
                m = {"id": ex["id"], "level": ex["level"], "kind": ex["kind"], "size": list(ex["image"].size),
                     "scene": json.loads(ex["scene"]), "num_tol_abs": ex["num_tol_abs"]}
                if ex["recall_only"]:
                    m["recall_only"] = True
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
        print(split, len(ds), "->", out)


if __name__ == "__main__":
    main()
