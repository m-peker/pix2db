"""Figure 2: method overview. Two framed panels, box widths fitted to their text, orthogonal connectors only."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).parent / "fig"
INK, MUTED, BLUE, LBLUE, GRAY = "#0b0b0b", "#52514e", "#2a78d6", "#dbe8f8", "#efeeea"
EDGE, LINE, FRAME_FC, FRAME_EC = "#b9b8b2", "#5f5e5a", "#fbfbf9", "#d9d8d2"
plt.rcParams.update({"font.family": "serif", "font.size": 9, "pdf.fonttype": 42})

W_IN, H_IN = 7.2, 3.08
FS, PADX, GAP = 6.5, 1.6, 3.4          # font size, inner horizontal padding, gap between boxes (x units)
fig, ax = plt.subplots(figsize=(W_IN, H_IN))
fig.subplots_adjust(0, 0, 1, 1)
ax.set_xlim(0, 100); ax.set_ylim(0, 100 * H_IN / W_IN); ax.axis("off")
R = fig.canvas.get_renderer()


def text_w(s):
    """Width of a (multi-line) label in data units."""
    t = ax.text(0, 0, s.replace("|", "\n"), fontsize=FS, linespacing=1.3)
    bb = t.get_window_extent(renderer=R).transformed(ax.transData.inverted())
    t.remove()
    return bb.width


def box(x, y, w, h, s, blue=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.8",
                                fc=LBLUE if blue else GRAY, ec=BLUE if blue else EDGE, lw=0.8, zorder=2))
    ax.text(x + w / 2, y + h / 2, s.replace("|", "\n"), ha="center", va="center", fontsize=FS, color=INK,
            linespacing=1.3, zorder=3)


def seg(*pts):
    xs, ys = zip(*pts)
    ax.add_line(Line2D(xs, ys, color=LINE, lw=0.85, solid_joinstyle="miter", solid_capstyle="butt", zorder=1))


def arrow(*pts):  # orthogonal polyline, arrow head on the last segment
    if len(pts) > 2:
        seg(*pts[:-1])
    ax.annotate("", xy=pts[-1], xytext=pts[-2], zorder=1,
                arrowprops=dict(arrowstyle="-|>,head_length=0.42,head_width=0.2", color=LINE, lw=0.85,
                                shrinkA=0, shrinkB=0))


def frame(y0, y1, label):
    ax.add_patch(FancyBboxPatch((0.5, y0), 99.0, y1 - y0, boxstyle="round,pad=0,rounding_size=0.9",
                                fc=FRAME_FC, ec=FRAME_EC, lw=0.7, zorder=0))
    ax.text(2.0, y1 - 1.3, label, fontsize=7.2, color=MUTED, fontweight="bold", va="top")


# ---- labels
SYN = ["Spider SQLite DBs|(146 training DBs)", "Scene sampler:|one table or|parent + child (FK)",
       "Renderer:|L1–L6, receipts,|scan effects"]
REAL = ["PubTabNet, FinTabNet,|CORD annotations", "Converter: spans|to rows, flat|headers, numbers"]
DATA = "36,589 pairs|(image, gold dump),|execution-checked"
LORA = "LoRA fine-tuning|(loss on the|SQL answer)"
INF = ["document|image", "pix2db-2b|Qwen3-VL-2B + LoRA", "verify and repair|(Algorithm 1)", "SQLite|database",
       "SQL|queries"]

H = 9.0                                   # box height (three text lines)
# panel (a): columns 0-1 hold the two source rows, column 2 the renderer, then dataset and LoRA
w = [max(text_w(SYN[0]), text_w(REAL[0])), max(text_w(SYN[1]), text_w(REAL[1])), text_w(SYN[2]),
     text_w(DATA), text_w(LORA)]
w = [v + 2 * PADX for v in w]
BUS = 3.4                                 # extra room for the merge bus before the dataset box
total = sum(w) + GAP * 3 + GAP + BUS
x0 = 2.0 + (96.0 - total) / 2
xs = [x0]
for i in range(1, 5):
    xs.append(xs[-1] + w[i - 1] + GAP + (BUS if i == 3 else 0))
Y1, Y2 = 29.6, 17.8                       # synthetic row, real row (bottom edges)
YA0, YA1 = 15.4, 42.6                     # panel (a) frame
YD = (Y1 + Y2) / 2                        # dataset and LoRA row, centred between the source rows
frame(YA0, YA1, "(a) Training data and fine-tuning")
for i, s in enumerate(SYN):
    box(xs[i], Y1, w[i], H, s)
for i, s in enumerate(REAL):
    box(xs[i], Y2, w[i], H, s)
box(xs[3], YD, w[3], H, DATA, blue=True)
box(xs[4], YD, w[4], H, LORA)
c1, c2, cd = Y1 + H / 2, Y2 + H / 2, YD + H / 2
arrow((xs[0] + w[0], c1), (xs[1], c1)); arrow((xs[1] + w[1], c1), (xs[2], c1))
arrow((xs[0] + w[0], c2), (xs[1], c2))
xm = xs[3] - GAP                          # merge bus
seg((xs[2] + w[2], c1), (xm, c1), (xm, c2), (xs[1] + w[1], c2))
arrow((xm, cd), (xs[3], cd))
arrow((xs[3] + w[3], cd), (xs[4], cd))

# panel (b): inference chain, spread evenly over the width
YB0, YB1 = 0.5, 13.4
frame(YB0, YB1, "(b) Inference")
wi = [text_w(s) + 2 * PADX for s in INF]
g = (96.0 - sum(wi)) / (len(INF) - 1)
xi = [2.0]
for v in wi[:-1]:
    xi.append(xi[-1] + v + g)
HB, YB = 6.6, 1.9
for x, v, s, b in zip(xi, wi, INF, [False, True, False, False, False]):
    box(x, YB, v, HB, s, blue=b)
cb = YB + HB / 2
for i in range(len(INF) - 1):
    arrow((xi[i] + wi[i], cb), (xi[i + 1], cb))
# adapter weights: from LoRA box down to the model box
xl = xs[4] + w[4] / 2
xmdl = xi[1] + wi[1] / 2
yr = YB + HB + 2.4
arrow((xl, YD), (xl, yr), (xmdl, yr), (xmdl, YB + HB))
ax.text((xl + xmdl) / 2, yr + 0.35, "trained adapter, merged into the base model", fontsize=5.9, color=MUTED,
        ha="center", va="bottom", style="italic")
fig.savefig(OUT / "method.png", dpi=300, bbox_inches="tight", pad_inches=0.02)
print("method.png", [round(v, 1) for v in w], round(total, 1))
