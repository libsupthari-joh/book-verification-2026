"""One-time / repeatable bulk loader for a CSV or Excel file.

Usage:
    DATABASE_URL='postgresql://...' python upload_to_neon.py 2025-2026.xlsx

The script uses the same database setting as the Streamlit app and never
contains a credential.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python upload_to_neon.py <file.xlsx|file.csv>")
        return 2
    database_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    if not database_url:
        print("ERROR: DATABASE_URL is not set.")
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERROR: file not found: {path}")
        return 2
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_excel(path)
    frame.columns = [str(col).strip().lower() for col in frame.columns]
    frame = frame.loc[:, ~frame.columns.duplicated()]
    table = "books"
    with psycopg2.connect(database_url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s
                ORDER BY ordinal_position
                """,
                (table,),
            )
            existing = [row[0] for row in cur.fetchall()]
            if not existing:
                definitions = sql.SQL(", ").join(
                    sql.SQL("{} TEXT").format(sql.Identifier(col)) for col in frame.columns
                )
                cur.execute(
                    sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
                        sql.Identifier(table), definitions
                    )
                )
                existing = list(frame.columns)
            columns = [col for col in frame.columns if col in existing]
            if not columns:
                raise RuntimeError("No Excel columns match the books table.")
            values = [
                tuple(None if pd.isna(value) else value for value in row)
                for row in frame[columns].itertuples(index=False, name=None)
            ]
            query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
                sql.Identifier(table),
                sql.SQL(", ").join(sql.Identifier(col) for col in columns),
            )
            execute_values(cur, query.as_string(conn), values, page_size=1000)
    print(f"Uploaded {len(values):,} rows to {table}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())