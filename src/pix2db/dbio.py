"""Load model outputs into SQLite and read databases back as plain Python tables."""
from __future__ import annotations

import io
import re
import sqlite3
from dataclasses import dataclass

ALLOWED = re.compile(r"^\s*(CREATE\s+TABLE|INSERT\s+INTO)\b", re.I)
FENCE = re.compile(r"```(?:sql|sqlite|html)?\s*(.*?)```", re.S | re.I)


@dataclass
class LoadResult:
    con: sqlite3.Connection
    n_statements: int
    n_errors: int
    errors: list[str]


def strip_fences(text: str) -> str:
    blocks = FENCE.findall(text)
    if blocks:
        return "\n".join(blocks)
    # unterminated fence (output hit the token limit)
    m = re.search(r"```(?:sql|sqlite|html)?\s*(.*)", text, re.S | re.I)
    return m.group(1) if m else text


def split_statements(sql: str) -> list[str]:
    stmts, buf = [], ""
    for line in sql.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            stmts.append(buf.strip())
            buf = ""
    if buf.strip():
        stmts.append(buf.strip())  # incomplete tail, will likely fail
    return stmts


def load_sql(text: str) -> LoadResult:
    """Execute only CREATE TABLE / INSERT INTO statements into a fresh in-memory DB."""
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys=OFF")
    stmts = [s for s in split_statements(strip_fences(text)) if s]
    errors = []
    n = 0
    for s in stmts:
        if not ALLOWED.match(s):
            continue
        n += 1
        try:
            con.execute(s)
        except sqlite3.Error as e:
            errors.append(f"{type(e).__name__}: {e} :: {s[:120]}")
    con.commit()
    return LoadResult(con, n, len(errors), errors)


def load_html_tables(text: str) -> LoadResult:
    """Baseline pipeline: VLM → HTML table(s) → pandas.read_html → SQLite (the '20-line script')."""
    import pandas as pd
    from .scene import snake

    con = sqlite3.connect(":memory:")
    errors = []
    try:
        dfs = pd.read_html(io.StringIO(strip_fences(text)))
    except Exception as e:  # noqa: BLE001
        return LoadResult(con, 0, 1, [f"read_html: {e}"])
    for k, df in enumerate(dfs):
        if isinstance(df.columns, pd.MultiIndex):
            cols = ["_".join(dict.fromkeys(str(x) for x in tup if not str(x).startswith("Unnamed")))
                    for tup in df.columns]
        else:
            cols = [str(c) for c in df.columns]
        seen, names = {}, []
        for c in cols:
            s = snake(c)
            seen[s] = seen.get(s, 0) + 1
            names.append(s if seen[s] == 1 else f"{s}_{seen[s]}")
        df.columns = names
        try:
            df.to_sql(f"table_{k + 1}", con, index=False)
        except Exception as e:  # noqa: BLE001
            errors.append(f"to_sql: {e}")
    return LoadResult(con, len(dfs), len(errors), errors)


@dataclass
class DBTable:
    name: str
    columns: list[str]
    decl_types: list[str]
    rows: list[tuple]
    fks: list[tuple[str, str, str]]  # (from_col, parent_table, parent_col)


def read_db(con: sqlite3.Connection) -> list[DBTable]:
    out = []
    names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
             if not r[0].startswith("sqlite_")]
    for t in names:
        info = con.execute(f'PRAGMA table_info("{t}")').fetchall()
        cols = [i[1] for i in info]
        types = [(i[2] or "").upper() for i in info]
        rows = con.execute(f'SELECT * FROM "{t}"').fetchall()
        fks = [(f[3], f[2], f[4]) for f in con.execute(f'PRAGMA foreign_key_list("{t}")').fetchall()]
        out.append(DBTable(t, cols, types, rows, fks))
    return out
