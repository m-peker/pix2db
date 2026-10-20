"""Verify and repair a model's SQL dump, statement by statement.

Repairs (deterministic, applied only to statements that fail):
  1. truncated output      → drop the incomplete tail, keep complete VALUES tuples
  2. unescaped apostrophes → O'Brien → O''Brien
  3. bad identifiers       → quote keywords / names starting with a digit
  4. PRIMARY KEY conflicts → drop the PK constraint and reload (data beats constraints)
Checks (reported as warnings): empty tables, values that disagree with the declared type,
FK columns pointing at missing parent values, duplicate rows.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field

from .dbio import ALLOWED, split_statements, strip_fences
from .scene import SQLITE_KEYWORDS, snake

IDENT = r'(?:"[^"]+"|`[^`]+`|\[[^\]]+\]|[A-Za-z_0-9]+)'


@dataclass
class Report:
    sql: str                       # repaired SQL
    con: sqlite3.Connection
    repairs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _quote_ident(name: str) -> str:
    if name[0] in '"`[':
        return name
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) and name.upper() not in SQLITE_KEYWORDS:
        return name
    return '"' + name + '"'


def fix_apostrophes(stmt: str) -> str:
    # a quote between two letters inside a literal is almost always an unescaped apostrophe
    return re.sub(r"(?<=[A-Za-z])'(?=[A-Za-z])", "''", stmt)


def fix_identifiers(stmt: str) -> str:
    m = re.match(r"(?is)(\s*CREATE\s+TABLE\s+)(" + IDENT + r")(\s*\()(.*)(\)\s*;?\s*)$", stmt)
    if m:
        body = m.group(4)
        parts, depth, buf = [], 0, ""
        for ch in body:
            depth += ch == "("
            depth -= ch == ")"
            if ch == "," and depth == 0:
                parts.append(buf)
                buf = ""
            else:
                buf += ch
        parts.append(buf)
        fixed = []
        for p in parts:
            s = p.strip()
            if re.match(r"(?i)(PRIMARY|FOREIGN|UNIQUE|CHECK|CONSTRAINT)\b", s):
                s = re.sub(r"\(([^()]*)\)", lambda mm: "(" + ", ".join(_quote_ident(x.strip()) for x in mm.group(1).split(",")) + ")", s)
                fixed.append("  " + s)
            else:
                mm = re.match(r"(" + IDENT + r")(.*)$", s, re.S)
                fixed.append("  " + (_quote_ident(mm.group(1)) + mm.group(2) if mm else s))
        return m.group(1) + _quote_ident(m.group(2)) + " (\n" + ",\n".join(fixed) + "\n);"
    m = re.match(r"(?is)(\s*INSERT\s+INTO\s+)(" + IDENT + r")\s*\(([^)]*)\)(\s*VALUES.*)$", stmt)
    if m:
        cols = ", ".join(_quote_ident(c.strip()) for c in m.group(3).split(","))
        return f"{m.group(1)}{_quote_ident(m.group(2))} ({cols}){m.group(4)}"
    return stmt


TYPE_TOKEN = re.compile(r"(?is)^(.*?)\s+((?:INTEGER|INT|REAL|TEXT|NUMERIC|FLOAT|DOUBLE|DECIMAL|DATETIME|DATE|"
                        r"BOOLEAN|VARCHAR|CHAR)\b.*)$")


def _clean_name(name: str) -> str:
    name = name.strip()
    if name[:1] in '"`[':
        return name
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return _quote_ident(name)
    s = snake(name)
    return _quote_ident(s if not s[0].isdigit() else "c_" + s)


def sanitize_identifiers(stmt: str) -> str:
    """Rewrite free-text column names ('# of sequences¹') into snake_case identifiers."""
    m = re.match(r"(?is)(\s*CREATE\s+TABLE\s+)(.+?)(\s*\()(.*)(\)\s*;?\s*)$", stmt)
    if m:
        parts, depth, buf = [], 0, ""
        for ch in m.group(4):
            depth += ch == "("
            depth -= ch == ")"
            if ch == "," and depth == 0:
                parts.append(buf)
                buf = ""
            else:
                buf += ch
        parts.append(buf)
        fixed = []
        for p in parts:
            s = p.strip()
            if re.match(r"(?i)(PRIMARY|FOREIGN|UNIQUE|CHECK|CONSTRAINT)\b", s):
                s = re.sub(r"\(([^()]*)\)",
                           lambda mm: "(" + ", ".join(_clean_name(x) for x in mm.group(1).split(",")) + ")", s)
                fixed.append("  " + s)
                continue
            mm = TYPE_TOKEN.match(s)
            fixed.append("  " + (_clean_name(mm.group(1)) + " " + mm.group(2) if mm else _clean_name(s)))
        return m.group(1) + _clean_name(m.group(2)) + " (\n" + ",\n".join(fixed) + "\n);"
    m = re.match(r"(?is)(\s*INSERT\s+INTO\s+)(.+?)\s*\(([^)]*)\)(\s*VALUES.*)$", stmt)
    if m:
        cols = ", ".join(_clean_name(c) for c in m.group(3).split(","))
        return f"{m.group(1)}{_clean_name(m.group(2))} ({cols}){m.group(4)}"
    return stmt


def salvage_insert(stmt: str) -> str | None:
    """Keep only complete VALUES tuples of a truncated INSERT."""
    m = re.match(r"(?is)(\s*INSERT\s+INTO\s+.*?VALUES\s*)(.*)$", stmt)
    if not m:
        return None
    head, body = m.group(1), m.group(2)
    tuples, depth, buf, in_str = [], 0, "", False
    i = 0
    while i < len(body):
        ch = body[i]
        if in_str:
            buf += ch
            if ch == "'":
                if i + 1 < len(body) and body[i + 1] == "'":
                    buf += "'"
                    i += 1
                else:
                    in_str = False
        elif ch == "'":
            in_str = True
            buf += ch
        elif ch == "(":
            depth += 1
            buf += ch
        elif ch == ")":
            depth -= 1
            buf += ch
            if depth == 0:
                tuples.append(buf.strip().lstrip(",").strip())
                buf = ""
        elif depth > 0:
            buf += ch
        i += 1
    if not tuples:
        return None
    return head + ",\n".join(tuples) + ";"


def drop_primary_key(con: sqlite3.Connection, table: str) -> str | None:
    """Recreate `table` without PRIMARY KEY / UNIQUE so that conflicting rows can be stored."""
    row = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    if not row:
        return None
    new = re.sub(r"(?i),\s*(CONSTRAINT\s+\S+\s+)?(PRIMARY\s+KEY|UNIQUE)\s*\([^)]*\)", "", row[0])  # table-level
    new = re.sub(r"(?i)\s+PRIMARY\s+KEY(\s+(ASC|DESC))?(\s+AUTOINCREMENT)?", "", new)          # column-level
    new = re.sub(r"(?i)\s+UNIQUE\b", "", new)
    if new == row[0]:
        return None
    try:
        sqlite3.connect(":memory:").execute(new)  # validate before touching the real DB
    except sqlite3.Error:
        return None
    con.execute(f'ALTER TABLE "{table}" RENAME TO "__old_{table}"')
    con.execute(new)
    con.execute(f'INSERT INTO "{table}" SELECT * FROM "__old_{table}"')
    con.execute(f'DROP TABLE "__old_{table}"')
    return new


def _try(con, stmt) -> str | None:
    try:
        con.execute(stmt)
        return None
    except sqlite3.Error as e:
        return f"{type(e).__name__}: {e}"


def repair(text: str) -> Report:
    con = sqlite3.connect(":memory:")
    rep = Report("", con)
    raw = [s for s in split_statements(strip_fences(text)) if s]
    final = []
    for k, stmt in enumerate(raw):
        if not ALLOWED.match(stmt):
            continue
        is_last = k == len(raw) - 1
        if not sqlite3.complete_statement(stmt):
            if is_last and re.match(r"(?i)\s*INSERT", stmt):
                s2 = salvage_insert(stmt)
                if s2:
                    rep.repairs.append("salvaged complete rows of a truncated INSERT")
                    stmt = s2
            else:
                stmt = stmt.rstrip() + ";"
        err = _try(con, stmt)
        if err:
            for name, fn in (("escaped apostrophes", fix_apostrophes), ("quoted identifiers", fix_identifiers),
                             ("escaped apostrophes + quoted identifiers", lambda s: fix_identifiers(fix_apostrophes(s))),
                             ("sanitized identifiers", sanitize_identifiers),
                             ("escaped apostrophes + sanitized identifiers",
                              lambda s: sanitize_identifiers(fix_apostrophes(s)))):
                s2 = fn(stmt)
                if s2 != stmt and _try(con, s2) is None:
                    rep.repairs.append(name)
                    stmt, err = s2, None
                    break
        if err and "UNIQUE constraint failed" in err:
            tbl = err.split("failed:")[1].strip().split(".")[0]
            try:
                dropped = drop_primary_key(con, tbl)
            except sqlite3.Error:
                dropped = None
            if dropped and _try(con, stmt) is None:
                rep.repairs.append(f"dropped PRIMARY KEY on {tbl} (duplicate key values)")
                final = [re.sub(r"(?i)\s+PRIMARY\s+KEY", "", s) if re.match(rf'(?is)\s*CREATE\s+TABLE\s+"?{re.escape(tbl)}"?\s*\(', s) else s
                         for s in final]
                err = None
        if err:
            rep.errors.append(f"{err} :: {stmt[:100]}")
            continue
        final.append(stmt)
    con.commit()
    rep.sql = "\n".join(final)
    rep.warnings = checks(con)
    return rep


def checks(con: sqlite3.Connection) -> list[str]:
    w = []
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for t in tables:
        n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        if n == 0:
            w.append(f"table {t} is empty")
            continue
        info = con.execute(f'PRAGMA table_info("{t}")').fetchall()
        for _, col, decl, *_ in info:
            d = (decl or "").upper()
            if "INT" in d or "REAL" in d or "NUM" in d:
                bad = con.execute(f'SELECT COUNT(*) FROM "{t}" WHERE typeof("{col}")=\'text\'').fetchone()[0]
                if bad:
                    w.append(f"{t}.{col}: {bad} non-numeric value(s) in a {d} column")
        dup = con.execute(f'SELECT COUNT(*) - COUNT(DISTINCT {", ".join(chr(34) + c[1] + chr(34) for c in info)}) '
                          f'FROM "{t}"').fetchone()[0] if len(info) == 1 else \
            n - con.execute(f'SELECT COUNT(*) FROM (SELECT DISTINCT * FROM "{t}")').fetchone()[0]
        if dup:
            w.append(f"table {t}: {dup} duplicate row(s)")
        for fk in con.execute(f'PRAGMA foreign_key_list("{t}")').fetchall():
            parent, frm, to = fk[2], fk[3], fk[4]
            try:
                miss = con.execute(
                    f'SELECT COUNT(*) FROM "{t}" WHERE "{frm}" IS NOT NULL AND "{frm}" NOT IN '
                    f'(SELECT "{to}" FROM "{parent}")').fetchone()[0]
                if miss:
                    w.append(f"{t}.{frm}: {miss} value(s) not found in {parent}.{to}")
            except sqlite3.Error:
                w.append(f"{t}: foreign key references missing table/column {parent}.{to}")
    return w
