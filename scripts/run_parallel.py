#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Stage 2 & 3 in Parallel
รัน Website และ Facebook scraper พร้อมกัน
รันจาก root: python scripts/run_parallel.py
"""
import sys
import os
import time
from multiprocessing import Process

# ให้ import stage2/facebook จาก project root ได้ (ทั้ง process หลักและ child)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def run_stage2():
    """Run Stage 2 - Website Scraper"""
    import stage2_email_finder

    print("\n" + "="*70)
    print("🌐 Starting Stage 2: Website Scraper")
    print("="*70)

    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _db = os.path.join(_root, 'pipeline.db')
    finder = stage2_email_finder.EmailFinderPlaywright(
        db_path=_db,
        verbose=True
    )
    finder.run()


def run_stage3():
    """Run Stage 3 - Facebook Scraper"""
    import facebook_about_scraper

    print("\n" + "="*70)
    print("📘 Starting Stage 3: Facebook Scraper")
    print("="*70)

    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _db = os.path.join(_root, 'pipeline.db')
    scraper = facebook_about_scraper.FacebookPlaywrightScraper(
        db_path=_db,
        verbose=True
    )
    scraper.run()


def main():
    print("="*70)
    print("🚀 PARALLEL EXECUTION - Stage 2 & 3")
    print("="*70)
    print()
    print("Starting both scrapers in parallel...")
    print("This will run Stage 2 (Website) and Stage 3 (Facebook) simultaneously")
    print()

    start_time = time.time()

    p2 = Process(target=run_stage2, name="Stage2-Website")
    p3 = Process(target=run_stage3, name="Stage3-Facebook")

    print("[START] Launching Stage 2 & 3...")
    p2.start()
    p3.start()

    print("[WAIT] Waiting for both stages to complete...")
    print()

    p2.join()
    p3.join()

    elapsed = time.time() - start_time

    print()
    print("="*70)
    print("✅ BOTH STAGES COMPLETED!")
    print("="*70)
    print(f"Total Time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    print()
    print("Next step:")
    print("  python stage4_crossref_scraper.py --verbose")
    print("="*70)


if __name__ == "__main__":
    main()
