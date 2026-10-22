"""Pick demo examples from the eval sets and cache the v2 model outputs for them.

Writes space/examples/<NN_name>.png and space/examples/cache.json {md5(RGB pixels): raw model output}.
Picks, per slot, the first eval item (sorted by id) the model got right (f1 >= min_f1 after repair).
"""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
from PIL import Image

SLOTS = [  # (file name, eval set, filter)
    ("01_merged_cells", "test", lambda r: r.level == 3),
    ("02_invoice_with_foreign_key", "test", lambda r: r.level == 4),
    ("03_scanned_document", "test", lambda r: r.level == 5 and r.kind == "doc"),
    ("04_chart", "test", lambda r: r.level == 6),
    ("05_receipt", "test_receipt", lambda r: True),
    ("06_receipt_photo_cord", "real_cord", lambda r: True),
    ("07_scientific_table_pubtabnet", "real_pubtabnet", lambda r: True),
    ("08_financial_table_fintabnet", "real_fintabnet", lambda r: True),
    ("09_table_photo_tabrecset", "unseen_tabrecset", lambda r: True),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs/eval")
    ap.add_argument("--data", default="data")
    ap.add_argument("--system", default="pix2db-2b-v2__sql")
    ap.add_argument("--out", default="space/examples")
    ap.add_argument("--min-f1", type=float, default=0.95)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = {}
    for name, s, filt in SLOTS:
        df = pd.read_csv(Path(args.runs) / s / "scores.csv")
        df = df[(df.system == args.system + "+repair") & (df.f1 >= args.min_f1)].sort_values("id")
        df = df[[bool(filt(r)) for r in df.itertuples()]]
        if df.empty:
            print("no example for", name)
            continue
        sid = df.iloc[0].id
        outs = {json.loads(l)["id"]: json.loads(l)["output"]
                for l in open(Path(args.runs) / s / f"{args.system}.jsonl", encoding="utf-8")}
        img = Image.open(Path(args.data) / s / "images" / f"{sid}.png").convert("RGB")
        img.save(out / f"{name}.png")
        cache[hashlib.md5(img.tobytes()).hexdigest()] = outs[sid]
        print(name, s, sid, round(float(df.iloc[0].f1), 3))
    json.dump(cache, open(out / "cache.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
