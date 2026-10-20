"""Render chart scenes with matplotlib. Gold = (category column, 1–3 numeric series).

If value labels are drawn, values are exactly recoverable; otherwise the scene carries an
absolute numeric tolerance (fraction of the axis range) used by the metric.
"""
from __future__ import annotations

import io
import random

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

from .render import FONTS, IDLIKE, humanize, pick_style  # noqa: E402
from .scene import Column, Scene, Table  # noqa: E402

PALETTES = ["tab10", "Set2", "Dark2", "Paired", "viridis", "Pastel1"]


def chart_scene_from(scene: Scene, rng: random.Random) -> Scene | None:
    """Pick a category column (unique short text) + numeric columns from a single-table scene."""
    t = scene.tables[0]
    n = len(t.rows)
    if not 3 <= n <= 12:
        return None
    cats = [j for j, c in enumerate(t.columns) if c.type == "TEXT"
            and len({r[j] for r in t.rows}) == n and all(r[j] and len(str(r[j])) <= 22 for r in t.rows)]
    nums = [j for j, c in enumerate(t.columns) if c.type in ("INTEGER", "REAL")
            and not IDLIKE.search(c.name) and not any(x in c.name for x in ("card", "zip", "post", "phone", "isbn"))
            and all(isinstance(r[j], (int, float)) and abs(r[j]) < 1e9 for r in t.rows)
            and not all(isinstance(r[j], int) and 1800 <= r[j] <= 2100 for r in t.rows)]
    if not cats or not nums:
        return None
    cj = rng.choice(cats)
    ser = rng.sample(nums, min(len(nums), rng.choice([1, 1, 2, 3])))
    cols = [cj] + ser
    tab = Table(t.name, [t.columns[j] for j in cols], [[r[j] for j in cols] for r in t.rows])
    return Scene(scene.db_id, [tab])


def _fmt_label(v) -> str:
    return str(v) if isinstance(v, int) else repr(v)


def render_chart(scene: Scene, rng: random.Random) -> tuple[Image.Image, dict]:
    t = scene.tables[0]
    cats = [str(r[0]) for r in t.rows]
    series = [[r[k] for r in t.rows] for k in range(1, len(t.columns))]
    names = [c.name for c in t.columns[1:]]
    style = pick_style(rng, 2)
    allpos = all(v >= 0 for s in series for v in s)
    kind = rng.choice(["bar", "barh", "line"] + (["pie"] if len(series) == 1 and allpos else []))
    # labels only when they are short and exact
    exact_ok = all(len(_fmt_label(v)) <= 9 for s in series for v in s)
    labels = exact_ok and (kind == "pie" or rng.random() < 0.6)

    plt.rcParams["font.family"] = rng.choice(FONTS)
    fig, ax = plt.subplots(figsize=(rng.uniform(5.5, 9), rng.uniform(3.8, 5.5)), dpi=rng.choice([90, 110, 130]))
    cmap = plt.get_cmap(rng.choice(PALETTES))
    colors = [cmap(i % cmap.N if cmap.N < 50 else int(i * 255 / max(1, len(series)))) for i in range(max(len(series), len(cats)))]
    x = list(range(len(cats)))
    w = 0.8 / len(series)
    if kind == "pie":
        wedges, *_ = ax.pie(series[0], labels=cats, colors=colors[:len(cats)], startangle=rng.choice([0, 90]),
                            autopct=None)
        for wdg, v in zip(wedges, series[0]):
            ang = (wdg.theta2 + wdg.theta1) / 2
            import math
            ax.annotate(_fmt_label(v), xy=(0.6 * math.cos(math.radians(ang)), 0.6 * math.sin(math.radians(ang))),
                        ha="center", va="center", fontsize=9)
        ax.axis("equal")
    else:
        for k, (s, nm) in enumerate(zip(series, names)):
            if kind == "line":
                ax.plot(x, s, marker="o", color=colors[k], label=humanize(nm, style))
                if labels:
                    for xi, v in zip(x, s):
                        ax.annotate(_fmt_label(v), (xi, v), textcoords="offset points", xytext=(0, 6),
                                    ha="center", fontsize=8)
            elif kind == "bar":
                pos = [xi - 0.4 + w * (k + 0.5) for xi in x]
                bars = ax.bar(pos, s, width=w * 0.95, color=colors[k], label=humanize(nm, style))
                if labels:
                    ax.bar_label(bars, labels=[_fmt_label(v) for v in s], fontsize=8, padding=2)
            else:
                pos = [xi - 0.4 + w * (k + 0.5) for xi in x]
                bars = ax.barh(pos, s, height=w * 0.95, color=colors[k], label=humanize(nm, style))
                if labels:
                    ax.bar_label(bars, labels=[_fmt_label(v) for v in s], fontsize=8, padding=2)
        if kind == "barh":
            ax.set_yticks(x, cats)
            ax.invert_yaxis()
            ax.set_ylabel(humanize(t.columns[0].name, style))
        else:
            ax.set_xticks(x, cats, rotation=rng.choice([0, 30, 45]) if max(map(len, cats)) > 6 else 0,
                          ha="right" if max(map(len, cats)) > 6 else "center")
            ax.set_xlabel(humanize(t.columns[0].name, style))
        if len(series) > 1 or rng.random() < 0.4:
            ax.legend(fontsize=8)
        elif kind != "barh":
            ax.set_ylabel(humanize(names[0], style))
        if rng.random() < 0.5:
            ax.grid(axis="x" if kind == "barh" else "y", alpha=0.3)
        for side in ("top", "right"):
            ax.spines[side].set_visible(rng.random() < 0.3)
    ax.set_title(humanize(t.name, style), fontsize=rng.choice([11, 12, 14]))
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=rng.choice(["white", "#fafafa", "#f5f7fb"]))
    plt.close(fig)
    img = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")

    vals = [abs(v) for s in series for v in s]
    tol = 0.0 if labels else 0.04 * (max(vals) if vals else 1.0)
    return img, {"chart_kind": kind, "value_labels": labels, "num_tol_abs": tol}
