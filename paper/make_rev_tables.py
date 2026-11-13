"""Tables and numbers for the FAITH revision, from the scored runs in cache/rev/runs/rev/<set>/scores*.csv.

Writes paper/tables_rev/<name>.json (header + rows of strings) and paper/tables_rev/numbers.json.
Systems that are not scored yet (pending trainings) are skipped, so the script can be rerun at any time.
Usage: python paper/make_rev_tables.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
RUNS = HERE / "cache" / "rev" / "runs" / "rev"
OUT = HERE / "tables_rev"
OUT.mkdir(exist_ok=True)
RNG = np.random.default_rng(42)
B = 2000

SYS = {  # key -> (system name in scores, label)
    "ours": ("pix2db-2b-v2__sql+repair", "PIX2DB-2b (ours)"),
    "ours_raw": ("pix2db-2b-v2__sql", "PIX2DB-2b, no repair"),
    "seed1": ("rev_seed1__sql+repair", "PIX2DB-2b, seed 1"),
    "seed2": ("rev_seed2__sql+repair", "PIX2DB-2b, seed 2"),
    "html2b": ("rev_html__html", "2B fine-tuned → HTML → SQLite"),
    "synth": ("rev_synth__sql+repair", "synthetic only (36,589)"),
    "real": ("rev_real__sql+repair", "real only (19,589)"),
    "v1": ("pix2db-2b-v1__sql+repair", "synthetic only (24,000, v1)"),
    "q8": ("Qwen3-VL-8B-Instruct__sql+repair", "Qwen3-VL-8B → SQL"),
    "h8": ("Qwen3-VL-8B-Instruct__html", "Qwen3-VL-8B → HTML → SQLite"),
    "q4": ("Qwen3-VL-4B-Instruct__sql+repair", "Qwen3-VL-4B → SQL"),
    "q2": ("Qwen3-VL-2B-Instruct__sql+repair", "Qwen3-VL-2B → SQL (base)"),
    "dl": ("docling__html", "Docling (TableFormer + OCR)"),
}
SETS = {  # key -> (dir, primary metric, label)
    "synth": ("test", "table_exact", "Synthetic"),
    "ptn": ("real_pubtabnet", "f1", "PubTabNet"),
    "ftn": ("real_fintabnet", "f1", "FinTabNet"),
    "cord": ("real_cord", "recall", "CORD"),
    "rcpt": ("test_receipt", "recall", "Receipts"),
    "trs": ("unseen_tabrecset", "f1", "TabRecSet"),
    "inv": ("real_invoices", "recall", "Invoices"),
    "chart": ("test_chart", "table_exact", "Charts"),
}
DEG = ["clean", "rotation", "lighting", "noise", "blur", "contrast", "grayscale", "jpeg", "all"]

_cache: dict[str, pd.DataFrame] = {}



def sg(x):
    """Signed 2-decimal value; values that round to zero are written 0.00 (no sign)."""
    return "0.00" if abs(x) < 0.005 else f"{x:+.2f}"

def load(d: str) -> pd.DataFrame:
    if d not in _cache:
        fs = sorted((RUNS / d).glob("scores*.csv"))
        _cache[d] = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True) if fs else pd.DataFrame()
    return _cache[d]


def get(d: str, key: str) -> pd.DataFrame:
    df = load(d)
    if df.empty:
        return df
    return df[df.system == SYS[key][0]].drop_duplicates("id").set_index("id").sort_index()


def has(d, key):
    return len(get(d, key)) > 0


def boot_ci(x: np.ndarray):
    idx = RNG.integers(0, len(x), (B, len(x)))
    m = x[idx].mean(1)
    return np.quantile(m, 0.025), np.quantile(m, 0.975)


def paired(a: pd.Series, b: pd.Series):
    """Mean difference a-b, 95% paired bootstrap interval, one-sided p (a not better than b)."""
    ids = a.index.intersection(b.index)
    d = (a.loc[ids] - b.loc[ids]).to_numpy(float)
    idx = RNG.integers(0, len(d), (B, len(d)))
    m = d[idx].mean(1)
    return d.mean(), np.quantile(m, 0.025), np.quantile(m, 0.975), float((m <= 0).mean())


def f2(x):
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.2f}"


def f3(x):
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.3f}"


def save(name, header, rows, **extra):
    (OUT / f"{name}.json").write_text(json.dumps({"header": header, "rows": rows, **extra}, ensure_ascii=False, indent=1),
                                      encoding="utf-8")


NUM: dict[str, str] = {}


def main():
    # ---------------------------------------------------------------- main comparison (Section 5)
    order = ["ours", "html2b", "q8", "h8", "q4", "q2", "dl"]
    rows, best = [], {}
    for sk, (d, met, _) in SETS.items():  # best = every system tied with the maximum at two decimals
        vals = {k: round(get(d, k)[met].mean(), 2) for k in order if has(d, k)}
        best[sk] = {k for k, v in vals.items() if v == max(vals.values())}
    for k in order:
        r = [SYS[k][1]]
        for sk, (d, met, _) in SETS.items():
            if not has(d, k):
                r.append("–")
                continue
            x = get(d, k)[met].to_numpy(float)
            lo, hi = boot_ci(x)
            a, ci = f"{x.mean():.2f}", f"[{lo:.2f}, {hi:.2f}]"
            r.append(f"<b>{a}</b>\n{ci}" if k in best[sk] else f"{a}\n{ci}")
        fk = get("test", k).fk_recall.dropna() if has("test", k) else pd.Series(dtype=float)
        r.append(f2(fk.mean()) if len(fk) else "–")
        rows.append(r)
    fks = [float(r[-1]) for r in rows if r[-1] != "–"]  # bold the best FK recall as well
    for r in rows:
        if r[-1] != "–" and float(r[-1]) == max(fks):
            r[-1] = f"<b>{r[-1]}</b>"
    save("main", ["System"] + [v[2] for v in SETS.values()] + ["FK recall"], rows)

    # significance: ours vs every competitor on every set
    sig = []
    for sk, (d, met, lab) in SETS.items():
        for k in order[1:]:
            if not has(d, k):
                continue
            m, lo, hi, p = paired(get(d, "ours")[met], get(d, k)[met])
            sig.append([lab, SYS[k][1], f"{m:+.3f}", f"[{lo:+.3f}, {hi:+.3f}]", "<0.001" if p < 0.001 else f"{p:.3f}"])
            NUM[f"diff_{sk}_{k}"] = sg(m)
            NUM[f"p_{sk}_{k}"] = "< 0.001" if p < 0.001 else f"= {p:.3f}"
            NUM[f"ci_{sk}_{k}"] = f"[{sg(lo)}, {sg(hi)}]"
    save("significance", ["Set", "Competitor", "Δ (ours − competitor)", "95% interval", "p (one-sided)"], sig)
    for sk, (d, met, _) in SETS.items():
        for k in order + ["v1", "synth", "real", "seed1", "seed2", "ours_raw"]:
            if has(d, k):
                NUM[f"{sk}_{k}"] = f2(get(d, k)[met].mean())
                NUM[f"{sk}_{k}_f1"] = f2(get(d, k).f1.mean())

    # ---------------------------------------------------------------- per level (synthetic test)
    lv_sys = ["ours", "html2b", "q8", "h8", "q2", "dl"]
    rows = []
    for k in lv_sys:
        if not has("test", k):
            continue
        g = get("test", k)
        ex = g.groupby("level").table_exact.mean()
        f1 = g.groupby("level").f1.mean()
        rows.append([SYS[k][1]] + [f"{ex[l]:.2f} / {f1[l]:.2f}" for l in range(1, 7)])
        for l in range(1, 7):
            NUM[f"lv{l}_{k}"] = f2(ex[l])
            NUM[f"lv{l}_{k}_f1"] = f2(f1[l])
    save("levels", ["System", "L1 clean", "L2 styled", "L3 hierarchical", "L4 document", "L5 scan", "L6 chart"], rows)
    # per-level error profile of ours: exact failures by cause
    g = get("test", "ours")
    prof = []
    for l in range(1, 7):
        x = g[g.level == l]
        prof.append([f"L{l}", f2(x.table_exact.mean()), f2(x.f1.mean()), f2(x.rowcount_ok.mean()),
                     f2(x.type_acc.mean()), f2(x.exec_ok.mean())])
    save("levels_ours", ["Level", "Exact", "Cell F1", "Row count right", "Type acc.", "Executes"], prof)
    for l in range(1, 7):  # failures of exact match: how far off are they?
        x = g[(g.level == l) & (g.table_exact < 1)]
        miss = x.gold_cells - x.matched
        NUM[f"lvfail{l}_n"] = str(len(x))
        NUM[f"lvfail{l}_le2"] = f"{(miss <= 2).mean() * 100:.0f}%"
        NUM[f"lvfail{l}_rows"] = f"{(1 - x.rowcount_ok.mean()) * 100:.0f}%"

    # ---------------------------------------------------------------- degradations
    rows = []
    for k in ["ours", "html2b", "q8", "h8", "dl"]:
        if not all(has(f"degrade/{v}", k) for v in DEG):
            continue
        met = "f1" if k == "dl" else "table_exact"
        r = [SYS[k][1] + (" (F1)" if k == "dl" else "")]
        for v in DEG:
            x = get(f"degrade/{v}", k)[met].mean()
            r.append(f2(x))
            NUM[f"deg_{v}_{k}"] = f2(x)
        rows.append(r)
    save("degrade", ["System", "Clean", "Rotation", "Lighting", "Noise", "Blur", "Contrast", "Grayscale", "JPEG",
                     "All"], rows)
    # paired: clean vs each variant for ours (exact), p two-sided via bootstrap
    for v in DEG[1:]:
        m, lo, hi, p = paired(get(f"degrade/{v}", "ours").table_exact, get("degrade/clean", "ours").table_exact)
        NUM[f"degci_{v}"] = f"{m:+.3f} [{lo:+.3f}, {hi:+.3f}]"

    # ---------------------------------------------------------------- charts
    meta = {}
    for f in (HERE / "cache" / "rev" / "data" / "test_chart").glob("meta*.jsonl"):
        for l in f.open(encoding="utf-8"):
            dd = json.loads(l)
            meta[dd["id"]] = (dd["chart_kind"], dd["value_labels"])
    rows = []
    kinds = ["bar", "barh", "line", "pie"]
    for k in ["ours", "html2b", "q8", "h8", "q4", "q2"]:
        if not has("test_chart", k):
            continue
        g = get("test_chart", k).copy()
        g["ck"] = [meta[i][0] for i in g.index]
        g["lab"] = [meta[i][1] for i in g.index]
        r = [SYS[k][1]] + [f2(g[g.ck == c].table_exact.mean()) for c in kinds]
        r += [f2(g[g.lab].table_exact.mean()), f2(g[~g.lab].table_exact.mean()),
              f2(g[g.lab].f1.mean()), f2(g[~g.lab].f1.mean()), f2(g.table_exact.mean())]
        rows.append(r)
        for c in kinds:
            NUM[f"ch_{c}_{k}"] = f2(g[g.ck == c].table_exact.mean())
        NUM[f"ch_lab_{k}"] = f2(g[g.lab].table_exact.mean())
        NUM[f"ch_unlab_{k}"] = f2(g[~g.lab].table_exact.mean())
        NUM[f"ch_labf1_{k}"] = f2(g[g.lab].f1.mean())
        NUM[f"ch_unlabf1_{k}"] = f2(g[~g.lab].f1.mean())
    n = pd.Series([v[0] for v in meta.values()]).value_counts()
    NUM.update({f"nch_{c}": str(n.get(c, 0)) for c in kinds})
    NUM["nch_lab"] = str(sum(v[1] for v in meta.values()))
    NUM["nch_unlab"] = str(sum(not v[1] for v in meta.values()))
    save("charts", ["System", "Bar", "Horiz. bar", "Line", "Pie", "Labeled exact", "Unlabeled exact",
                    "Labeled F1", "Unlabeled F1", "All exact"], rows)

    # ---------------------------------------------------------------- schema and query metrics (synthetic test)
    rows = []
    for k in ["ours", "seed1", "seed2", "html2b", "q8", "h8", "q4", "q2", "dl", "synth", "real"]:
        if not has("test", k):
            continue
        g = get("test", k)
        fkp = g.n_pred_fk_ok.sum() / g.n_pred_fk.sum() if g.n_pred_fk.sum() else np.nan
        pkp = g.n_pred_pk_ok.sum() / g.n_pred_pk.sum() if g.n_pred_pk.sum() else np.nan
        r = [SYS[k][1], f2(g.fk_recall.dropna().mean()), f2(fkp), f2(g.ref_integrity.mean()), f2(pkp),
             f2(g.table_count_ok.mean()), f2(g.col_count_ok.mean()), f2(g.type_acc.mean()),
             f2(g.q_ok.sum() / g.q_n.sum())]
        if k not in ("synth", "real"):  # ablation models: numbers only, not in the schema table
            rows.append(r)
        NUM[f"fkr_{k}"], NUM[f"fkp_{k}"], NUM[f"ri_{k}"], NUM[f"pkp_{k}"] = r[1], r[2], r[3], r[4]
        NUM[f"tc_{k}"], NUM[f"cc_{k}"], NUM[f"ta_{k}"], NUM[f"qa_{k}"] = r[5], r[6], r[7], r[8]
        NUM[f"nfk_{k}"] = f"{int(g.n_pred_fk_ok.sum())}/{int(g.n_pred_fk.sum())}"
        NUM[f"npk_{k}"] = f"{int(g.n_pred_pk_ok.sum())}/{int(g.n_pred_pk.sum())}"
    save("schema", ["System", "FK recall", "FK precision", "Ref. integrity", "PK precision", "Table count",
                    "Column count", "Type acc.", "Query equiv."], rows)
    # query equivalence on all sets
    rows = []
    for k in ["ours", "html2b", "q8", "h8", "q4", "q2", "dl"]:
        r = [SYS[k][1]]
        for sk, (d, _, _) in SETS.items():
            if has(d, k):
                g = get(d, k)
                x = g.q_ok.sum() / g.q_n.sum()
                r.append(f2(x))
                NUM[f"qe_{sk}_{k}"] = f2(x)
            else:
                r.append("–")
        rows.append(r)
    save("query", ["System"] + [v[2] for v in SETS.values()], rows)

    # invoices detail
    rows = []
    for k in ["ours", "seed1", "seed2", "html2b", "q8", "q4", "q2", "h8", "dl"]:
        if not has("real_invoices", k):
            continue
        g = get("real_invoices", k)
        r = [SYS[k][1], f2(g.recall.mean()), f2(g.fk_recall.dropna().mean()) if g.fk_recall.notna().any() else "–",
             f2(g.n_pred_tables.mean()), f2(g.q_ok.sum() / g.q_n.sum())]
        rows.append(r)
        NUM[f"inv_rec_{k}"], NUM[f"inv_fk_{k}"], NUM[f"inv_nt_{k}"] = r[1], r[2], r[3]
    save("invoices", ["System", "Cell recall", "FK recall", "Tables per output", "Query equiv."], rows)
    # item-table-only recall of ours on invoices: share of gold cells in item table found
    # (approximated by recall restricted to outputs with one table)

    # ---------------------------------------------------------------- data ablation
    rows = []
    for k in ["v1", "synth", "real", "ours"]:
        r = [SYS[k][1] if k != "ours" else "mixed (36,589, v2)"]
        ok = False
        for sk, (d, met, _) in SETS.items():
            if has(d, k):
                ok = True
                r.append(f2(get(d, k)[met].mean()))
            else:
                r.append("–")
        fk = get("test", k).fk_recall.dropna() if has("test", k) else pd.Series(dtype=float)
        r.append(f2(fk.mean()) if len(fk) else "–")
        if ok:
            rows.append(r)
    save("data_ablation", ["Training data"] + [v[2] for v in SETS.values()] + ["FK recall"], rows)

    # ---------------------------------------------------------------- seeds
    seeds = [k for k in ["ours", "seed1", "seed2"] if has("test", k)]
    rows = []
    for sk, (d, met, lab) in SETS.items():
        v = [get(d, k)[met].mean() for k in seeds if has(d, k)]
        rows.append([lab] + [f3(x) for x in v] + ["–"] * (3 - len(v)) +
                    [f"{np.mean(v):.3f} ± {np.std(v, ddof=1):.3f}" if len(v) > 1 else "–"])
        if len(v) > 1:
            NUM[f"seed_{sk}"] = f"{np.mean(v):.2f} ± {np.std(v, ddof=1):.2f}"
            NUM[f"seedrange_{sk}"] = f"{max(v) - min(v):.2f}"
    v = [get("test", k).fk_recall.dropna().mean() for k in seeds]
    rows.append(["FK recall"] + [f3(x) for x in v] + ["–"] * (3 - len(v)) +
                [f"{np.mean(v):.3f} ± {np.std(v, ddof=1):.3f}" if len(v) > 1 else "–"])
    NUM["nseeds"] = str(len(seeds))
    if len(seeds) > 1:
        sds = [np.std([get(d, k)[met].mean() for k in seeds], ddof=1) for d, met, _ in SETS.values()]
        NUM["seed_maxsd"] = f"{max(sds):.3f}"
        NUM["seed_maxsd_set"] = list(SETS.values())[int(np.argmax(sds))][2]
        NUM["seed_nsmall"] = ["no", "one", "two", "three", "four", "five", "six", "seven", "all"][
            sum(s < 0.01 for s in sds)]
        fk = [get("test", k).fk_recall.dropna().mean() for k in seeds]
        NUM["seed_fk"] = f"{min(fk):.2f}–{max(fk):.2f}"
    # training loss (logged every 10 steps), mean per tenth of the epoch
    for name in ["seed1", "html", "seed2", "synth", "real"]:
        f = HERE / "cache" / "rev" / "logs" / f"loss_{name}.txt"
        if f.exists() and f.stat().st_size:
            d = np.loadtxt(f)
            for q in range(10):
                m = (d[:, 0] >= q / 10) & (d[:, 0] < (q + 1) / 10 + (q == 9))
                NUM[f"loss_{name.replace('seed', 's')}_q{q + 1}"] = f"{d[m, 1].mean():.3f}"
    save("seeds", ["Set", "Seed 42", "Seed 1", "Seed 2", "Mean ± s.d."], rows)

    # ---------------------------------------------------------------- repair: per set, strategies, loss
    rows = []
    for sk, (d, _, lab) in list(SETS.items()):
        r = [lab]
        for k, kr in [("ours", "ours_raw")]:
            pass
        for raw, rep in [("pix2db-2b-v2__sql", "pix2db-2b-v2__sql+repair"),
                         ("Qwen3-VL-8B-Instruct__sql", "Qwen3-VL-8B-Instruct__sql+repair"),
                         ("Qwen3-VL-2B-Instruct__sql", "Qwen3-VL-2B-Instruct__sql+repair")]:
            df = load(d)
            a, b = df[df.system == raw], df[df.system == rep]
            if not len(a):
                r += ["–", "–"]
                continue
            r += [f"{a.exec_ok.mean():.2f} → {b.exec_ok.mean():.2f}", f"{a.f1.mean():.2f} → {b.f1.mean():.2f}"]
        rows.append(r)
    save("repair_sets", ["Set", "PIX2DB exec", "PIX2DB F1", "8B exec", "8B F1", "2B exec", "2B F1"], rows)

    ab = pd.read_csv(HERE / "cache" / "repair_ablation.csv")
    cfg_order = ["none", "only salvage", "only apostrophes", "only identifiers", "only drop_pk", "only row_fallback",
                 "-salvage", "-apostrophes", "-identifiers", "-drop_pk", "-row_fallback", "full"]
    labels = {"none": "none (raw output)", "full": "all strategies", "only salvage": "only truncation salvage",
              "only apostrophes": "only apostrophe escaping", "only identifiers": "only identifier quoting/renaming",
              "only drop_pk": "only primary-key dropping", "only row_fallback": "only row-by-row insertion",
              "-salvage": "all but truncation salvage", "-apostrophes": "all but apostrophe escaping",
              "-identifiers": "all but identifier quoting/renaming", "-drop_pk": "all but primary-key dropping",
              "-row_fallback": "all but row-by-row insertion"}
    rows = []
    for c in cfg_order:
        if c not in set(ab.config):
            continue
        r = [labels[c]]
        for s in ["pix2db-2b-v2__sql", "Qwen3-VL-8B-Instruct__sql", "Qwen3-VL-2B-Instruct__sql"]:
            x = ab[(ab.config == c) & (ab.system == s)]
            r += [f"{x.exec_ok.mean():.3f}", f"{x.f1.mean():.3f}"]
        rows.append(r)
        x = ab[(ab.config == c) & (ab.system == "pix2db-2b-v2__sql")]
        NUM[f"rs_{c}_exec"], NUM[f"rs_{c}_f1"] = f"{x.exec_ok.mean():.3f}", f"{x.f1.mean():.3f}"
    save("repair_strategies", ["Repair configuration", "PIX2DB exec", "PIX2DB F1", "8B exec", "8B F1", "2B exec",
                               "2B F1"], rows)
    NUM["rs_sets"] = ", ".join(sorted(set(ab["set"])))
    loss = pd.read_csv(HERE / "cache" / "repair_loss.csv")
    rows = []
    for s, lab in [("pix2db-2b-v2__sql", "PIX2DB-2b"), ("Qwen3-VL-8B-Instruct__sql", "Qwen3-VL-8B"),
                   ("Qwen3-VL-2B-Instruct__sql", "Qwen3-VL-2B")]:
        x = loss[loss.system == s]
        resc = x[x.rescued]
        rows.append([lab, str(len(x)), str(int(x.n_repairs.gt(0).sum())), str(len(resc)),
                     f2(resc.f1.mean()) if len(resc) else "–", f2(resc.precision.mean()) if len(resc) else "–",
                     f"{int(x.rows_dropped.sum())} / {int(x.gold_rows.sum()):,}", str(int(x.pk_dropped.sum()))])
        key = s.split("__")[0]
        NUM[f"loss_n_{key}"], NUM[f"loss_rep_{key}"], NUM[f"loss_resc_{key}"] = rows[-1][1], rows[-1][2], rows[-1][3]
        NUM[f"loss_rescf1_{key}"], NUM[f"loss_rescp_{key}"] = rows[-1][4], rows[-1][5]
        NUM[f"loss_rows_{key}"], NUM[f"loss_pk_{key}"] = rows[-1][6], rows[-1][7]
    save("repair_loss", ["Model", "Outputs", "Repaired", "Rescued (raw fails)", "F1 of rescued",
                         "Precision of rescued", "Rows dropped / gold rows", "PKs dropped"], rows)

    # ---------------------------------------------------------------- types and cost (synthetic test)
    rows = []
    for k in ["ours", "html2b", "q8", "h8", "q4", "q2", "dl"]:
        if not has("test", k):
            continue
        g = get("test", k)
        rawk = {"ours": "pix2db-2b-v2__sql", "q8": "Qwen3-VL-8B-Instruct__sql", "q4": "Qwen3-VL-4B-Instruct__sql",
                "q2": "Qwen3-VL-2B-Instruct__sql"}.get(k)
        df = load("test")
        ex = df[df.system == rawk].exec_ok.mean() if rawk else np.nan
        rows.append([SYS[k][1], f2(g.type_acc.mean()), f2(ex), f"{g.n_tokens.mean():.0f}" if g.n_tokens.notna().any()
                     else "–"])
    save("types", ["System", "Type accuracy", "SQL executes (raw)", "Output tokens"], rows)

    (OUT / "numbers.json").write_text(json.dumps(NUM, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(NUM)} numbers, tables in {OUT}")
    for f in sorted(OUT.glob("*.json")):
        if f.name == "numbers.json":
            continue
        t = json.loads(f.read_text(encoding="utf-8"))
        print(f"\n== {f.stem}\n" + " | ".join(t["header"]))
        for r in t["rows"]:
            print(" | ".join(r))


if __name__ == "__main__":
    main()
