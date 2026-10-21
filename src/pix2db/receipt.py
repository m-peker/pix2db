"""Synthetic receipts. Gold = one `items` table (item_name, quantity, [unit_price], price).
Header text, subtotal / tax / total / payment lines are rendered but not stored (derived or not tabular).
"""
from __future__ import annotations

import html
import random

from .scene import Column, Scene, Table

ADJ = ["ICED", "HOT", "FRIED", "GRILLED", "SPICY", "SWEET", "BBQ", "CHEESE", "CHICKEN", "BEEF", "VEGGIE", "MINI",
       "LARGE", "DOUBLE", "CLASSIC", "GREEN", "BLACK", "ORIGINAL", "SPECIAL", "HOUSE", "CRISPY", "SOUR", "LEMON"]
NOUN = ["TEA", "COFFEE", "LATTE", "BURGER", "RICE", "NOODLE", "SOUP", "SALAD", "PIZZA", "TOAST", "CAKE", "WATER",
        "JUICE", "FRIES", "WINGS", "SANDWICH", "DONUT", "BREAD", "MILK", "SODA", "TACO", "WRAP", "STEAK", "PASTA",
        "DUMPLING", "BAO", "SUSHI", "MOCHA", "SMOOTHIE", "COOKIE", "MUFFIN", "NASI GORENG", "MIE AYAM", "BAKSO"]
SUFFIX = ["", "", "", " L", " M", " S", " (R)", " 2PC", " SET", " 500ML", " REG", " XL"]
SHOPS = ["CAFE", "BAKERY", "RESTO", "MART", "KITCHEN", "DINER", "EXPRESS", "HOUSE", "CORNER", "BISTRO"]
FONTS = ["DejaVu Sans Mono", "Liberation Mono", "FreeMono", "Courier 10 Pitch", "Ubuntu Mono", "Noto Sans Mono"]


def item_name(rng: random.Random) -> str:
    n = rng.choice(NOUN)
    if rng.random() < 0.7:
        n = rng.choice(ADJ) + " " + n
    n += rng.choice(SUFFIX)
    return n.title() if rng.random() < 0.2 else n


def sample_receipt(rng: random.Random) -> tuple[Scene, dict]:
    style = rng.choice(["idr", "usd", "eur"])
    n = rng.randint(2, 12)
    unit_col = rng.random() < 0.5
    rows, names = [], set()
    while len(rows) < n:
        nm = item_name(rng)
        if nm in names:
            continue
        names.add(nm)
        q = rng.choice([1, 1, 1, 1, 2, 2, 3, 4, 5])
        if style == "idr":
            up = rng.randint(3, 120) * 1000
        else:
            up = round(rng.randint(50, 3000) / 100, 2)
        price = round(up * q, 2) if isinstance(up, float) else up * q
        rows.append([nm, q, up, price] if unit_col else [nm, q, price])
    cols = [Column("item_name", "TEXT"), Column("quantity", "INTEGER")]
    if unit_col:
        cols.append(Column("unit_price", "REAL" if style != "idr" else "INTEGER"))
    cols.append(Column("price", "REAL" if style != "idr" else "INTEGER"))
    return Scene("receipt", [Table("items", cols, rows)]), {"style": style, "unit_col": unit_col}


def _money(v, style: str) -> str:
    if style == "idr":
        return f"{v:,}".replace(",", rng_sep[0])
    s = f"{v:,.2f}"
    if style == "eur":
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


rng_sep = [","]


