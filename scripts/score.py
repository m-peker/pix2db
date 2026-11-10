"""Score run files against gold scenes and print a level × system table.

Usage: python scripts/score.py --data data/feas --runs runs/feas [--show-errors 3]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pix2db.data import load_meta  # noqa: E402
from pix2db.dbio import load_html_tables, load_sql, read_db  # noqa: E402
from pix2db.metrics import score as _score  # noqa: E402
from pix2db.queries import query_equivalence  # noqa: E402

_GOLD = {}


def score(scene, pred_tables, tol, con=None, key=None):
    """Cell/schema metrics plus query-execution equivalence on the predicted database."""
    s = _score(scene, pred_tables, tol)
    align = s.pop("_align", {})
    if con is not None:
        if key not in _GOLD:
            _GOLD[key] = load_sql(scene.to_sql()).con
        ok, n = query_equivalence(scene, _GOLD[key], con, align, tol)
        s.update(q_ok=ok, q_n=n, q_acc=ok / n if n else None)
    return s
from pix2db.repair import repair  # noqa: E402
from pix2db.scene import Scene  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--show-errors", type=int, default=0)
    ap.add_argument("--repair", action="store_true", help="also score SQL runs after the repair layer")
    args = ap.parse_args()

    meta = {d["id"]: d for d in load_meta(args.data)}
    rows = []
    for f in sorted(Path(args.runs).glob("*.jsonl")):
        system = f.stem
        is_html = system.endswith("__html")
        for l in f.open(encoding="utf-8"):
            r = json.loads(l)
            m = meta[r["id"]]
            scene = Scene.from_dict(m["scene"])
            lr = load_html_tables(r["output"]) if is_html else load_sql(r["output"])
            s = score(scene, read_db(lr.con), m.get("num_tol_abs", 0.0), lr.con, r["id"])
            s.update(id=r["id"], level=m["level"], kind=m["kind"], system=system,
                     exec_ok=float(lr.n_errors == 0 and lr.n_statements > 0),
                     n_tokens=r.get("n_tokens"), seconds=r.get("seconds"))
            rows.append(s)
            if args.repair and not is_html:
                rp = repair(r["output"])
                s2 = score(scene, read_db(rp.con), m.get("num_tol_abs", 0.0), rp.con, r["id"])
                s2.update(id=r["id"], level=m["level"], kind=m["kind"], system=system + "+repair",
                          exec_ok=float(rp.ok and bool(rp.sql)), n_tokens=r.get("n_tokens"),
                          seconds=r.get("seconds"), n_warnings=len(rp.warnings))
                rows.append(s2)
            if args.show_errors and lr.errors and args.show_errors > 0:
                print(system, r["id"], lr.errors[:2])
                args.show_errors -= 1
    df = pd.DataFrame(rows)
    out = Path(args.runs) / "scores.csv"
    df.to_csv(out, index=False)

    pd.set_option("display.width", 200)
    for metric in ["f1", "recall", "table_exact", "type_acc", "exec_ok"]:
        piv = df.pivot_table(index="system", columns="level", values=metric, aggfunc="mean")
        piv["all"] = df.groupby("system")[metric].mean()
        print(f"\n== {metric} ==")
        print(piv.round(3).to_string())
    fk = df[df.fk_recall.notna()]
    if len(fk):
        print("\n== fk_recall (doc scenes) ==")
        print(fk.groupby("system").fk_recall.mean().round(3).to_string())
    g = df.groupby("system")
    sch = pd.DataFrame({"q_acc": g.q_ok.sum() / g.q_n.sum(),
                        "fk_precision": g.n_pred_fk_ok.sum() / g.n_pred_fk.sum().replace(0, float("nan")),
                        "pk_precision": g.n_pred_pk_ok.sum() / g.n_pred_pk.sum().replace(0, float("nan")),
                        "ref_integrity": g.ref_integrity.mean(), "table_count_ok": g.table_count_ok.mean(),
                        "col_count_ok": g.col_count_ok.mean()})
    print("\n== schema and query equivalence (pooled) ==")
    print(sch.round(3).to_string())
    print("\n== mean output tokens / sec per image ==")
    print(df.groupby("system")[["n_tokens", "seconds"]].mean().round(1).to_string())
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
