"""Sample "scenes" (gold mini-databases) from Spider SQLite files.

A scene is one table, or a parent/child pair linked by a foreign key, with a small
sample of rows and columns. The scene is the gold answer for one rendered image.
"""
from __future__ import annotations

import random
import re
import sqlite3
from dataclasses import dataclass, field, asdict
from pathlib import Path

MAX_CELL_CHARS = 40


@dataclass
class Column:
    name: str
    type: str  # INTEGER | REAL | TEXT (inferred from values, not from Spider's declared type)


@dataclass
class Table:
    name: str
    columns: list[Column]
    rows: list[list]
    primary_key: str | None = None


@dataclass
class ForeignKey:
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str


@dataclass
class Scene:
    db_id: str
    tables: list[Table]
    foreign_keys: list[ForeignKey] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Scene":
        return Scene(
            db_id=d["db_id"],
            tables=[Table(t["name"], [Column(**c) for c in t["columns"]], t["rows"], t.get("primary_key"))
                    for t in d["tables"]],
            foreign_keys=[ForeignKey(**f) for f in d.get("foreign_keys", [])],
        )

    def to_sql(self) -> str:
        """Gold dump in the exact target format the model should produce."""
        out = []
        fk_by_child = {}
        for fk in self.foreign_keys:
            fk_by_child.setdefault(fk.child_table, []).append(fk)
        for t in self.tables:
            defs = []
            for c in t.columns:
                d = f"  {q(c.name)} {c.type}"
                if c.name == t.primary_key:
                    d += " PRIMARY KEY"
                defs.append(d)
            for fk in fk_by_child.get(t.name, []):
                defs.append(f"  FOREIGN KEY ({q(fk.child_column)}) REFERENCES "
                            f"{q(fk.parent_table)}({q(fk.parent_column)})")
            out.append(f"CREATE TABLE {q(t.name)} (\n" + ",\n".join(defs) + "\n);")
        for t in self.tables:
            cols = ", ".join(q(c.name) for c in t.columns)
            vals = ",\n".join(f"({', '.join(sql_literal(v) for v in r)})" for r in t.rows)
            out.append(f"INSERT INTO {q(t.name)} ({cols}) VALUES\n{vals};")
        return "\n".join(out)


SQLITE_KEYWORDS = set("""ABORT ACTION ADD AFTER ALL ALTER ALWAYS ANALYZE AND AS ASC ATTACH AUTOINCREMENT BEFORE BEGIN
BETWEEN BY CASCADE CASE CAST CHECK COLLATE COLUMN COMMIT CONFLICT CONSTRAINT CREATE CROSS CURRENT CURRENT_DATE
CURRENT_TIME CURRENT_TIMESTAMP DATABASE DEFAULT DEFERRABLE DEFERRED DELETE DESC DETACH DISTINCT DO DROP EACH ELSE END
ESCAPE EXCEPT EXCLUDE EXCLUSIVE EXISTS EXPLAIN FAIL FILTER FIRST FOLLOWING FOR FOREIGN FROM FULL GENERATED GLOB GROUP
GROUPS HAVING IF IGNORE IMMEDIATE IN INDEX INDEXED INITIALLY INNER INSERT INSTEAD INTERSECT INTO IS ISNULL JOIN KEY
LAST LEFT LIKE LIMIT MATCH MATERIALIZED NATURAL NO NOT NOTHING NOTNULL NULL NULLS OF OFFSET ON OR ORDER OTHERS OUTER
OVER PARTITION PLAN PRAGMA PRECEDING PRIMARY QUERY RAISE RANGE RECURSIVE REFERENCES REGEXP REINDEX RELEASE RENAME
REPLACE RESTRICT RETURNING RIGHT ROLLBACK ROW ROWS SAVEPOINT SELECT SET TABLE TEMP TEMPORARY THEN TIES TO TRANSACTION
TRIGGER UNBOUNDED UNION UNIQUE UPDATE USING VACUUM VALUES VIEW VIRTUAL WHEN WHERE WINDOW WITH WITHOUT""".split())


def q(name: str) -> str:
    """Quote an identifier only when needed (leading digit, odd chars, or SQL keyword)."""
    if re.fullmatch(r"[a-z_][a-z0-9_]*", name) and name.upper() not in SQLITE_KEYWORDS:
        return name
    return '"' + name.replace('"', '""') + '"'


def sql_literal(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def snake(name: str) -> str:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s).strip("_").lower()
    return s or "col"


