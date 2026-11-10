"""Independent multi-table test set: invoice images from katanaml-org/invoices-donut-data-v1 (MIT).

Gold = two tables linked by a foreign key:
  invoice(invoice_no PK, invoice_date, seller, client, seller_tax_id, client_tax_id, iban)
  item(invoice_no FK -> invoice, description, quantity, net_price, net_worth, vat, gross_worth)
Summary totals are not stored (derived rows, as in the prompt). Numbers: decimal comma -> float,
'10%' -> 10.0; dates MM/DD/YYYY -> YYYY-MM-DD. Never used for training.
Usage: python scripts/make_invoices.py --out data/real_invoices [--limit 10]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from datasets import load_dataset

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pix2db.scene import Column, ForeignKey, Scene, Table, coerce_column, infer_type  # noqa: E402

HEADER = [("invoice_no", "invoice_no"), ("invoice_date", "invoice_date"), ("seller", "seller"),
          ("client", "client"), ("seller_tax_id", "seller_tax_id"), ("client_tax_id", "client_tax_id"),
          ("iban", "iban")]
ITEM = [("item_desc", "description"), ("item_qty", "quantity"), ("item_net_price", "net_price"),
        ("item_net_worth", "net_worth"), ("item_vat", "vat"), ("item_gross_worth", "gross_worth")]


def num(s):
    if s is None:
        return None
    t = str(s).strip().replace("%", "").replace(" ", "").replace("$", "")
    if re.fullmatch(r"-?[\d.]*,\d+", t):
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return str(s).strip()


def date(s):
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*", str(s or ""))
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else (s or None)


def to_scene(gt: dict, sid: str) -> Scene | None:
    h, items = gt.get("header") or {}, gt.get("items") or []
    if not h.get("invoice_no") or not items:
        return None
    if isinstance(items, dict):
        items = [items]
    key = coerce_column([str(h["invoice_no"]).strip()])[0]
    hvals = [key] + [date(h.get(k)) if k == "invoice_date" else (str(h.get(k)).strip() if h.get(k) else None)
                     for k, _ in HEADER[1:]]
    hcols = [Column(n, infer_type([v])) for (_, n), v in zip(HEADER, hvals)]
    rows = []
    for it in items:
        r = [key, (it.get("item_desc") or "").strip() or None] + [num(it.get(k)) for k, _ in ITEM[1:]]
        rows.append(r)
    icols = [Column("invoice_no", hcols[0].type)] + [
        Column(n, infer_type([r[j + 1] for r in rows])) for j, (_, n) in enumerate(ITEM)]
    inv = Table("invoice", hcols, [hvals], "invoice_no")
    item = Table("item", icols, rows, None)
    return Scene(sid, [inv, item], [ForeignKey("item", "invoice_no", "invoice", "invoice_no")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="katanaml-org/invoices-donut-data-v1")
    ap.add_argument("--splits", nargs="+", default=["test", "validation"])
    ap.add_argument("--out", default="data/real_invoices")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    n = skipped = 0
    with (out / "meta.jsonl").open("w", encoding="utf-8") as f:
        for split in args.splits:
            for k, ex in enumerate(load_dataset(args.repo, split=split)):
                if args.limit and n >= args.limit:
                    break
                gt = json.loads(ex["ground_truth"])["gt_parse"]
                sid = f"inv_{split[:3]}_{k:04d}"
                scene = to_scene(gt, sid)
                if scene is None:
                    skipped += 1
                    continue
                img = ex["image"].convert("RGB")
                img.save(out / "images" / f"{sid}.png")
                f.write(json.dumps({"id": sid, "level": 12, "kind": "invoice", "size": list(img.size),
                                    "scene": scene.to_dict(), "num_tol_abs": 0.0, "recall_only": True}, ensure_ascii=False) + "\n")
                n += 1
    print(f"{n} invoices written to {out} ({skipped} skipped)")


if __name__ == "__main__":
    main()
