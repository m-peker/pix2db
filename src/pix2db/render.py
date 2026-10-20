"""Render a Scene to HTML at a given difficulty level, then to PNG.

Rule: every displayed value must be losslessly recoverable to the gold value
(no rounding, no truncation). Formatting only adds separators, currency symbols,
or rewrites pure ISO dates in an unambiguous long form.

Rendering may reorder a table's rows/columns IN PLACE so that the gold scene follows
the visual order (the training target then reads top-to-bottom, left-to-right).
"""
from __future__ import annotations

import datetime as dt
import html
import io
import random
import re

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from .scene import Scene, Table

MONEY_HINTS = ("price", "cost", "amount", "salary", "budget", "revenue", "fee", "payment", "sales",
               "income", "charge", "total", "value", "money", "balance", "profit", "pay")
FONTS = ["DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono", "Liberation Sans", "Liberation Serif",
         "Liberation Mono", "FreeSans", "FreeSerif", "Bitstream Charter", "Roboto", "Open Sans", "Lato",
         "Carlito", "Caladea", "Ubuntu", "Noto Sans", "Noto Serif"]
GROUP_LABELS_NUM = ["Figures", "Metrics", "Values", "Statistics", "Numbers"]
GROUP_LABELS_TXT = ["Details", "Info", "General", "Description", "Identity"]
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
QTY_HINTS = ("quantity", "qty", "count", "units", "number_of", "num_of", "amount", "hours", "points")
IDLIKE = re.compile(r"(^|_)(id|year|yr|code|no|num|number|zip|phone|season)($|_)")


def humanize(name: str, style: str) -> str:
    words = name.replace("_", " ").split()
    if style == "title":
        return " ".join(w.capitalize() for w in words)
    if style == "sentence":
        s = " ".join(words)
        return s[:1].upper() + s[1:]
    if style == "upper":
        return " ".join(words).upper()
    return name


def pick_style(rng: random.Random, level: int) -> str:
    return "raw" if level <= 1 else rng.choice(["title", "sentence", "upper", "raw"])


class Formatter:
    """Per-column display formatting, fixed for one image."""

    def __init__(self, table: Table, rng: random.Random, level: int):
        self.fmt = []
        for j, c in enumerate(table.columns):
            f = {"thousands": False, "currency": None, "date": None}
            if level >= 2:
                if c.type in ("INTEGER", "REAL"):
                    vals = [r[j] for r in table.rows if isinstance(r[j], (int, float))]
                    yearlike = bool(vals) and all(isinstance(v, int) and 1800 <= v <= 2100 for v in vals)
                    f["thousands"] = not IDLIKE.search(c.name) and not yearlike and rng.random() < 0.6
                    if any(h in c.name for h in MONEY_HINTS) and rng.random() < 0.7:
                        f["currency"] = rng.choice(["$", "€", "£", "USD "])
                if c.type == "TEXT" and rng.random() < 0.7:
                    f["date"] = rng.choice(["%b %d, %Y", "%d %B %Y", "%B %d, %Y", "%d %b %Y"])
            self.fmt.append(f)

    def __call__(self, j: int, v) -> str:
        f = self.fmt[j]
        if v is None:
            return ""
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if isinstance(v, int):
                s = f"{v:,}" if f["thousands"] else str(v)
            else:
                s = repr(v)
                if f["thousands"] and abs(v) >= 1000 and "e" not in s:
                    ip, _, fp = s.partition(".")
                    s = f"{int(ip):,}" + ("." + fp if fp else "")
            if f["currency"]:
                s = ("-" + f["currency"] + s[1:]) if s.startswith("-") else f["currency"] + s
            return s
        s = str(v)
        if f["date"] and ISO_DATE.match(s):
            try:
                return dt.date.fromisoformat(s).strftime(f["date"])
            except ValueError:
                return s
        return s


