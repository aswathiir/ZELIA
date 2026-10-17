#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg2


def ensure_migration_table(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_name TEXT PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )


def already_applied(cur, name: str) -> bool:
    cur.execute("SELECT 1 FROM schema_migrations WHERE migration_name = %s", (name,))
    return cur.fetchone() is not None


def mark_applied(cur, name: str):
    cur.execute(
        "INSERT INTO schema_migrations (migration_name) VALUES (%s) ON CONFLICT (migration_name) DO NOTHING",
        (name,),
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Run SQL migrations in database/migrations.")
    p.add_argument("--db-url", default=os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL"))
    p.add_argument("--migrations-dir", default="database/migrations")
    p.add_argument("--include-upgrade", action="store_true", help="Also execute schema_v28_upgrade.sql at end")
    args = p.parse_args()

    if not args.db_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL is required")

    migration_dir = Path(args.migrations_dir)
    files = sorted(migration_dir.glob("*.sql"))
    if not files:
        raise SystemExit(f"No migration files found in {migration_dir}")

    conn = psycopg2.connect(args.db_url)
    conn.autocommit = False
    cur = conn.cursor()
    ensure_migration_table(cur)
    conn.commit()

    applied = []
    skipped = []
    try:
        for f in files:
            name = f.name
            if already_applied(cur, name):
                skipped.append(name)
                continue
            sql = f.read_text(encoding="utf-8")
            cur.execute(sql)
            mark_applied(cur, name)
            conn.commit()
            applied.append(name)

        if args.include_upgrade:
            upgrade = Path("schema_v28_upgrade.sql")
            if upgrade.exists():
                name = upgrade.name
                if not already_applied(cur, name):
                    cur.execute(upgrade.read_text(encoding="utf-8"))
                    mark_applied(cur, name)
                    conn.commit()
                    applied.append(name)
                else:
                    skipped.append(name)
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    print("Applied migrations:")
    for m in applied:
        print(f"  - {m}")
    print("Skipped migrations:")
    for m in skipped:
        print(f"  - {m}")


if __name__ == "__main__":
    main()

