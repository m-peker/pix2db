"""Repair-layer ablation and information-loss accounting (revision, Reviewer A #7 / Reviewer B).

For every SQL run in paper/cache/runs/eval_runs_v2/<set>/ it applies: no repair, full repair, full minus one
strategy, and one strategy alone. It reports execution rate and cell F1, and for full repair the number of
rows dropped, primary keys removed and the F1 of outputs that only execute after repair ("rescued").
Output: paper/cache/repair_ablation.csv, paper/cache/repair_loss.csv
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pix2db.dbio import load_sql, read_db  # noqa: E402
from pix2db.metrics import score  # noqa: E402
from pix2db.repair import STRATEGIES, repair  # noqa: E402
from pix2db.scene import Scene  # noqa: E402

RUNS = ROOT / "paper/cache/runs/eval_runs_v2"
SETS = ["test", "real_pubtabnet", "real_fintabnet", "real_cord", "test_receipt"]
SYSTEMS = ["pix2db-2b-v2__sql", "pix2db-2b-v1__sql", "Qwen3-VL-2B-Instruct__sql", "Qwen3-VL-8B-Instruct__sql"]
CONFIGS = {"none": (), "full": STRATEGIES}
CONFIGS.update({f"-{s}": tuple(x for x in STRATEGIES if x != s) for s in STRATEGIES})
CONFIGS.update({f"only {s}": (s,) for s in STRATEGIES})


def main():
    allmeta = pd.read_parquet(ROOT / "paper/cache/meta_all.parquet")
    tolf = ROOT / "paper/cache/num_tol.json"  # id -> chart tolerance (not stored in meta_all)
    tol = json.load(open(tolf)) if tolf.exists() else {}
    abl, loss = [], []
    for st in SETS:
        meta = allmeta[allmeta.split == st].set_index("id")
        for sysn in SYSTEMS:
            f = RUNS / st / f"{sysn}.jsonl"
            if not f.exists():
                continue
            for line in f.open(encoding="utf-8"):
                r = json.loads(line)
                m = meta.loc[r["id"]]
                sc = Scene.from_dict(json.loads(m.scene) if isinstance(m.scene, str) else m.scene)
                raw = load_sql(r["output"])
                raw_ok = raw.n_errors == 0 and raw.n_statements > 0
                for cname, en in CONFIGS.items():
                    if cname == "none":
                        con, ok = raw.con, raw_ok
                    else:
                        rp = repair(r["output"], en)
                        con, ok = rp.con, rp.ok and bool(rp.sql)
                    s = score(sc, read_db(con), tol.get(r["id"], 0.0))
                    abl.append(dict(set=st, system=sysn, config=cname, id=r["id"], exec_ok=float(ok), f1=s["f1"],
                                    exact=s["table_exact"]))
                    if cname == "full":
                        dropped = sum(int(w.split()[0]) for w in rp.warnings if "could not be repaired" in w)
                        loss.append(dict(set=st, system=sysn, id=r["id"], raw_ok=raw_ok, rep_ok=ok,
                                         rescued=(not raw_ok) and ok, f1=s["f1"], precision=s["precision"],
                                         rows_dropped=dropped,
                                         pk_dropped=sum("dropped PRIMARY KEY" in x for x in rp.repairs),
                                         n_repairs=len(rp.repairs), gold_rows=sum(len(t.rows) for t in sc.tables)))
            print(st, sysn, flush=True)
    a = pd.DataFrame(abl)
    a.to_csv(ROOT / "paper/cache/repair_ablation.csv", index=False)
    lo = pd.DataFrame(loss)
    lo.to_csv(ROOT / "paper/cache/repair_loss.csv", index=False)
    pd.set_option("display.width", 220)
    print(a.groupby(["system", "config"])[["exec_ok", "f1"]].mean().unstack(0).round(3))
    print(lo.groupby("system").agg(n=("id", "size"), raw_ok=("raw_ok", "mean"), rescued=("rescued", "sum"),
                                   rows_dropped=("rows_dropped", "sum"), gold_rows=("gold_rows", "sum"),
                                   pk_dropped=("pk_dropped", "sum")))
    print("F1 / precision of rescued outputs:")
    print(lo[lo.rescued].groupby("system")[["f1", "precision"]].agg(["mean", "size"]).round(3))


if __name__ == "__main__":
    main()
