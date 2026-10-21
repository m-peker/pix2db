"""Convert a real annotated HTML table (PubTabNet / FinTabNet) into a gold Table.

Conventions (same as the synthetic data):
- multi-row headers with colspans are flattened: "2019 → Revenue" becomes column `2019_revenue`
- rowspan cells in the body are repeated in every row they cover
- body colspans (section rows like "Assets") make the table ambiguous → rejected
- numbers: thousand separators / currency removed, accounting negatives "(1,234)" → -1234,
  a lone dash "—" → NULL; a column is numeric only if every non-empty value parses
"""
from __future__ import annotations

import re

from .scene import Column, Table, infer_type, snake

DASHES = str.maketrans({"−": "-", "–": "-", "—": "-", " ": " ", " ": " ", " ": " "})
EMPTY = {"", "-", "--", "—", "–", "n/a", "N/A"}


def clean_text(s: str | None) -> str | None:
    if s is None:
        return None
    s = re.sub(r"<[^>]+>", "", s)
    s = " ".join(s.split())
    return s or None


def parse_number(s: str):
    """Return int/float for plain or formatted numbers, else None."""
    t = s.translate(DASHES).strip()
    t = re.sub(r"^(US\$|\$|€|£|USD)\s*", "", t)
    neg = False
    if re.fullmatch(r"\(\s*[\d.,]+\s*\)", t):
        neg, t = True, t.strip("() ")
    if t.startswith("-"):
        neg, t = True, t[1:].strip()
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", t):
        t = t.replace(",", "")
    if re.fullmatch(r"(0|[1-9]\d*)", t):
        v = int(t)
    elif re.fullmatch(r"(0|[1-9]\d*)?\.\d+", t):
        v = float(t)
    else:
        return None
    return -v if neg else v


def _grid(rows) -> list[list[str | None]] | None:
    """rows: list of <tr> elements → rectangular grid with spans expanded (None where a span was empty)."""
    grid: dict[tuple[int, int], str | None] = {}
    width = 0
    for r, tr in enumerate(rows):
        c = 0
        for cell in tr.find_all(["td", "th"]):
            while (r, c) in grid:
                c += 1
            rs, cs = int(cell.get("rowspan", 1) or 1), int(cell.get("colspan", 1) or 1)
            txt = clean_text(cell.get_text(" "))
            for dr in range(rs):
                for dc in range(cs):
                    grid[(r + dr, c + dc)] = txt
            c += cs
            width = max(width, c)
    if not grid:
        return None
    height = max(r for r, _ in grid) + 1
    return [[grid.get((r, c)) for c in range(width)] for r in range(height)]


def html_to_table(html: str, name: str = "table_1", max_rows: int = 30, max_cols: int = 10) -> Table | None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    thead, tbody = soup.find("thead"), soup.find("tbody")
    if not thead or not tbody:
        return None
    body_rows = tbody.find_all("tr")
    if any(int(c.get("colspan", 1) or 1) > 1 for tr in body_rows for c in tr.find_all(["td", "th"])):
        return None  # section/sub-total rows spanning columns: no unambiguous relational form
    head = _grid(thead.find_all("tr"))
    body = _grid(body_rows)
    if not head or not body or len(head[0]) != len(body[0]):
        return None
    ncols = len(head[0])
    if not (2 <= ncols <= max_cols and 2 <= len(body) <= max_rows):
        return None
    names = []
    for c in range(ncols):
        parts = []
        for r in range(len(head)):
            v = head[r][c]
            if v and (not parts or parts[-1] != v):
                parts.append(v)
        nm = snake(" ".join(parts)) if parts else ("item" if c == 0 else "")
        if not nm or nm == "col":
            return None
        if nm[0].isdigit():
            nm = "c_" + nm
        names.append(nm)
    seen = {}
    for k, nm in enumerate(names):
        seen[nm] = seen.get(nm, 0) + 1
        if seen[nm] > 1:
            names[k] = f"{nm}_{seen[nm]}"
    # values
    cols = []
    for c in range(ncols):
        raw = [None if (body[r][c] is None or body[r][c].translate(DASHES).strip() in EMPTY) else body[r][c]
               for r in range(len(body))]
        nums = [parse_number(v) if v is not None else None for v in raw]
        if any(v is not None for v in raw) and all(n is not None for v, n in zip(raw, nums) if v is not None):
            col = nums
        else:
            col = raw
        cols.append(col)
    rows = [list(r) for r in zip(*cols)]
    rows = [r for r in rows if any(v is not None for v in r)]
    if len(rows) < 2:
        return None
    return Table(name, [Column(nm, infer_type([r[k] for r in rows])) for k, nm in enumerate(names)], rows)
