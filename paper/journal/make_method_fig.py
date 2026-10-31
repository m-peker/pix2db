"""Figure 2: method overview drawn on a grid with orthogonal connectors only."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).parent / "fig" / "method.png"
INK, MUTED, EDGE, FILL = "#1d1d1b", "#5c5b57", "#a9a8a2", "#f2f1ed"
BLUE_E, BLUE_F = "#2a78d6", "#e3eefb"
plt.rcParams.update({"font.family": "serif", "font.size": 8})

fig, ax = plt.subplots(figsize=(7.2, 4.1))
ax.set_xlim(0, 100)
ax.set_ylim(0, 57)
ax.axis("off")

H = 7.0                      # box height
ROW = [45, 35, 25, 15, 5]    # box bottoms, top to bottom
A, B = (1, 28.5), (31, 59.5)  # training columns (x0, x1)
C = (71, 99)                 # inference column


def box(x0, x1, row, text, blue=False, bold_first=False):
    y = ROW[row]
    ax.add_patch(FancyBboxPatch((x0, y), x1 - x0, H, boxstyle="round,pad=0,rounding_size=1.1",
                                fc=BLUE_F if blue else FILL, ec=BLUE_E if blue else EDGE, lw=0.9))
    lines = text.split("\n")
    if bold_first and len(lines) > 1:
        ax.text((x0 + x1) / 2, y + H * 0.66, lines[0], ha="center", va="center", fontsize=7.8, color=INK,
                fontweight="bold")
        ax.text((x0 + x1) / 2, y + H * 0.30, "\n".join(lines[1:]), ha="center", va="center", fontsize=6.7,
                color=MUTED, linespacing=1.15)
    else:
        ax.text((x0 + x1) / 2, y + H / 2, text, ha="center", va="center", fontsize=7.6, color=INK, linespacing=1.15)


def down(x, r_from, r_to):
    ax.annotate("", xy=(x, ROW[r_to] + H), xytext=(x, ROW[r_from]),
                arrowprops=dict(arrowstyle="-|>,head_length=0.45,head_width=0.22", color=MUTED, lw=0.9,
                                shrinkA=0, shrinkB=0))


mid = lambda c: (c[0] + c[1]) / 2  # noqa: E731

# panel titles
ax.text(A[0], 54.3, "(a) Training data and fine-tuning", fontsize=8.4, color=INK, fontweight="bold")
ax.text(C[0], 54.3, "(b) Inference", fontsize=8.4, color=INK, fontweight="bold")

# (a) two sources that meet in the gold pairs
box(*A, 0, "Spider databases\n146 training databases", bold_first=True)
box(*A, 1, "Scene sampler\n1–2 tables or parent + child", bold_first=True)
box(*A, 2, "Renderer\nlevels L1–L6, receipts, scans", bold_first=True)
box(*B, 0, "Real annotations\nPubTabNet · FinTabNet · CORD", bold_first=True)
box(*B, 1, "Converter\nspans → rows, flat headers", bold_first=True)
box(A[0], B[1], 3, "Gold pairs\n36,589 (image, SQLite dump), each checked by execution", bold_first=True)
box(A[0], B[1], 4, "LoRA fine-tuning of Qwen3-VL-2B\nloss on the SQL answer only", blue=True, bold_first=True)
down(mid(A), 0, 1)
down(mid(A), 1, 2)
down(mid(A), 2, 3)
down(mid(B), 0, 1)
down(mid(B), 1, 3)
down(mid((A[0], B[1])), 3, 4)

# (b) inference chain
box(*C, 0, "Document image", )
box(*C, 1, "PIX2DB-2b\nwrites the SQL dump", blue=True, bold_first=True)
box(*C, 2, "Verify and repair\nAlgorithm 1", bold_first=True)
box(*C, 3, "SQLite database\ntables, types, keys", bold_first=True)
box(*C, 4, "SQL queries")
for r in range(4):
    down(mid(C), r, r + 1)

# orthogonal connector: fine-tuned weights -> PIX2DB-2b
xg = 65.2
y_from = ROW[4] + H / 2
y_to = ROW[1] + H / 2
ax.plot([B[1], xg, xg], [y_from, y_from, y_to], color=BLUE_E, lw=0.9, ls=(0, (3, 2)))
ax.annotate("", xy=(C[0], y_to), xytext=(xg, y_to),
            arrowprops=dict(arrowstyle="-|>,head_length=0.45,head_width=0.22", color=BLUE_E, lw=0.9,
                            ls=(0, (3, 2)), shrinkA=0, shrinkB=0))
ax.text(xg + 0.8, (y_from + y_to) / 2, "fine-tuned\nweights", fontsize=6.8, color=BLUE_E, va="center", ha="left")

fig.savefig(OUT, dpi=300, bbox_inches="tight", pad_inches=0.04)
print("saved", OUT)