def _css(rng: random.Random, level: int) -> str:
    font = rng.choice(FONTS)
    size = rng.randint(12, 17)
    if level == 1:
        return f"""body{{margin:0;background:#fff;font-family:'{font}';font-size:{size}px;color:#000}}
#page{{display:inline-block;padding:16px}}
table{{border-collapse:collapse;margin-bottom:14px}} td,th{{border:1px solid #444;padding:4px 8px;text-align:left}}
th{{font-weight:bold}}"""
    hdr_bg = rng.choice(["#1f4e79", "#2e7d32", "#6a1b9a", "#37474f", "#b71c1c", "#e0e0e0", "#fff3cd", "#ffffff",
                         "#004d40", "#4a148c", "#f57c00"])
    hdr_fg = "#111" if hdr_bg in ("#e0e0e0", "#fff3cd", "#ffffff") else "#fff"
    zebra = rng.choice(["#f5f5f5", "#eef4fb", "#fafafa", "transparent"])
    border = rng.choice(["1px solid #999", "1px solid #ddd", "none", "2px solid #333"])
    hb = rng.choice(["1px solid #ccc", "none"])
    pad = f"{rng.randint(3, 9)}px {rng.randint(6, 14)}px"
    align = rng.choice(["left", "center"])
    bg = rng.choice(["#ffffff", "#fdfcf7", "#f7f9fc"])
    return f"""body{{margin:0;background:{bg};font-family:'{font}';font-size:{size}px;color:#222}}
#page{{display:inline-block;padding:{rng.randint(14, 32)}px;background:{bg};max-width:1350px}}
h1{{font-size:{size + 6}px;margin:0 0 10px 0}} h2{{font-size:{size + 3}px;margin:16px 0 8px 0}}
table{{border-collapse:collapse;border:{border};margin-bottom:14px}}
th{{background:{hdr_bg};color:{hdr_fg};padding:{pad};text-align:{align};border:{hb}}}
td{{padding:{pad};border-bottom:1px solid #ddd;border-left:{hb};border-right:{hb};text-align:{align};vertical-align:middle}}
tbody tr:nth-child(even) td{{background:{zebra}}}
tfoot td{{font-weight:bold;border-top:2px solid #333}}
.num{{text-align:right}}
.side th{{text-align:left}}
.form{{display:grid;grid-template-columns:repeat({rng.choice([1, 2, 3])},auto);gap:6px 28px;margin-bottom:12px;
  padding:10px 14px;border:1px solid #bbb;border-radius:{rng.choice([0, 4, 8])}px}}
.form .k{{color:#555;font-size:{size - 1}px}} .form .v{{font-weight:bold}}
.doc-head{{display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid {hdr_bg};
  margin-bottom:12px;padding-bottom:6px}}
.logo{{width:42px;height:42px;border-radius:50%;background:{hdr_bg};opacity:.8}}
.note{{color:#777;font-size:{size - 2}px;margin-top:4px}}"""


def _reorder(t: Table, order: list[int]):
    t.columns = [t.columns[j] for j in order]
    t.rows = [[r[j] for j in order] for r in t.rows]


