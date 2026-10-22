"""Every number, table and plot in the paper comes from this script.

Inputs : results/v1/*_scores.csv, results/v2/*_scores.csv, paper/cache/meta_all.parquet,
         paper/cache/runs/eval_runs_v2/*/*.jsonl, preview/ + space/examples/ images
Outputs: paper/figures/*.pdf, paper/tables/*.tex, paper/numbers.tex (\newcommand macros)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
FIG, TAB = ROOT / "paper/figures", ROOT / "paper/tables"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(42)

# validated categorical palette (dataviz reference instance, light mode), fixed order
C = {"ours": "#2a78d6", "8b_sql": "#eb6834", "8b_html": "#1baf7a", "4b": "#eda100", "2b": "#e87ba4",
     "v1": "#8fb8ea"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "serif", "font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                     "axes.spines.right": False, "legend.frameon": False, "pdf.fonttype": 42,
                     "savefig.bbox": "tight", "savefig.pad_inches": 0.02})
SHORT = {"ours": "pix2db-2b (ours)", "8b_sql": "8B → SQL", "8b_html": "8B → HTML → SQLite", "4b": "4B → SQL",
         "2b": "2B → SQL (base)"}

SYS = {  # label, csv system name, color
    "ours": ("pix2db-2b (ours)", "pix2db-2b-v2__sql+repair"),
    "v1": ("pix2db-2b, synthetic only", "pix2db-2b-v1__sql+repair"),
    "8b_sql": ("Qwen3-VL-8B → SQL", "Qwen3-VL-8B-Instruct__sql+repair"),
    "8b_html": ("Qwen3-VL-8B → HTML → SQLite", "Qwen3-VL-8B-Instruct__html"),
    "4b": ("Qwen3-VL-4B → SQL", "Qwen3-VL-4B-Instruct__sql+repair"),
    "2b": ("Qwen3-VL-2B → SQL (base)", "Qwen3-VL-2B-Instruct__sql+repair"),
}
SETS = [  # key, label, metric
    ("test", "Synthetic", "table_exact"),
    ("real_pubtabnet", "PubTabNet", "f1"),
    ("real_fintabnet", "FinTabNet", "f1"),
    ("real_cord", "CORD", "recall"),
    ("test_receipt", "Synth. receipts", "recall"),
    ("unseen_tabrecset", "TabRecSet", "f1"),
]
LEVELS = {1: "clean", 2: "styled", 3: "hierarchical", 4: "document", 5: "scan", 6: "chart"}

scores = {s: pd.read_csv(ROOT / f"results/v2/{s}_scores.csv") for s, _, _ in SETS}
nums: dict[str, str] = {}


def col(df, key, metric):
    return df[df.system == SYS[key][1]].set_index("id")[metric]


def boot_ci(x, n=2000):
    x = np.asarray(x, float)
    m = RNG.choice(x, (n, len(x))).mean(1)
    return x.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5)


def paired_p(a, b, n=5000):
    """one-sided paired bootstrap: P(mean(a-b) <= 0)"""
    d = np.asarray(a, float) - np.asarray(b, float)
    m = RNG.choice(d, (n, len(d))).mean(1)
    return (m <= 0).mean()


def macro(name, val):
    nums[name] = val


# ---------------------------------------------------------------- main table with CIs
order = ["ours", "8b_sql", "8b_html", "4b", "2b"]
lines = []
best_rival = {}
for key in order:
    cells = []
    for s, _, metric in SETS:
        m, lo, hi = boot_ci(col(scores[s], key, metric).values)
        cells.append((m, lo, hi))
    lines.append((key, cells))
for j, (s, _, metric) in enumerate(SETS):
    vals = {k: c[j][0] for k, c in lines}
    rival = max((k for k in order if k != "ours"), key=lambda k: vals[k])
    best_rival[s] = rival
    a, b = col(scores[s], "ours", metric), col(scores[s], rival, metric)
    a, b = a.align(b, join="inner")
    p = paired_p(a, b) if vals["ours"] > vals[rival] else paired_p(b, a)
    macro(f"p{s.replace('_', '')}", f"{p:.3f}")
fk = scores["test"][scores["test"].fk_recall.notna()]
fkv = {k: fk[fk.system == SYS[k][1]].fk_recall.mean() for k in order}

hdr = " & ".join(f"\\makecell{{{lab}\\\\[-1pt]\\scriptsize {('exact' if m == 'table_exact' else m)}}}"
                 for _, lab, m in SETS)
out = ["\\begin{tabular}{l" + "c" * (len(SETS) + 1) + "}", "\\toprule",
       f"System & {hdr} & \\makecell{{FK\\\\[-1pt]\\scriptsize recall}} \\\\", "\\midrule"]
for key, cells in lines:
    row = [SYS[key][0].replace("→", "$\\to$")]
    for j, (m, lo, hi) in enumerate(cells):
        best = m >= max(c[j][0] for _, c in lines) - 1e-9
        v = f"{m:.2f}"
        v = f"\\textbf{{{v}}}" if best else v
        row.append(f"{v}\\,{{\\tiny[{lo:.2f},{hi:.2f}]}}")
    f = fkv[key]
    row.append(f"\\textbf{{{f:.2f}}}" if f >= max(fkv.values()) - 1e-9 else f"{f:.2f}")
    out.append(" & ".join(row) + " \\\\")
    if key == "ours":
        out.append("\\midrule")
out += ["\\bottomrule", "\\end{tabular}"]
(TAB / "main.tex").write_text("\n".join(out), encoding="utf-8")

for key, cells in lines:
    for j, (s, _, _) in enumerate(SETS):
        macro(f"{key.replace('_', '')}{s.replace('_', '')}", f"{cells[j][0]:.2f}")
for k in order:
    macro(f"fk{k.replace('_', '')}", f"{fkv[k]:.2f}")

# ---------------------------------------------------------------- per-level figure (synthetic test)
t = scores["test"]
fig, ax = plt.subplots(figsize=(7.0, 2.3))
keys = ["ours", "8b_sql", "8b_html", "4b", "2b"]
w = 0.16
for i, k in enumerate(keys):
    v = [t[(t.system == SYS[k][1]) & (t.level == lv)].table_exact.mean() for lv in LEVELS]
    ax.bar(np.arange(6) + (i - 2) * w, v, w * 0.9, color=C[k], label=SHORT[k], zorder=3)
ax.set_xticks(range(6), [f"L{lv}\n{nm}" for lv, nm in LEVELS.items()])
ax.set_ylabel("table exact match")
ax.set_ylim(0, 1)
ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
ax.legend(ncol=5, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=7.2, handlelength=1, columnspacing=1.2)
fig.tight_layout()
fig.savefig(FIG / "levels.pdf")
plt.close(fig)
lv_ours = {lv: t[(t.system == SYS["ours"][1]) & (t.level == lv)].table_exact.mean() for lv in LEVELS}
lv_html = {lv: t[(t.system == SYS["8b_html"][1]) & (t.level == lv)].table_exact.mean() for lv in LEVELS}
for lv in LEVELS:
    macro(f"lvours{'abcdef'[lv - 1]}", f"{lv_ours[lv]:.2f}")
    macro(f"lvhtml{'abcdef'[lv - 1]}", f"{lv_html[lv]:.2f}")

# ---------------------------------------------------------------- data ablation figure (v1 vs v2)
fig, ax = plt.subplots(figsize=(3.4, 2.3))
sets = SETS
x = np.arange(len(sets))
for i, (k, lab) in enumerate([("v1", "synthetic only (v1)"), ("ours", "+ real & receipts (v2)")]):
    v = [col(scores[s], k, m).mean() for s, _, m in sets]
    ax.bar(x + (i - 0.5) * 0.36, v, 0.33, color=C[k], label=lab, zorder=3)
    for xi, vi in zip(x, v):
        ax.text(xi + (i - 0.5) * 0.36, vi + 0.015, f"{vi:.2f}"[1:] if round(vi, 2) < 1 else "1.0", ha="center",
                fontsize=5.6, color=MUTED)
ax.set_xticks(x, [lab for _, lab, _ in sets], rotation=25, ha="right")
ax.set_ylim(0, 1.12)
ax.set_yticks([0, .25, .5, .75, 1])
ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.2), ncol=2, fontsize=7)
fig.tight_layout()
fig.savefig(FIG / "ablation_data.pdf")
plt.close(fig)
for s, _, m in sets:
    macro(f"vone{s.replace('_', '')}", f"{col(scores[s], 'v1', m).mean():.2f}")

# ---------------------------------------------------------------- repair ablation (all SQL systems, all sets pooled)
rows = []
for s, lab, m in SETS:
    df = scores[s]
    for k in ["ours", "8b_sql", "4b", "2b"]:
        base = SYS[k][1].replace("+repair", "")
        for variant, name in [("raw", base), ("rep", base + "+repair")]:
            d = df[df.system == name]
            rows.append(dict(set=s, sys=k, variant=variant, exec=d.exec_ok.mean(), f1=d.f1.mean(), n=len(d)))
rp = pd.DataFrame(rows)
rp["exec_w"], rp["f1_w"] = rp.exec * rp.n, rp.f1 * rp.n
agg = rp.groupby(["sys", "variant"])[["exec_w", "f1_w", "n"]].sum()
pooled = pd.DataFrame({"exec": agg.exec_w / agg.n, "f1": agg.f1_w / agg.n}).unstack()
fig, axes = plt.subplots(1, 2, figsize=(3.4, 1.75), sharey=True)
ylabels = [SYS[k][0].split(" (")[0].replace(" → SQL", "") for k in ["ours", "8b_sql", "4b", "2b"]]
for ax, met, lab in [(axes[0], "exec", "SQL executes"), (axes[1], "f1", "cell F1")]:
    for yi, k in enumerate(["ours", "8b_sql", "4b", "2b"]):
        a, b = pooled.loc[k, (met, "raw")], pooled.loc[k, (met, "rep")]
        ax.plot([a, b], [yi, yi], color=GRID, lw=2.2, zorder=1)
        ax.scatter([a], [yi], s=16, color="white", edgecolor=C[k], lw=1.2, zorder=3)
        ax.scatter([b], [yi], s=18, color=C[k], zorder=4)
    ax.set_title(lab, fontsize=8)
    ax.set_xlim(0.2 if met == "f1" else 0.6, 1.0)
    ax.grid(axis="x", color=GRID, lw=0.6, zorder=0)
axes[0].set_yticks(range(4), ylabels)
axes[0].invert_yaxis()
fig.text(0.99, 0.01, "○ raw   ● after repair", ha="right", fontsize=6.5, color=MUTED)
fig.tight_layout()
fig.savefig(FIG / "ablation_repair.pdf")
plt.close(fig)
for k in ["ours", "8b_sql", "4b", "2b"]:
    for met in ["exec", "f1"]:
        for v in ["raw", "rep"]:
            macro(f"rep{k.replace('_', '')}{met}{v}", f"{pooled.loc[k, (met, v)]:.2f}")

# ---------------------------------------------------------------- per-set repair table
out = ["\\begin{tabular}{lcccccc}", "\\toprule",
       "& \\multicolumn{2}{c}{pix2db-2b} & \\multicolumn{2}{c}{Qwen3-VL-8B} & \\multicolumn{2}{c}{Qwen3-VL-2B}\\\\",
       "\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\\cmidrule(lr){6-7}",
       "Set & exec & F1 & exec & F1 & exec & F1 \\\\", "\\midrule"]
for s, lab, _ in SETS:
    r = [lab]
    for k in ["ours", "8b_sql", "2b"]:
        q = rp[(rp.set == s) & (rp.sys == k)].set_index("variant")
        r += [f"{q.loc['raw', 'exec']:.2f}$\\to${q.loc['rep', 'exec']:.2f}", f"{q.loc['raw', 'f1']:.2f}$\\to${q.loc['rep', 'f1']:.2f}"]
    out.append(" & ".join(r) + " \\\\")
out += ["\\bottomrule", "\\end{tabular}"]
(TAB / "repair.tex").write_text("\n".join(out), encoding="utf-8")

# ---------------------------------------------------------------- types, exec, efficiency on the synthetic test
out = ["\\begin{tabular}{lcccc}", "\\toprule",
       "System & types & exec & tokens & s/img \\\\", "\\midrule"]
for k in ["ours", "8b_sql", "8b_html", "4b", "2b"]:
    d = t[t.system == SYS[k][1]]
    d_raw = t[t.system == SYS[k][1].replace("+repair", "")]
    label = SHORT[k].replace("→", r"$\to$")
    ex = "--" if k == "8b_html" else f"{d_raw.exec_ok.mean():.2f}"
    out.append(f"{label} & {d.type_acc.mean():.2f} & {ex} & {d.n_tokens.mean():.0f} & {d.seconds.mean():.2f} " + r"\\")
out += ["\\bottomrule", "\\end{tabular}"]
(TAB / "types.tex").write_text("\n".join(out), encoding="utf-8")
macro("tokours", f"{t[t.system == SYS['ours'][1]].n_tokens.mean():.0f}")
macro("tokhtml", f"{t[t.system == SYS['8b_html'][1]].n_tokens.mean():.0f}")

# ---------------------------------------------------------------- data statistics
meta = pd.read_parquet(ROOT / "paper/cache/meta_all.parquet").reset_index(drop=True)


def scene_stats(s):
    sc = json.loads(s)
    ts = sc["tables"]
    return pd.Series({"tables": len(ts), "rows": sum(len(x["rows"]) for x in ts),
                      "cols": np.mean([len(x["columns"]) for x in ts]),
                      "cells": sum(len(x["rows"]) * len(x["columns"]) for x in ts), "fk": len(sc.get("foreign_keys", []))})


st = meta.join(meta.scene.apply(scene_stats))
names = {"train": "train (synthetic)", "train_real": "train (real)", "train_receipt": "train (receipts)",
         "validation": "validation", "test": "test (synthetic)", "test_receipt": "test (receipts)",
         "real_pubtabnet": "PubTabNet (val)", "real_fintabnet": "FinTabNet (val)", "real_cord": "CORD (test)",
         "unseen_tabrecset": "TabRecSet (unseen)"}
out = ["\\begin{tabular}{lrrrrr}", "\\toprule",
       "Split & images & tables/img & rows & cols & with FK \\\\", "\\midrule"]
for sp, nm in names.items():
    g = st[st.split == sp]
    out.append(f"{nm} & {len(g):,} & {g.tables.mean():.2f} & {g.rows.mean():.1f} & {g.cols.mean():.1f} & "
               f"{(g.fk > 0).mean() * 100:.0f}\\% \\\\")
out += ["\\bottomrule", "\\end{tabular}"]
(TAB / "data.tex").write_text("\n".join(out), encoding="utf-8")
macro("ntrainused", "36{,}589")

# ---------------------------------------------------------------- error analysis on TabRecSet (unseen)
runs = ROOT / "paper/cache/runs/eval_runs_v2/unseen_tabrecset"
tr = scores["unseen_tabrecset"]
um = st[st.split == "unseen_tabrecset"].set_index("id")


def keyvalue(scene_json):
    tb = json.loads(scene_json)["tables"][0]
    if len(tb["columns"]) != 2:
        return False
    first = [str(r[0] or "") for r in tb["rows"]]
    return sum(f.strip().endswith(":") for f in first) >= max(2, len(first) // 2)


um["kv"] = um.scene.apply(keyvalue)
cat_rows = []
for k in ["ours", "8b_html", "8b_sql"]:
    d = tr[tr.system == SYS[k][1]].set_index("id").join(um[["kv", "rows"]])
    gold_rows = d["rows"]

    def cat(r):
        if r.f1 >= 0.9:
            return "correct (F1 ≥ 0.9)"
        if r.kv:
            return "key-value layout"
        if r.n_pred_tables == 0 or r.f1 == 0:
            return "no usable output"
        if not r.rowcount_ok:
            return "row segmentation"
        return "cell content"
    d["cat"] = d.apply(cat, axis=1)
    cat_rows.append(d.cat.value_counts().rename(k))
cats = pd.concat(cat_rows, axis=1).fillna(0).astype(int)
corder = ["correct (F1 ≥ 0.9)", "cell content", "row segmentation", "key-value layout", "no usable output"]
cats = cats.reindex(corder).fillna(0).astype(int)
macro("nkv", str(int(um.kv.sum())))
for k in cats.columns:
    for c in corder:
        macro(f"err{k.replace('_', '')}{''.join(ch for ch in c.split()[0] if ch.isalpha())}", str(int(cats.loc[c, k])))
kv_ids = um[um.kv].index
for k in ["ours", "8b_html"]:
    d = tr[tr.system == SYS[k][1]].set_index("id")
    macro(f"kvfone{k.replace('_', '')}", f"{d.loc[d.index.isin(kv_ids), 'f1'].mean():.2f}")
    macro(f"nokvfone{k.replace('_', '')}", f"{d.loc[~d.index.isin(kv_ids), 'f1'].mean():.2f}")

fig, ax = plt.subplots(figsize=(3.4, 1.9))
shades = ["#2a78d6", "#8fb8ea", "#c9dcf3", "#eda100", "#b9b8b2"]
labels = {"ours": "pix2db-2b", "8b_html": "8B → HTML", "8b_sql": "8B → SQL"}
for yi, k in enumerate(cats.columns):
    left = 0
    for c, sh in zip(corder, shades):
        v = cats.loc[c, k]
        ax.barh(yi, v, left=left, color=sh, edgecolor="white", lw=1, height=0.62,
                label=c if yi == 0 else None)
        if v >= 9:
            ax.text(left + v / 2, yi, str(v), ha="center", va="center", fontsize=6.3,
                    color="white" if sh in ("#2a78d6",) else INK)
        left += v
ax.set_yticks(range(len(cats.columns)), [labels[k] for k in cats.columns])
ax.invert_yaxis()
ax.set_xlim(0, 150)
ax.set_xlabel("TabRecSet tables (n = 150)", fontsize=7)
ax.legend(ncol=3, fontsize=6, loc="upper center", bbox_to_anchor=(0.4, -0.42), handlelength=0.9, columnspacing=0.8)
fig.tight_layout()
fig.savefig(FIG / "errors_tabrecset.pdf")
plt.close(fig)

# ---------------------------------------------------------------- render gallery (data figure)
picks = [("preview/validation/L1_clean", "L1 clean"), ("preview/validation/L2_styled", "L2 styled"),
         ("preview/validation/L3_hierarchical", "L3 hierarchical"), ("preview/validation/L4_document", "L4 document"),
         ("preview/validation/L5_scan", "L5 scan"), ("preview/validation/L6_chart", "L6 chart")]
ims = []
for d, lab in picks + [("space/examples/05_receipt.png", "receipt")]:
    p = ROOT / d
    f = p if p.is_file() else sorted(p.glob("*.png"))[1]
    ims.append((Image.open(f).convert("RGB"), lab))
rows_ = [ims[:4], ims[4:]]  # two rows; equal height within a row, true aspect ratios
W, gap, title_h = 7.0, 0.08, 0.16
heights = [(W - gap * (len(r) - 1)) / sum(im.width / im.height for im, _ in r) for r in rows_]
H = sum(heights) + title_h * 2 + 0.1
fig = plt.figure(figsize=(W, H))
axes, y = [], H
for r, h in zip(rows_, heights):
    y -= h + title_h
    x = 0.0
    for im, lab in r:
        w_ = h * im.width / im.height
        ax = fig.add_axes([x / W, y / H, w_ / W, h / H])
        axes.append((ax, im, lab))
        x += w_ + gap
for ax, im, lab in axes:
    ax.imshow(im)
    ax.set_title(lab, fontsize=7.5, pad=2)
    ax.axis("off")
fig.savefig(FIG / "renders.pdf", dpi=240)
plt.close(fig)

# ---------------------------------------------------------------- macros
DIG = dict(zip("0123456789", ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]))


def texname(k):  # LaTeX macro names may contain letters only
    return "".join(DIG.get(ch, ch) for ch in k if ch.isalnum())


(ROOT / "paper/numbers.tex").write_text(
    "".join(f"\\newcommand{{\\N{texname(k)}}}{{{v}}}\n" for k, v in sorted(nums.items())), encoding="utf-8")
print(f"{len(nums)} macros; best rivals: {best_rival}")
print(cats)
