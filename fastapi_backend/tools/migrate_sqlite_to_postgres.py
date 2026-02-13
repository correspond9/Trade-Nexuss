#!/usr/bin/env python3
"""Migrate data from a local SQLite broker.db to a Postgres database.

Usage:
  python migrate_sqlite_to_postgres.py --sqlite-path ./fastapi_backend/database/broker.db --target-url postgresql://user:pass@host:5432/dbname

The script will:
 - verify the SQLite file exists
 - create a timestamped backup copy of the SQLite file (unless --no-backup)
 - reflect the SQLite schema and create matching tables in Postgres
 - copy rows table-by-table
 - attempt to set Postgres sequences for integer primary keys named `id`

This is intended to be non-destructive; it will not remove the SQLite file.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError


def parse_args():
    p = argparse.ArgumentParser(description="Migrate SQLite -> Postgres (basic table copy)")
    p.add_argument("--sqlite-path", required=True, help="Path to broker.db (SQLite)")
    p.add_argument("--target-url", required=False, help="Target Postgres URL. If omitted uses env DATABASE_URL")
    p.add_argument("--no-backup", action="store_true", help="Do not create a backup copy of the SQLite file")
    p.add_argument("--batch-size", type=int, default=500, help="Rows per INSERT batch")
    return p.parse_args()


def backup_sqlite(sqlite_path: Path) -> Path:
    ts = time.strftime("%Y%m%d-%H%M%S")
    dest = sqlite_path.with_name(f"broker.db.backup.{ts}")
    shutil.copy2(str(sqlite_path), str(dest))
    print(f"Backed up SQLite DB to: {dest}")
    return dest


def main():
    args = parse_args()
    sqlite_path = Path(args.sqlite_path)
    if not sqlite_path.exists():
        print(f"ERROR: SQLite DB not found at {sqlite_path}")
        sys.exit(2)

    target_url = args.target_url or os.environ.get("DATABASE_URL")
    if not target_url:
        print("ERROR: No target Postgres URL provided and DATABASE_URL not set")
        sys.exit(2)

    if not args.no_backup:
        backup_sqlite(sqlite_path)

    src_url = f"sqlite:///{sqlite_path.as_posix()}"
    print(f"Source (sqlite): {src_url}")
    print(f"Target (postgres): {target_url}")

    try:
        src_engine = create_engine(src_url)
        dst_engine = create_engine(target_url)

        src_meta = MetaData()
        print("Reflecting SQLite schema...")
        src_meta.reflect(bind=src_engine)

        print("Mapping types and creating tables in target Postgres (if missing)...")
        inspector = inspect(dst_engine)

        # helper to map SQLite types (as strings) to SQLAlchemy/Postgres types
        from sqlalchemy import Table, Column, Integer, Float, String, Text, Boolean, DateTime
        from sqlalchemy.dialects.postgresql import TIMESTAMP

        def map_column_type(col):
            tstr = str(col.type).upper()
            if 'DATETIME' in tstr or 'DATE' in tstr:
                return TIMESTAMP()
            if 'FLOAT' in tstr or 'REAL' in tstr or 'DOUBLE' in tstr:
                return Float()
            if 'INT' in tstr:
                return Integer()
            if 'CHAR' in tstr or 'VARCHAR' in tstr:
                # preserve length if available
                try:
                    length = getattr(col.type, 'length', None)
                except Exception:
                    length = None
                return String(length) if length else String()
            if 'TEXT' in tstr:
                return Text()
            if 'BOOL' in tstr:
                return Boolean()
            # fallback
            return Text()

        dest_meta = MetaData()

        with src_engine.connect() as src_conn, dst_engine.begin() as dst_conn:
            for table in src_meta.sorted_tables:
                tname = table.name
                print(f"Preparing table: {tname} ...")

                # Build destination Table with mapped column types
                cols = []
                for col in table.columns:
                    col_type = map_column_type(col)
                    col_kwargs = {
                        'primary_key': col.primary_key,
                        'nullable': col.nullable,
                    }
                    if col.unique:
                        col_kwargs['unique'] = True
                    cols.append(Column(col.name, col_type, **col_kwargs))

                dst_table = Table(tname, dest_meta, *cols, extend_existing=True)

                # create table if not exists using explicit DDL with mapped SQL types
                if not inspector.has_table(tname):
                    col_defs = []
                    for c in cols:
                        cname = c.name
                        ctype = c.type
                        # map SQLAlchemy types to Postgres SQL type names
                        tname_sql = None
                        if isinstance(ctype, TIMESTAMP):
                            tname_sql = 'TIMESTAMP'
                        else:
                            ctype_name = type(ctype).__name__.upper()
                            if 'FLOAT' in ctype_name or 'REAL' in ctype_name:
                                tname_sql = 'DOUBLE PRECISION'
                            elif 'INTEGER' in ctype_name or 'INT' in ctype_name:
                                tname_sql = 'INTEGER'
                            elif 'STRING' in ctype_name or 'VARCHAR' in ctype_name:
                                # try to include length if present
                                length = getattr(ctype, 'length', None)
                                tname_sql = f"VARCHAR({length})" if length else 'VARCHAR'
                            elif 'TEXT' in ctype_name:
                                tname_sql = 'TEXT'
                            elif 'BOOLEAN' in ctype_name or 'BOOL' in ctype_name:
                                tname_sql = 'BOOLEAN'
                            else:
                                tname_sql = 'TEXT'

                        col_sql = f"{cname} {tname_sql}"
                        if c.primary_key:
                            col_sql += ' PRIMARY KEY'
                        if not c.nullable:
                            col_sql += ' NOT NULL'
                        if getattr(c, 'unique', False):
                            col_sql += ' UNIQUE'
                        col_defs.append(col_sql)

                    create_sql = f"CREATE TABLE IF NOT EXISTS {tname} (\n  " + ",\n  ".join(col_defs) + "\n);"
                    print("About to run CREATE SQL:\n", create_sql)
                    dst_conn.execute(text(create_sql))

                # Now copy rows
                print(f"Copying table: {tname} ...")
                rows = src_conn.execute(table.select()).fetchall()
                if not rows:
                    print(f"  no rows to copy")
                    continue

                keys = rows[0].keys()
                data = [dict(zip(keys, row)) for row in rows]

                batch_size = args.batch_size
                for i in range(0, len(data), batch_size):
                    batch = data[i : i + batch_size]
                    dst_conn.execute(dst_table.insert(), batch)
                print(f"  copied {len(data)} rows")

                # Attempt to fix sequence for integer primary key named 'id'
                pk_cols = [c.name for c in table.primary_key]
                if len(pk_cols) == 1 and pk_cols[0] == 'id':
                    try:
                        max_id = dst_conn.execute(text(f"SELECT MAX(id) FROM {tname}")).scalar() or 0
                        if max_id:
                            seq_stmt = text(f"SELECT setval(pg_get_serial_sequence(:t, :c), :v)")
                            dst_conn.execute(seq_stmt, {"t": tname, "c": 'id', "v": int(max_id)})
                            print(f"  set sequence for {tname}.id to {max_id}")
                    except SQLAlchemyError:
                        pass

        print("Migration completed successfully.")

    except SQLAlchemyError as e:
        print("ERROR during migration:")
        print(e)
        sys.exit(3)


if __name__ == '__main__':
    main()
