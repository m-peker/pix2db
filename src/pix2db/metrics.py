"""Name-agnostic comparison of a predicted database against the gold scene.

Matching: tables (Hungarian on matched cells) → columns (Hungarian on value overlap)
→ rows (Hungarian on equal aligned cells). Values are compared after lenient
normalization (separators, currency, date format); whether a value was *stored*
with the right type is scored separately (type accuracy).
"""
from __future__ import annotations

import datetime as dt
import re
from collections import Counter

import numpy as np
from scipy.optimize import linear_sum_assignment

from .dbio import DBTable
from .scene import Scene

CURRENCY = re.compile(r"^(?:USD|EUR|GBP|US\$|[$€£¥₺])\s*|\s*(?:USD|EUR|GBP|[$€£¥₺])$", re.I)
DATE_FORMATS = ["%Y-%m-%d", "%b %d, %Y", "%d %B %Y", "%B %d, %Y", "%d %b %Y", "%Y/%m/%d", "%d.%m.%Y"]


def norm(v):
    if v is None:
        return None
    if isinstance(v, bool):
        v = int(v)
    if isinstance(v, (int, float)):
        return ("n", round(float(v), 6))
    s = " ".join(str(v).split()).strip().strip("'\"")
    if s == "" or s.upper() in ("NULL", "NONE", "NAN", "-"):
        return None
    t = CURRENCY.sub("", s)
    neg = t.startswith("-")
    t2 = t[1:] if neg else t
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?|\d+(\.\d+)?|\.\d+", t2):
        try:
            f = float(t2.replace(",", ""))
            return ("n", round(-f if neg else f, 6))
        except ValueError:
            pass
    for fmt in DATE_FORMATS:
        try:
            return ("d", dt.datetime.strptime(s, fmt).date().isoformat())
        except ValueError:
            continue
    return ("s", s.casefold())


def affinity(decl: str) -> str:
    """SQLite type affinity rules, collapsed to NUM / TEXT."""
    d = decl.upper()
    if "INT" in d:
        return "NUM"
    if any(x in d for x in ("CHAR", "CLOB", "TEXT")):
        return "TEXT"
    if any(x in d for x in ("REAL", "FLOA", "DOUB", "NUMERIC", "DECIMAL")):
        return "NUM"
    return "TEXT" if d == "" else "NUM"


def stored_numeric(values) -> bool:
    vals = [v for v in values if v is not None]
    return bool(vals) and all(isinstance(v, (int, float)) for v in vals)


def eq(a, b, tol: float = 0.0) -> bool:
    if a is None or b is None:
        return False
    if tol and a[0] == "n" and b[0] == "n":
        return abs(a[1] - b[1]) <= tol
    return a == b


def _overlap(gc, pc, tol: float) -> int:
    if not tol:
        cg = Counter(x for x in gc if x is not None)
        cp = Counter(x for x in pc if x is not None)
        return sum((cg & cp).values())
    pool = [x for x in pc if x is not None]
    hits = 0
    for x in gc:
        for k, y in enumerate(pool):
            if eq(x, y, tol):
                hits += 1
                pool.pop(k)
                break
    return hits


def _align(gold_cols, pred_cols, tol: float = 0.0):
    """gold_cols/pred_cols: list of lists of normalized values (column-major)."""
    G, P = len(gold_cols), len(pred_cols)
    if G == 0 or P == 0:
        return []
    m = np.zeros((G, P))
    for i, gc in enumerate(gold_cols):
        for j, pc in enumerate(pred_cols):
            m[i, j] = _overlap(gc, pc, tol)
    r, c = linear_sum_assignment(-m)
    return [(i, j) for i, j in zip(r, c) if m[i, j] > 0]