NUMERIC_STR = re.compile(r"^-?(0|[1-9]\d*)(\.\d+)?$")


def coerce_column(values: list) -> list:
    """Spider often stores numbers as TEXT ('2016'). Convert a column whose non-empty values are
    all plain numeric strings (no leading zeros) to int/float, so the gold types are sensible."""
    floats = [v for v in values if isinstance(v, float)]
    if floats and all(v.is_integer() and abs(v) < 1e15 for v in floats)             and all(v is None or isinstance(v, (int, float)) for v in values):
        return [int(v) if isinstance(v, float) else v for v in values]
    strs = [v for v in values if isinstance(v, str) and v != ""]
    if not strs or not all(NUMERIC_STR.match(v) for v in strs):
        return values
    if any(v not in (None, "") and not isinstance(v, (str, int, float)) for v in values):
        return values
    out = []
    for v in values:
        if isinstance(v, str) and v != "":
            v = float(v) if "." in v else int(v)
        elif v == "":
            v = None
        out.append(v)
    return out


def infer_type(values: list) -> str:
    vals = [v for v in values if v is not None and v != ""]
    if not vals:
        return "TEXT"
    if all(isinstance(v, int) and not isinstance(v, bool) for v in vals):
        return "INTEGER"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
        return "REAL"
    return "TEXT"


def _usable_columns(cur, table: str) -> list[tuple[str, str]]:
    cols = cur.execute(f'PRAGMA table_info("{table}")').fetchall()
    return [(c[1], (c[2] or "").upper()) for c in cols if "BLOB" not in (c[2] or "").upper()]


def _clean_rows(rows: list[tuple]) -> list[list]:
    out = []
    for r in rows:
        rr = []
        for v in r:
            if isinstance(v, bytes):
                v = None
            if isinstance(v, str):
                v = " ".join(v.split()) or None
            if isinstance(v, float) and v.is_integer() and abs(v) < 1e12:
                pass  # keep float; type inference decides
            rr.append(v)
        out.append(rr)
    return out


def _good_column(values: list) -> bool:
    nonnull = [v for v in values if v not in (None, "")]
    if len(nonnull) < max(2, len(values) // 2):
        return False
    return all(len(str(v)) <= MAX_CELL_CHARS for v in nonnull)


def _build_table(name: str, colnames: list[str], rows: list[list], pk: str | None, rng: random.Random,
                 n_cols: tuple[int, int], keep: list[str] = ()) -> Table | None:
    keep_idx = [i for i, c in enumerate(colnames) if c in keep]
    good = [i for i in range(len(colnames)) if _good_column([r[i] for r in rows])]
    good = sorted(set(good) | set(keep_idx))
    if len(good) < n_cols[0]:
        return None
    k = rng.randint(n_cols[0], min(n_cols[1], len(good)))
    optional = [i for i in good if i not in keep_idx]
    chosen = keep_idx + rng.sample(optional, max(0, k - len(keep_idx)))
    chosen = sorted(set(chosen))
    cols = [colnames[i] for i in chosen]
    data = [[r[i] for i in chosen] for r in rows]
    # dedupe rows, drop rows that are mostly empty
    seen, uniq = set(), []
    for r in data:
        key = tuple(r)
        if key in seen or sum(v in (None, "") for v in r) > len(r) // 2:
            continue
        seen.add(key)
        uniq.append(r)
    if len(uniq) < 3:
        return None
    for j in range(len(cols)):
        col = coerce_column([r[j] for r in uniq])
        for r, v in zip(uniq, col):
            r[j] = v
    columns = [Column(snake(c), infer_type([r[j] for r in uniq])) for j, c in enumerate(cols)]
    if len({c.name for c in columns}) != len(columns):
        return None
    pk_s = snake(pk) if pk and pk in cols else None
    if pk_s:
        k = [c.name for c in columns].index(pk_s)
        if len({r[k] for r in uniq}) != len(uniq) or any(r[k] is None for r in uniq):
            pk_s = None
    return Table(snake(name), columns, uniq, pk_s)


def sample_single(db_path: Path, rng: random.Random, n_rows=(4, 12), n_cols=(3, 7)) -> Scene | None:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.text_factory = lambda b: b.decode("utf-8", errors="replace")
    try:
        cur = con.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                  if not r[0].startswith("sqlite_")]
        rng.shuffle(tables)
        for t in tables:
            cols = _usable_columns(cur, t)
            if len(cols) < n_cols[0]:
                continue
            names = [c[0] for c in cols]
            q = ", ".join(f'"{c}"' for c in names)
            rows = cur.execute(f'SELECT {q} FROM "{t}" LIMIT 2000').fetchall()
            if len(rows) < n_rows[0]:
                continue
            rows = rng.sample(rows, min(len(rows), rng.randint(*n_rows)))
            pks = [c[1] for c in cur.execute(f'PRAGMA table_info("{t}")') if c[5] > 0]
            pk = pks[0] if len(pks) == 1 else None  # composite keys are not declared
            tab = _build_table(t, names, _clean_rows(rows), pk, rng, n_cols)
            if tab:
                return Scene(db_path.parent.name, [tab])
        return None
    except sqlite3.Error:
        return None
    finally:
        con.close()


