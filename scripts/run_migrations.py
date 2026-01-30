# -*- coding: utf-8 -*-
"""
Run Database Migrations
รันจาก root: python scripts/run_migrations.py
"""
import sys
import sqlite3
import os

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# โฟลเดอร์ migrations อยู่ข้างๆ ไฟล์นี้, DB อยู่ที่ project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
MIGRATIONS_DIR = os.path.join(SCRIPT_DIR, 'migrations')
DB_PATH = os.path.join(PROJECT_ROOT, 'pipeline.db')


def run_migrations():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("="*70)
    print("🔄 Running Database Migrations")
    print("="*70)
    print()

    if not os.path.isdir(MIGRATIONS_DIR):
        print(f"[ERROR] Migrations folder not found: {MIGRATIONS_DIR}")
        conn.close()
        return

    migration_files = sorted([f for f in os.listdir(MIGRATIONS_DIR) if f.endswith('.sql')])

    for migration_file in migration_files:
        print(f"Running: {migration_file}...")

        with open(os.path.join(MIGRATIONS_DIR, migration_file), 'r', encoding='utf-8') as f:
            sql = f.read()

        try:
            cursor.executescript(sql)
            print(f"  ✅ {migration_file} completed")
        except Exception as e:
            print(f"  ⚠️  {migration_file} skipped (already exists or error): {e}")

    conn.commit()
    conn.close()

    print()
    print("="*70)
    print("✅ Migrations completed!")
    print("="*70)


if __name__ == "__main__":
    run_migrations()