def _pair_score(gold_rows, pred_rows, tol: float = 0.0):
    """Return matched-cell count and details for one gold table vs one pred table."""
    gcols = list(map(list, zip(*gold_rows))) if gold_rows else []
    pcols = list(map(list, zip(*pred_rows))) if pred_rows else []
    colmap = _align(gcols, pcols, tol)
    if not colmap:
        return 0, colmap, []
    R, S = len(gold_rows), len(pred_rows)
    m = np.zeros((R, S))
    for a in range(R):
        for b in range(S):
            m[a, b] = sum(1 for i, j in colmap if eq(gold_rows[a][i], pred_rows[b][j], tol))
    r, c = linear_sum_assignment(-m)
    rowmap = [(a, b) for a, b in zip(r, c)]
    return int(m[r, c].sum()), colmap, rowmap


def score(scene: Scene, pred: list[DBTable], num_tol_abs: float = 0.0) -> dict:
    gold = [[[norm(v) for v in row] for row in t.rows] for t in scene.tables]
    predn = [[[norm(v) for v in row] for row in t.rows] for t in pred]
    gold_cells = sum(sum(v is not None for v in row) for t in gold for row in t)
    pred_cells = sum(sum(v is not None for v in row) for t in predn for row in t)

    res = {"n_pred_tables": len(pred), "n_gold_tables": len(gold), "gold_cells": gold_cells,
           "pred_cells": pred_cells}
    if not pred or gold_cells == 0:
        res.update(matched=0, precision=0.0, recall=0.0, f1=0.0, table_exact=0.0, type_acc=None,
                   rowcount_ok=0.0, fk_recall=None if not scene.foreign_keys else 0.0)
        return res

    pairs = {}
    m = np.zeros((len(gold), len(pred)))
    for gi, g in enumerate(gold):
        for pi, p in enumerate(predn):
            pairs[gi, pi] = _pair_score(g, p, num_tol_abs)
            m[gi, pi] = pairs[gi, pi][0]
    r, c = linear_sum_assignment(-m)
    tmatch = {gi: pi for gi, pi in zip(r, c) if m[gi, pi] > 0}

    matched = int(sum(m[gi, pi] for gi, pi in tmatch.items()))
    prec = matched / pred_cells if pred_cells else 0.0
    rec = matched / gold_cells
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0

    exact, rowcount_ok, type_hits, type_n = 0, 0, 0, 0
    for gi, gt in enumerate(scene.tables):
        g_cells = sum(v is not None for row in gold[gi] for v in row)
        if gi not in tmatch:
            continue
        pi = tmatch[gi]
        pt = pred[pi]
        _, colmap, _ = pairs[gi, pi]
        if len(pt.rows) == len(gt.rows):
            rowcount_ok += 1
            if m[gi, pi] == g_cells and len(pt.columns) == len(gt.columns):
                exact += 1
        for i, j in colmap:
            gnum = gt.columns[i].type in ("INTEGER", "REAL")
            pcol = [row[j] for row in pt.rows]
            # correct if declared affinity and stored values both agree with gold numeric-ness
            pnum = affinity(pt.decl_types[j]) == "NUM" and stored_numeric(pcol)
            ptxt = affinity(pt.decl_types[j]) == "TEXT" or not stored_numeric(pcol)
            type_hits += int(pnum if gnum else ptxt)
            type_n += 1

    fk_recall = None
    if scene.foreign_keys:
        name_of = {gi: pred[pi].name for gi, pi in tmatch.items()}
        idx = {t.name: k for k, t in enumerate(scene.tables)}
        hits = 0
        for fk in scene.foreign_keys:
            ci, pi_ = idx[fk.child_table], idx[fk.parent_table]
            if ci in tmatch and pi_ in tmatch:
                child_pred = pred[tmatch[ci]]
                if any(ptab.lower() == name_of[pi_].lower() for _, ptab, _ in child_pred.fks):
                    hits += 1
        fk_recall = hits / len(scene.foreign_keys)

    res.update(matched=matched, precision=prec, recall=rec, f1=f1,
               table_exact=exact / len(gold), rowcount_ok=rowcount_ok / len(gold),
               type_acc=(type_hits / type_n) if type_n else None, fk_recall=fk_recall)
    return res
