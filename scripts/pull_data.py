"""Restore generated splits from the Hub into the local layout (images/<id>.png + meta.jsonl).

Usage: python scripts/pull_data.py --repo musapeker/pix2db-data --out data
"""
import argparse
import json
from pathlib import Path

from datasets import load_dataset

DIRS = {"train": "train", "validation": "val", "test": "test",
        "real_pubtabnet": "real_pubtabnet", "real_cord": "real_cord",
        "train_real": "real_train", "train_receipt": "receipt_train", "real_fintabnet": "real_fintabnet",
        "test_receipt": "test_receipt", "unseen_tabrecset": "unseen_tabrecset"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="musapeker/pix2db-data")
    ap.add_argument("--out", default="data")
    ap.add_argument("--splits", nargs="*", default=None)
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()
    for split, d in DIRS.items():
        if args.splits and split not in args.splits:
            continue
        ds = load_dataset(args.repo, split=split)
        out = Path(args.out) / d
        (out / "images").mkdir(parents=True, exist_ok=True)

        def save(ex):
            p = out / "images" / f"{ex['id']}.png"
            if not p.exists():
                ex["image"].save(p)
            return {"w": ex["image"].size[0], "h": ex["image"].size[1]}

        sizes = ds.map(save, num_proc=args.workers, remove_columns=["image"])
        with (out / "meta.jsonl").open("w", encoding="utf-8") as f:
            for ex in sizes:
                m = {"id": ex["id"], "level": ex["level"], "kind": ex["kind"], "size": [ex["w"], ex["h"]],
                     "scene": json.loads(ex["scene"]), "num_tol_abs": ex["num_tol_abs"]}
                if ex["recall_only"]:
                    m["recall_only"] = True
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
        print(split, len(ds), "->", out)


if __name__ == "__main__":
    main()
