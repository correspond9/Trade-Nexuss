#!/usr/bin/env python3
"""Dump SQLite DB to CSVs and generate Postgres-compatible DDL.

Usage:
  python sqlite_to_postgres_dump.py --sqlite-path fastapi_backend/database/broker.db --out-dir /tmp/sqlite_dump

This script writes:
 - {out_dir}/ddl.sql  : CREATE TABLE statements (Postgres types)
 - {out_dir}/{table}.csv : CSV exports (with header) for each table

It does not connect to Postgres; after running it you can apply DDL and COPY the CSVs into Postgres.
"""
from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--sqlite-path", required=True)
    p.add_argument("--out-dir", required=True)
    return p.parse_args()


TYPE_MAP = {
    'DATETIME': 'TIMESTAMP',
    'DATE': 'TIMESTAMP',
    'FLOAT': 'DOUBLE PRECISION',
    'REAL': 'DOUBLE PRECISION',
    'DOUBLE': 'DOUBLE PRECISION',
    'INT': 'INTEGER',
    'INTEGER': 'INTEGER',
    'BOOL': 'BOOLEAN',
    'BOOLEAN': 'BOOLEAN',
    'TEXT': 'TEXT',
    'CHAR': 'VARCHAR',
    'VARCHAR': 'VARCHAR',
}


def map_type(sqlite_type: str) -> str:
    if not sqlite_type:
        return 'TEXT'
    t = sqlite_type.strip().upper()
    for k, v in TYPE_MAP.items():
        if k in t:
            # preserve length for varchar(...) if present
            if 'CHAR' in k or 'VARCHAR' in k:
                # attempt to extract parentheses
                import re

                m = re.search(r"\((\d+)\)", t)
                if m:
                    return f"VARCHAR({m.group(1)})"
                return 'VARCHAR'
            return v
    return 'TEXT'


def main():
    args = parse_args()
    sqlite_path = Path(args.sqlite_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not sqlite_path.exists():
        raise SystemExit(f"SQLite DB not found: {sqlite_path}")

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # list tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [r[0] for r in cur.fetchall()]

    ddl_lines = []

    for tbl in tables:
        # get columns
        cur.execute(f"PRAGMA table_info('{tbl}')")
        cols = cur.fetchall()
        col_defs = []
        pk_cols = []
        for c in cols:
            cid, name, ctype, notnull, dflt_value, pk = c
            pg_type = map_type(ctype)
            col_sql = f"\"{name}\" {pg_type}"
            if pk:
                pk_cols.append(name)
            if notnull:
                col_sql += ' NOT NULL'
            if dflt_value is not None:
                # leave default as-is (best-effort)
                col_sql += f" DEFAULT {dflt_value}"
            col_defs.append(col_sql)

        pk_clause = ''
        if len(pk_cols) == 1 and pk_cols[0] == 'id':
            # use SERIAL for id
            # replace the id column definition
            new_defs = []
            for d in col_defs:
                if d.startswith('"id"'):
                    new_defs.append('"id" SERIAL PRIMARY KEY')
                else:
                    new_defs.append(d)
            col_defs = new_defs
        elif pk_cols:
            pk_clause = f", PRIMARY KEY ({', '.join('"%s"' % c for c in pk_cols)})"

        create_sql = f"CREATE TABLE IF NOT EXISTS \"{tbl}\" (\n  " + ",\n  ".join(col_defs) + pk_clause + "\n);"
        ddl_lines.append(create_sql)

        # export data to CSV
        cur2 = conn.cursor()
        cur2.execute(f"SELECT * FROM \"{tbl}\";")
        rows = cur2.fetchall()
        csv_path = out_dir / f"{tbl}.csv"
        with csv_path.open('w', newline='', encoding='utf-8') as fh:
            writer = csv.writer(fh)
            if rows:
                writer.writerow(rows[0].keys())
                for r in rows:
                    writer.writerow([r[k] for k in rows[0].keys()])
            else:
                # write header only
                writer.writerow([c[1] for c in cols])

        print(f"Wrote CSV for {tbl} -> {csv_path} ({len(rows)} rows)")

    ddl_path = out_dir / 'ddl.sql'
    ddl_path.write_text('\n\n'.join(ddl_lines))
    print(f"Wrote DDL -> {ddl_path}")


if __name__ == '__main__':
    main()