def sample_multi(db_path: Path, rng: random.Random, n_rows=(3, 8), n_cols=(2, 5)) -> Scene | None:
    """Two unrelated tables from the same database on one page (no FK)."""
    a = sample_single(db_path, rng, n_rows, n_cols)
    for _ in range(4):
        b = sample_single(db_path, rng, n_rows, n_cols)
        if a and b and b.tables[0].name != a.tables[0].name:
            return Scene(a.db_id, [a.tables[0], b.tables[0]])
    return None


def sample_parent_child(db_path: Path, rng: random.Random, n_child=(3, 15), n_cols=(3, 6)) -> Scene | None:
    """One parent row (rendered as a form header) + its child rows (rendered as an item table)."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.text_factory = lambda b: b.decode("utf-8", errors="replace")
    try:
        cur = con.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                  if not r[0].startswith("sqlite_")]
        fks = []
        for t in tables:
            for f in cur.execute(f'PRAGMA foreign_key_list("{t}")').fetchall():
                # (id, seq, table, from, to, ...)
                if f[2] and f[3] and f[4] and f[2] != t:
                    fks.append((t, f[3], f[2], f[4]))
        rng.shuffle(fks)
        for child, ccol, parent, pcol in fks:
            parent_real = next((x for x in tables if x.lower() == parent.lower()), None)
            if not parent_real:
                continue
            try:
                keys = cur.execute(
                    f'SELECT "{ccol}", COUNT(*) c FROM "{child}" GROUP BY "{ccol}" '
                    f'HAVING c BETWEEN {n_child[0]} AND 40').fetchall()
            except sqlite3.Error:
                continue
            if not keys:
                continue
            key = rng.choice(keys)[0]
            pcols = [c[0] for c in _usable_columns(cur, parent_real)]
            ccols = [c[0] for c in _usable_columns(cur, child)]
            if pcol not in pcols or ccol not in ccols or len(pcols) < 2 or len(ccols) < 3:
                continue
            prow = cur.execute(
                f'SELECT {", ".join(chr(34)+c+chr(34) for c in pcols)} FROM "{parent_real}" WHERE "{pcol}"=? LIMIT 1',
                (key,)).fetchall()
            if not prow:
                continue
            crows = cur.execute(
                f'SELECT {", ".join(chr(34)+c+chr(34) for c in ccols)} FROM "{child}" WHERE "{ccol}"=?',
                (key,)).fetchall()
            crows = rng.sample(crows, min(len(crows), rng.randint(*n_child)))
            # parent: keep pcol + a few attributes; good-column check on a single row is trivial,
            # so filter only by length / emptiness.
            pr = _clean_rows(prow)[0]
            keep = [i for i, c in enumerate(pcols)
                    if c == pcol or (pr[i] not in (None, "") and len(str(pr[i])) <= MAX_CELL_CHARS)]
            others = [i for i in keep if pcols[i] != pcol]
            others = rng.sample(others, min(len(others), rng.randint(2, 5)))
            pidx = sorted({pcols.index(pcol), *others})
            pr = [coerce_column([v])[0] for v in pr]
            ptab = Table(snake(parent_real), [Column(snake(pcols[i]), infer_type([pr[i]])) for i in pidx],
                         [[pr[i] for i in pidx]], snake(pcol))
            ctab = _build_table(child, ccols, _clean_rows(crows), None, rng, n_cols, keep=[ccol])
            if not ctab or ptab.name == ctab.name or len(ctab.rows) < n_child[0]:
                continue
            fk = ForeignKey(ctab.name, snake(ccol), ptab.name, snake(pcol))
            return Scene(db_path.parent.name, [ptab, ctab], [fk])
        return None
    except sqlite3.Error:
        return None
    finally:
        con.close()
