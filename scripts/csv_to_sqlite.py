#!/usr/bin/env python3
"""
CSV to SQLite Converter
แปลงไฟล์ CSV จาก google-maps-scraper (Docker) → SQLite
ตั้ง status='NEW' สำหรับ Stage 2 Email Finder
รันจาก root: python scripts/csv_to_sqlite.py <csv_file> <db_file>
"""
import sys
import os
import sqlite3
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MIGRATIONS_DIR = os.path.join(SCRIPT_DIR, 'migrations')


def create_tables(conn):
    """Run all migrations so places, emails, discovered_urls exist"""
    if not os.path.isdir(MIGRATIONS_DIR):
        raise FileNotFoundError(f"Migrations folder not found: {MIGRATIONS_DIR}")
    for name in sorted(os.listdir(MIGRATIONS_DIR)):
        if not name.endswith('.sql'):
            continue
        path = os.path.join(MIGRATIONS_DIR, name)
        with open(path, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
    print("[OK] Created tables successfully")


def convert_csv_to_sqlite(csv_file, db_file):
    """Convert CSV to SQLite"""
    if not Path(csv_file).exists():
        print(f"[ERROR] File not found: {csv_file}")
        return False

    print(f"[1/3] Reading CSV: {csv_file}")

    try:
        df = pd.read_csv(csv_file)
        print(f"[OK] Read {len(df)} places successfully")

        print(f"[INFO] Columns: {', '.join(df.columns[:10])}...")

        print(f"[2/3] Connecting to database: {db_file}")
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        create_tables(conn)

        print(f"[3/3] Inserting {len(df)} places into database...")
        success_count = 0
        skip_count = 0

        for idx, row in df.iterrows():
            try:
                place_id = row.get('place_id', '') or row.get('cid', '') or f"place_{idx}"
                name = row.get('title', '') or row.get('name', 'Unknown')
                website = row.get('website', None)
                phone = row.get('phone', None)
                google_maps_url = row.get('link', '')
                address = row.get('address', None)
                category = row.get('category', None)
                review_count = row.get('review_count', None)
                review_rating = row.get('review_rating', None)
                latitude = row.get('latitude', None)
                longitude = row.get('longitude', None)

                raw_data_json = json.dumps(row.to_dict(), ensure_ascii=False)

                cursor.execute("""
                    INSERT OR IGNORE INTO places (
                        place_id, name, website, phone, google_maps_url,
                        address, category, review_count, review_rating,
                        latitude, longitude, raw_data, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEW')
                """, (
                    place_id, name, website, phone, google_maps_url,
                    address, category, review_count, review_rating,
                    latitude, longitude, raw_data_json
                ))

                if cursor.rowcount > 0:
                    success_count += 1
                else:
                    skip_count += 1

            except Exception as e:
                print(f"[WARNING] Row {idx} error: {e}")
                skip_count += 1

        conn.commit()
        conn.close()

        print(f"\n[SUCCESS] Conversion completed:")
        print(f"   - Inserted: {success_count} places")
        print(f"   - Skipped: {skip_count} places (duplicates)")
        print(f"   - Database: {db_file}")

        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/csv_to_sqlite.py <csv_file> <db_file>")
        print("Example: python scripts/csv_to_sqlite.py output/results.csv pipeline.db")
        sys.exit(1)

    csv_file = sys.argv[1]
    db_file = sys.argv[2]

    print("=" * 60)
    print("CSV to SQLite Converter")
    print("=" * 60)

    success = convert_csv_to_sqlite(csv_file, db_file)

    if success:
        print("\n[DONE] Ready for Stage 2!")
    else:
        print("\n[ERROR] Conversion failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