def receipt_html(scene: Scene, info: dict, rng: random.Random) -> str:
    t = scene.tables[0]
    style = info["style"]
    rng_sep[0] = rng.choice([",", "."])
    font = rng.choice(FONTS)
    size = rng.randint(12, 15)
    width = rng.randint(260, 380)
    lines = []
    shop = f"{rng.choice(['THE ', '', 'KOPI ', 'TOKO '])}{rng.choice(ADJ)} {rng.choice(SHOPS)}"
    lines.append(f"<div class='c b'>{html.escape(shop)}</div>")
    if rng.random() < 0.8:
        lines.append(f"<div class='c'>Jl. {rng.choice(['Merdeka', 'Sudirman', 'Main St', 'Oak Ave'])} No.{rng.randint(1, 200)}</div>")
    lines.append(f"<div>{rng.randint(1, 28):02d}/{rng.randint(1, 12):02d}/20{rng.randint(15, 25)} "
                 f"{rng.randint(7, 22):02d}:{rng.randint(0, 59):02d}</div>")
    if rng.random() < 0.6:
        lines.append(f"<div>No: {rng.randint(100000, 999999)}  Table {rng.randint(1, 40)}</div>")
    lines.append("<div class='hr'></div>")
    fmt = rng.choice(["qty_first", "name_then_qty", "qty_x_unit"])
    unit_idx = 2 if info["unit_col"] else None
    for r in t.rows:
        nm, q, price = r[0], r[1], r[-1]
        up = r[unit_idx] if unit_idx else None
        if fmt == "qty_first":
            mid = f"{_money(up, style)}" if up is not None else ""
            lines.append(f"<div class='row'><span>{q} {html.escape(nm)}</span><span>{mid}</span>"
                         f"<span>{_money(price, style)}</span></div>")
        elif fmt == "name_then_qty":
            lines.append(f"<div>{html.escape(nm)}</div>")
            u = f" x {_money(up, style)}" if up is not None else ""
            lines.append(f"<div class='row'><span>&nbsp;&nbsp;{q}{u}</span><span>{_money(price, style)}</span></div>")
        else:
            u = f"@{_money(up, style)}" if up is not None else ""
            lines.append(f"<div class='row'><span>{html.escape(nm)}</span><span>{_money(price, style)}</span></div>")
            lines.append(f"<div class='row'><span>&nbsp;&nbsp;{q} {u}</span><span></span></div>")
        if rng.random() < 0.12:
            lines.append(f"<div>&nbsp;&nbsp;{rng.choice(['=*LARGE*==', '- less sugar', '+ extra cheese', 'NO ICE'])}</div>")
    lines.append("<div class='hr'></div>")
    sub = sum(r[-1] for r in t.rows)
    sub = round(sub, 2) if isinstance(sub, float) else sub
    tax = round(sub * 0.1, 2) if isinstance(sub, float) else int(sub * 0.1)
    tot = round(sub + tax, 2) if isinstance(sub, float) else sub + tax
    for label, v in [("SUBTOTAL", sub), (rng.choice(["TAX 10%", "PB1", "VAT"]), tax), ("TOTAL", tot)]:
        cls = " b" if label == "TOTAL" else ""
        lines.append(f"<div class='row{cls}'><span>{label}</span><span>{_money(v, style)}</span></div>")
    if rng.random() < 0.7:
        lines.append(f"<div class='row'><span>{rng.choice(['CASH', 'CARD', 'DEBIT', 'QRIS'])}</span>"
                     f"<span>{_money(tot, style)}</span></div>")
    if rng.random() < 0.6:
        lines.append(f"<div class='c'>{rng.choice(['THANK YOU', 'Terima Kasih', 'See you again!'])}</div>")
    css = f"""body{{margin:0;background:#fff}}
#page{{display:inline-block;width:{width}px;padding:18px 14px;background:{rng.choice(['#fffef8', '#fbfbf7', '#ffffff'])};
 font-family:'{font}';font-size:{size}px;color:{rng.choice(['#222', '#333', '#3a2f6b', '#2b2b55'])};line-height:1.35}}
.c{{text-align:center}} .b{{font-weight:bold}} .hr{{border-top:1px dashed #555;margin:6px 0}}
.row{{display:flex;justify-content:space-between;gap:8px}}"""
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body><div id='page'>{''.join(lines)}</div></body></html>"
