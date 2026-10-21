"""Real-image TRAINING data (disjoint from the real eval sets, which come from val/test splits).

  pubtabnet : apoidea/pubtabnet-html  split=train   (CDLA-Permissive-1.0)
  fintabnet : apoidea/fintabnet-html  split=train   (FinTabNet, CDLA-Permissive-1.0)
  cord      : naver-clova-ix/cord-v2  split=train   (CC-BY-4.0)

Usage: python scripts/make_real_train.py --which pubtabnet --n 10000 --out data/real_train
Output format = make_set.py (images/<id>.png + meta_<which>.jsonl).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_real import clean_text, num_id  # noqa: E402
from pix2db.htmltable import html_to_table  # noqa: E402
from pix2db.scene import Column, Scene, Table, coerce_column, infer_type  # noqa: E402

MAX_PIXELS = 1400 * 1800


def save(img, sid, out, f, level, kind, scene):
    img = img.convert("RGB")
    if img.size[0] * img.size[1] > MAX_PIXELS:
        img.thumbnail((1400, 1800))
    img.save(out / "images" / f"{sid}.png")
    f.write(json.dumps({"id": sid, "level": level, "kind": kind, "size": img.size,
                        "scene": scene.to_dict(), "num_tol_abs": 0.0}, ensure_ascii=False) + "\n")


def tables(which: str, n: int, rng: random.Random, out: Path, accept: float, split: str = "train"):
    from datasets import load_dataset
    repo = {"pubtabnet": "apoidea/pubtabnet-html", "fintabnet": "apoidea/fintabnet-html"}[which]
    ds = load_dataset(repo, *([] if which == "pubtabnet" else ["en"]), split=split, streaming=True).shuffle(seed=42, buffer_size=2000)
    kept = seen = 0
    with (out / f"meta_{which}.jsonl").open("w", encoding="utf-8") as f:
        for ex in ds:
            if kept >= n:
                break
            seen += 1
            if rng.random() > accept:
                continue
            h = ex.get("html_table") or ex.get("html")
            if not isinstance(h, str) or "<table" not in h:
                continue
            t = html_to_table(h)
            if t is None:
                continue
            # rough target-length guard (tokens ~ chars / 3)
            if len(Scene(which, [t]).to_sql()) > 6000:
                continue
            save(ex["image"], f"{which}_{kept:05d}", out, f, 7, which, Scene(which, [t]))
            kept += 1
            if kept % 1000 == 0:
                print(f"{which}: {kept} kept / {seen} seen", flush=True)
    print(f"{which}: {kept} kept / {seen} seen")


def cord(n: int, out: Path):
    from datasets import load_dataset
    ds = load_dataset("naver-clova-ix/cord-v2", split="train")
    kept = 0
    with (out / "meta_cord.jsonl").open("w", encoding="utf-8") as f:
        for ex in ds:
            if kept >= n:
                break
            gp = json.loads(ex["ground_truth"])["gt_parse"]
            menu = gp.get("menu", [])
            menu = [menu] if isinstance(menu, dict) else menu
            rows = []
            for m in menu:
                if not isinstance(m, dict) or "nm" not in m or "price" not in m:
                    continue
                nm = m["nm"] if isinstance(m["nm"], str) else " ".join(map(str, m["nm"]))
                cnt = m.get("cnt")
                cnt = num_id(cnt.rstrip("xX").strip()) if isinstance(cnt, str) else None
                rows.append([clean_text(nm), cnt, num_id(m["price"]) if isinstance(m["price"], str) else None])
            if len(rows) < 1:
                continue
            cols = [coerce_column(list(c)) for c in zip(*rows)]
            rows = [list(r) for r in zip(*cols)]
            t = Table("items", [Column(nm, infer_type(list(c))) for nm, c in
                                zip(["item_name", "quantity", "price"], cols)], rows)
            save(ex["image"], f"cord_{kept:05d}", out, f, 8, "cord", Scene("cord", [t]))
            kept += 1
    print("cord kept", kept)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", choices=["pubtabnet", "fintabnet", "cord"], required=True)
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--accept", type=float, default=0.5, help="random thinning of the stream for variety")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--split", default="train", help="dataset split (use test/validation for eval sets)")
    args = ap.parse_args()
    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    if args.which == "cord":
        cord(args.n, out)
    else:
        tables(args.which, args.n, random.Random(args.seed), out, args.accept, args.split)


if __name__ == "__main__":
    main()
