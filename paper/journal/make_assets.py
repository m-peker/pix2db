"""Raster figures for the Word manuscript (300 dpi PNG) + method overview and teaser composites."""
import json
from pathlib import Path

import fitz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image

P = Path(__file__).resolve().parents[1]
OUT = Path(__file__).parent / "fig"
INK, MUTED, BLUE, LBLUE, GRAY = "#0b0b0b", "#52514e", "#2a78d6", "#dbe8f8", "#efeeea"
plt.rcParams.update({"font.family": "serif", "font.size": 9, "pdf.fonttype": 42})

for name in ["renders", "levels", "ablation_data", "ablation_repair", "errors_tabrecset"]:
    doc = fitz.open(P / "figures" / f"{name}.pdf")
    doc[0].get_pixmap(dpi=300).save(OUT / f"{name}.png")

# ---- teaser: input image + produced dump
ex = json.load(open(P.parent / "space_static/examples.json", encoding="utf-8"))
sql = [e for e in ex if e["id"].startswith("02")][0]["sql"]
lines = ["CREATE TABLE users (user_id INTEGER PRIMARY KEY,",
         "  age_category_code TEXT, user_category_code TEXT,",
         "  user_address_id INTEGER, login_name TEXT,",
         "  date_registered TEXT);",
         "CREATE TABLE properties (date_on_market TEXT,",
         "  date_off_market TEXT, owner_user_id INTEGER,",
         "  property_type_code INTEGER,",
         "  FOREIGN KEY (owner_user_id) REFERENCES users(user_id));",
         "INSERT INTO users VALUES",
         "  (10, '18-25', 'Single Mother', 1, 'in', '1980-07-04 17:28:15');",
         "INSERT INTO properties VALUES",
         "  ('2002-01-06 18:44:23', '1978-09-24 13:42:49', 10, 2),",
         "  ('2011-12-15 01:52:28', '2017-05-27 20:55:25', 10, 2),",
         "  ('1976-08-01 00:52:48', '1970-11-22 02:09:50', 10, 2);"]
img = Image.open(P / "figures/teaser_doc.png").convert("RGB")
fig = plt.figure(figsize=(7.2, 2.75))
ax1 = fig.add_axes([0.0, 0.08, 0.42, 0.86]); ax1.imshow(img); ax1.axis("off")
ax1.set_title("(a) input image", fontsize=8.5, color=MUTED)
ax2 = fig.add_axes([0.45, 0.02, 0.55, 0.92]); ax2.axis("off")
ax2.set_title("(b) SQLite dump written by pix2db", fontsize=8.5, color=MUTED)
ax2.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.0,rounding_size=0.02",
                             transform=ax2.transAxes, fc="#f6f6f3", ec="#d6d5cf", lw=0.8))
for i, l in enumerate(lines):
    ax2.text(0.02, 0.95 - i * 0.066, l, family="monospace", fontsize=6.3, color=INK, transform=ax2.transAxes, va="top")
fig.savefig(OUT / "teaser.png", dpi=300, bbox_inches="tight", pad_inches=0.03)
plt.close(fig)

# ---- method overview
fig, ax = plt.subplots(figsize=(7.2, 3.0))
ax.set_xlim(0, 100); ax.set_ylim(0, 42); ax.axis("off")


def box(x, y, w, h, text, fc=GRAY, ec="#b9b8b2", bold=False, size=7.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2", fc=fc, ec=ec, lw=0.9))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=INK,
            fontweight="bold" if bold else "normal", linespacing=1.25)


def arrow(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.0,
                                                                  shrinkA=2, shrinkB=2))


ax.text(0, 40.5, "Training data construction", fontsize=8, color=MUTED, style="italic")
box(0.5, 28.5, 20, 9.5, "Spider SQLite databases\n(146 training DBs)", size=6.9)
box(24.5, 28.5, 21, 9.5, "Scene sampler\none table, two tables,\nparent + child (FK)", size=6.9)
box(49.5, 28.5, 22, 9.5, "Renderer (HTML/CSS,\nmatplotlib): L1-L6,\nreceipts, scan effects", size=6.9)
box(0.5, 15.5, 20, 9.5, "PubTabNet, FinTabNet\n(HTML annotations),\nCORD receipts", size=6.9)
box(24.5, 15.5, 21, 9.5, "Converter: spans to\nrows, flattened headers,\nnumbers normalized", size=6.9)
box(76, 21.5, 23, 10.5, "(image, gold SQLite dump)\n36,589 pairs,\nexecution-checked", fc=LBLUE, ec=BLUE, size=6.9)
arrow(20.8, 33.2, 24.2, 33.2); arrow(45.8, 33.2, 49.2, 33.2); arrow(71.8, 33.2, 75.8, 29.5)
arrow(20.8, 20.2, 24.2, 20.2); arrow(45.8, 20.2, 75.8, 24.5)
ax.text(0, 11.6, "Inference", fontsize=8, color=MUTED, style="italic")
box(0.5, 0.5, 13, 8.5, "document\nimage", size=6.9)
box(18, 0.5, 22, 8.5, "pix2db-2b\nQwen3-VL-2B + LoRA\n(r = 64, merged)", fc=LBLUE, ec=BLUE, size=6.9)
box(44.5, 0.5, 19, 8.5, "verify and repair\n(Algorithm 1)", size=6.9)
box(68, 0.5, 14, 8.5, "SQLite\ndatabase", size=6.9)
box(86.5, 0.5, 12.5, 8.5, "SQL\nqueries", size=6.9)
arrow(13.8, 4.7, 17.7, 4.7); arrow(40.3, 4.7, 44.2, 4.7); arrow(63.8, 4.7, 67.7, 4.7); arrow(82.3, 4.7, 86.2, 4.7)
arrow(87.5, 21.2, 29, 9.3)
ax.text(70, 13.2, "LoRA fine-tuning\n(loss on the SQL answer only)", fontsize=6.6, color=MUTED, ha="left")
fig.savefig(OUT / "method.png", dpi=300, bbox_inches="tight", pad_inches=0.03)
plt.close(fig)
print(sorted(p.name for p in OUT.iterdir()))
