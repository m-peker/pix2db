"""Query-execution equivalence: run the same aggregate queries on the gold and the predicted database.

Queries are generated from the gold schema (no hand-written SQL): row counts, SUM/MIN/MAX of numeric
columns, COUNT(DISTINCT) of text columns, and for each foreign key a join count and a per-parent child
count. Gold names are mapped to predicted names with the alignment found by metrics.score, so the check
does not depend on naming. A query counts as correct when both results agree (numbers within 1e-6 relative).
"""
from __future__ import annotations

import sqlite3

from .scene import Scene


def _q(n: str) -> str:
    return '"' + n.replace('"', '""') + '"'


def gold_queries(scene: Scene) -> list[tuple[str, list[tuple[str, str | None]]]]:
    """Return (template, [(table, column)]) pairs; {0},{1}.. are filled with quoted names."""
    out = []
    for t in scene.tables:
        out.append(("SELECT COUNT(*) FROM {0}", [(t.name, None)]))
        for c in t.columns:
            if c.type in ("INTEGER", "REAL"):
                for f in ("SUM", "MIN", "MAX"):
                    out.append((f"SELECT {f}(CAST({{1}} AS REAL)) FROM {{0}}", [(t.name, None), (t.name, c.name)]))
            else:
                out.append(("SELECT COUNT(DISTINCT {1}) FROM {0}", [(t.name, None), (t.name, c.name)]))
    for fk in scene.foreign_keys:
        out.append(("SELECT COUNT(*) FROM {0} JOIN {1} ON {0}.{2} = {1}.{3}",
                    [(fk.child_table, None), (fk.parent_table, None), (fk.child_table, fk.child_column),
                     (fk.parent_table, fk.parent_column)]))
    return out


def _fill(tpl, refs, names):
    vals = []
    for t, c in refs:
        if t not in names:
            return None
        pt, cols = names[t]
        if c is None:
            vals.append(_q(pt))
        elif c in cols:
            vals.append(_q(cols[c]))
        else:
            return None
    return tpl.format(*vals)


def _run(con, sql):
    try:
        return con.execute(sql).fetchall()
    except sqlite3.Error:
        return None


def _same(a, b, tol: float = 0.0) -> bool:
    if a is None or b is None or len(a) != len(b):
        return False
    for ra, rb in zip(a, b):
        for x, y in zip(ra, rb):
            if x is None or y is None:
                if x is not y:
                    return False
            elif isinstance(x, (int, float)) and isinstance(y, (int, float)):
                if abs(x - y) > max(tol, 1e-6 * max(1.0, abs(x))):
                    return False
            elif str(x) != str(y):
                return False
    return True


def query_equivalence(scene: Scene, gold_con: sqlite3.Connection, pred_con: sqlite3.Connection,
                      align: dict, num_tol_abs: float = 0.0) -> tuple[int, int]:
    """Return (n_equal, n_queries). Unmapped tables/columns count as wrong.
    For unlabeled charts (num_tol_abs > 0) a numeric result may differ by num_tol_abs per row."""
    nrows = max([len(t.rows) for t in scene.tables] + [1])
    ident = {t.name: (t.name, {c.name: c.name for c in t.columns}) for t in scene.tables}
    ok = n = 0
    for tpl, refs in gold_queries(scene):
        g = _run(gold_con, _fill(tpl, refs, ident))
        if g is None:
            continue
        n += 1
        sql = _fill(tpl, refs, align)
        ok += int(sql is not None and _same(g, _run(pred_con, sql), num_tol_abs * nrows))
    return ok, n