def _transposed_html(t: Table, rng: random.Random, level: int, title: str | None) -> str:
    """Records as columns, attributes as rows (common in spec sheets / comparisons)."""
    fmt = Formatter(t, rng, level)
    style = pick_style(rng, level)
    out = [f"<h2>{html.escape(title)}</h2>"] if title else []
    out.append('<table class="side"><tbody>')
    for j, c in enumerate(t.columns):
        cells = "".join(f"<td>{html.escape(fmt(j, r[j]))}</td>" for r in t.rows)
        out.append(f"<tr><th>{html.escape(humanize(c.name, style))}</th>{cells}</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def _table_html(t: Table, rng: random.Random, level: int, title: str | None = None,
                total_row: bool = False) -> str:
    if level >= 3 and len(t.rows) <= 8 and len(t.columns) <= 6 and rng.random() < 0.15:
        return _transposed_html(t, rng, level, title)

    order = list(range(len(t.columns)))
    group_col = None
    super_hdr = None
    if level >= 3:
        # Option A: merged cells on a repeated grouping column.
        cands = [j for j, c in enumerate(t.columns)
                 if len({r[j] for r in t.rows}) < len(t.rows) and all(r[j] not in (None, "") for r in t.rows)]
        if cands and rng.random() < 0.75:
            group_col = rng.choice(cands)
            order = [group_col] + [j for j in order if j != group_col]
        # Option B: two-level header grouping text vs numeric columns.
        if rng.random() < 0.6 or group_col is None:
            num = [j for j in order if t.columns[j].type != "TEXT" and j != group_col]
            txt = [j for j in order if t.columns[j].type == "TEXT" and j != group_col]
            if num and txt:
                lead = [group_col] if group_col is not None else []
                order = lead + txt + num
                super_hdr = ([(None, 1)] if lead else []) + [
                    (rng.choice(GROUP_LABELS_TXT), len(txt)), (rng.choice(GROUP_LABELS_NUM), len(num))]
    _reorder(t, order)
    if group_col is not None:
        group_col = 0
        t.rows.sort(key=lambda r: str(r[0]))

    fmt = Formatter(t, rng, level)
    style = pick_style(rng, level)
    heads = [humanize(c.name, style) for c in t.columns]
    out = [f"<h2>{html.escape(title)}</h2>"] if title else []
    out.append("<table><thead>")
    if super_hdr:
        out.append("<tr>")
        for label, span in super_hdr:
            if label is None:
                out.append(f'<th rowspan="2">{html.escape(heads[0])}</th>')
            else:
                out.append(f'<th colspan="{span}">{html.escape(label)}</th>')
        out.append("</tr><tr>")
        start = 1 if super_hdr[0][0] is None else 0
        out += [f"<th>{html.escape(h)}</th>" for h in heads[start:]]
        out.append("</tr>")
    else:
        out.append("<tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in heads) + "</tr>")
    out.append("</thead><tbody>")
    rows = t.rows
    i = 0
    while i < len(rows):
        span = 1
        if group_col is not None:
            while i + span < len(rows) and rows[i + span][0] == rows[i][0]:
                span += 1
        for s in range(span):
            r = rows[i + s]
            cells = []
            for j in range(len(t.columns)):
                if j == group_col:
                    if s == 0:
                        cells.append(f'<td rowspan="{span}">{html.escape(fmt(j, r[j]))}</td>')
                    continue
                cls = ' class="num"' if t.columns[j].type != "TEXT" and level >= 2 else ""
                cells.append(f"<td{cls}>{html.escape(fmt(j, r[j]))}</td>")
            out.append("<tr>" + "".join(cells) + "</tr>")
        i += span
    out.append("</tbody>")
    if total_row:
        # A derived "Total" line under the first non-id numeric column. It is NOT part of the gold data.
        nums = [j for j, c in enumerate(t.columns) if c.type != "TEXT" and not IDLIKE.search(c.name)
                and any(h in c.name for h in MONEY_HINTS + QTY_HINTS)
                and all(isinstance(r[j], (int, float)) for r in rows)]
        if nums and len(t.columns) >= 2:
            j = nums[-1]
            tot = sum(r[j] for r in rows)
            tot = round(tot, 6) if isinstance(tot, float) else tot
            label_col = 0 if j != 0 else 1
            cells = []
            for k in range(len(t.columns)):
                if k == label_col:
                    cells.append(f"<td>{rng.choice(['Total', 'TOTAL', 'Sum', 'Grand total'])}</td>")
                elif k == j:
                    cells.append(f'<td class="num">{html.escape(fmt(j, tot))}</td>')
                else:
                    cells.append("<td></td>")
            out.append("<tfoot><tr>" + "".join(cells) + "</tr></tfoot>")
    out.append("</table>")
    return "".join(out)


def _form_html(t: Table, rng: random.Random, level: int) -> str:
    fmt = Formatter(t, rng, level)
    style = pick_style(rng, max(level, 2))
    r = t.rows[0]
    sep = rng.choice([":", "", " -"])
    items = "".join(
        f'<div><span class="k">{html.escape(humanize(c.name, style))}{sep}</span> '
        f'<span class="v">{html.escape(fmt(j, r[j]))}</span></div>'
        for j, c in enumerate(t.columns))
    return f'<div class="form">{items}</div>'


def scene_html(scene: Scene, level: int, rng: random.Random) -> str:
    """level: 1..4 layout difficulty (5 = scan is applied on top of the image later)."""
    body = []
    style = pick_style(rng, level)
    if scene.foreign_keys and len(scene.tables) == 2:
        parent, child = scene.tables
        body.append(f'<div class="doc-head"><h1>{html.escape(humanize(parent.name, style))} '
                    f'{rng.choice(["Record", "Summary", "Sheet", "Report", "Details", "Statement"])}</h1>'
                    f'<div class="logo"></div></div>')
        body.append(_form_html(parent, rng, level))
        body.append(_table_html(child, rng, max(level, 3) if level >= 4 else level,
                                title=humanize(child.name, style), total_row=rng.random() < 0.35))
        if rng.random() < 0.4:
            body.append(f'<div class="note">{rng.choice(["Generated automatically.", "Page 1 of 1",
                                                         "Confidential", "All amounts as recorded."])}</div>')
    else:
        for t in scene.tables:
            title = humanize(t.name, style) if (level >= 2 and rng.random() < 0.7) or len(scene.tables) > 1 else None
            body.append(_table_html(t, rng, level, title, total_row=level >= 3 and rng.random() < 0.15))
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{_css(rng, level)}</style></head>"
            f"<body><div id='page'>{''.join(body)}</div></body></html>")


def scan_augment(img: Image.Image, rng: random.Random) -> Image.Image:
    """Cheap 'photographed / scanned document' degradation."""
    img = img.convert("RGB")
    w, h = img.size
    pad = int(0.04 * max(w, h))
    canvas = Image.new("RGB", (w + 2 * pad, h + 2 * pad), (235, 233, 228))
    canvas.paste(img, (pad, pad))
    img = canvas.rotate(rng.uniform(-2.5, 2.5), resample=Image.BICUBIC, expand=True, fillcolor=(210, 208, 204))
    a = np.asarray(img).astype(np.float32)
    gx = np.linspace(rng.uniform(0.85, 1.0), rng.uniform(0.95, 1.05), a.shape[1])[None, :, None]
    gy = np.linspace(rng.uniform(0.9, 1.05), rng.uniform(0.85, 1.0), a.shape[0])[:, None, None]
    a = a * gx * gy
    a += np.random.default_rng(rng.randint(0, 2**31)).normal(0, rng.uniform(3, 9), a.shape)
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if rng.random() < 0.7:
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 0.9)))
    img = ImageEnhance.Contrast(img).enhance(rng.uniform(0.8, 1.1))
    if rng.random() < 0.5:
        img = img.convert("L").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=rng.randint(45, 80))
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


class Renderer:
    """Playwright-based HTML → PNG (one browser, reused)."""

    def __init__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self._page = self._browser.new_page(viewport={"width": 1400, "height": 900}, device_scale_factor=1)

    def png(self, html_str: str) -> Image.Image:
        self._page.set_content(html_str)
        data = self._page.locator("#page").screenshot()
        return Image.open(io.BytesIO(data)).convert("RGB")

    def close(self):
        self._browser.close()
        self._pw.stop()


def render_scene(renderer: Renderer, scene: Scene, level: int, rng: random.Random) -> tuple[Image.Image, str]:
    html_str = scene_html(scene, min(level, 4), rng)
    img = renderer.png(html_str)
    if level >= 5:
        img = scan_augment(img, rng)
    return img, html_str
