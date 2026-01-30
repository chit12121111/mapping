#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 4: Cross-Reference Scraper 🔗
- Scrape Facebook URLs ที่ Stage 2 เจอ
- Scrape Website URLs ที่ Stage 3 เจอ
- หา email เพิ่มเติม
"""
import sys
import sqlite3
import re
import time
import argparse
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from email_validator import validate_email, EmailNotValidError
from playwright.sync_api import sync_playwright

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass


class CrossRefScraper:
    def __init__(self, db_path, verbose=False):
        self.db_path = db_path
        self.verbose = verbose
        
        # Settings
        self.page_timeout = 8000
        self.wait_time = 1500
        
        # Email regex
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # Playwright objects
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def connect_db(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        if self.verbose:
            print(f"[OK] Connected to database: {self.db_path}")
    
    def close_db(self):
        """Close database"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            if self.verbose:
                print("[OK] Closed database connection")
    
    def init_browser(self):
        """Initialize Playwright browser"""
        if self.verbose:
            print("[BROWSER] Launching Chromium...")
        
        self.playwright = sync_playwright().start()
        
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
            ]
        )
        
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            bypass_csp=True,
        )
        
        # Block images/CSS
        self.context.route("**/*.{png,jpg,jpeg,gif,svg,webp,mp4,avi,mov}", lambda route: route.abort())
        self.context.route("**/*.css", lambda route: route.abort())
        
        self.page = self.context.new_page()
        
        if self.verbose:
            print("[BROWSER] Ready!")
    
    def close_browser(self):
        """Close browser"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        
        if self.verbose:
            print("[BROWSER] Closed")
    
    # ==================== Database Operations ====================
    
    def get_discovered_urls(self, limit=None):
        """Get discovered URLs with status='NEW'"""
        sql = """
            SELECT id, place_id, url, url_type 
            FROM discovered_urls 
            WHERE status='NEW'
            ORDER BY id
        """
        if limit:
            sql += f" LIMIT {limit}"
        
        self.cursor.execute(sql)
        records = self.cursor.fetchall()
        
        if self.verbose:
            print(f"[INFO] Found {len(records)} discovered URLs (status='NEW')")
        
        return records
    
    def lock_discovered_url(self, url_id):
        """UPDATE status='PROCESSING'"""
        self.cursor.execute(
            "UPDATE discovered_urls SET status='PROCESSING', updated_at=strftime('%s', 'now') WHERE id=?",
            (url_id,)
        )
        self.conn.commit()
    
    def finalize_discovered_url(self, url_id, status):
        """UPDATE status='DONE' or 'FAILED'"""
        self.cursor.execute(
            "UPDATE discovered_urls SET status=?, updated_at=strftime('%s', 'now') WHERE id=?",
            (status, url_id)
        )
        self.conn.commit()
    
    def save_email(self, place_id, email, source):
        """Save email to emails table"""
        try:
            self.cursor.execute(
                "INSERT OR IGNORE INTO emails (place_id, email, source) VALUES (?, ?, ?)",
                (place_id, email, source)
            )
            self.conn.commit()
            return True
        except Exception as e:
            if self.verbose:
                print(f"   [WARNING] Save email error: {e}")
            return False
    
    # ==================== Scraping ====================
    
    def validate_email(self, email):
        """Validate email"""
        try:
            validated = validate_email(email, check_deliverability=False)
            return validated.normalized
        except EmailNotValidError:
            return None
    
    def _facebook_about_url(self, fb_url):
        """ไปที่หน้า About ของ Facebook (อีเมลอยู่ที่แท็บ About)"""
        url = (fb_url or "").strip().rstrip("/")
        if "/about" in url and ("/about?" in url or url.endswith("/about")):
            return url
        return f"{url}/about" if url else url

    def scrape_facebook_url(self, fb_url):
        """Scrape Facebook URL - ไปที่หน้า About เพื่อดึงอีเมล"""
        try:
            about_url = self._facebook_about_url(fb_url)
            self.page.goto(about_url, wait_until='domcontentloaded', timeout=self.page_timeout)
            self.page.wait_for_timeout(max(self.wait_time, 2500))  # รอให้ About โหลด
            
            html = self.page.content()
            
            # Find emails
            emails = re.findall(self.email_pattern, html, re.IGNORECASE)
            emails = [e for e in emails if 'facebook' not in e.lower()]
            
            # Validate
            valid_emails = []
            for email in emails:
                validated = self.validate_email(email)
                if validated:
                    valid_emails.append(validated)
            
            return list(set(valid_emails))
            
        except Exception as e:
            if self.verbose:
                print(f"   [ERROR] {str(e)[:50]}")
            return []
    
    def scrape_website_url(self, web_url):
        """Scrape Website URL"""
        try:
            self.page.goto(web_url, wait_until='commit', timeout=self.page_timeout)
            self.page.wait_for_timeout(self.wait_time)
            
            html = self.page.content()
            soup = BeautifulSoup(html, 'lxml')
            text = soup.get_text()
            
            # Find emails in both HTML and text
            raw_emails = set()
            raw_emails.update(re.findall(self.email_pattern, text, re.IGNORECASE))
            raw_emails.update(re.findall(self.email_pattern, html, re.IGNORECASE))
            
            # Validate
            valid_emails = []
            for email in raw_emails:
                email = email.strip().lower()
                validated = self.validate_email(email)
                if validated:
                    valid_emails.append(validated)
            
            return list(set(valid_emails))
            
        except Exception as e:
            if self.verbose:
                print(f"   [ERROR] {str(e)[:50]}")
            return []
    
    # ==================== Processing ====================
    
    def process_discovered_url(self, url_id, place_id, url, url_type):
        """Process 1 discovered URL"""
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"[PROCESSING] {url_type}: {url}")
            print(f"   Place ID: {place_id}")
        
        try:
            # Lock
            self.lock_discovered_url(url_id)
            
            # Scrape based on type
            emails = []
            if url_type == 'FACEBOOK':
                if self.verbose:
                    print(f"   [SCRAPE] Facebook page...")
                emails = self.scrape_facebook_url(url)
                source = 'CROSSREF_FB'
                
            elif url_type == 'WEBSITE':
                if self.verbose:
                    print(f"   [SCRAPE] Website...")
                emails = self.scrape_website_url(url)
                source = 'CROSSREF_WEB'
            
            # Save emails
            if emails:
                for email in emails:
                    self.save_email(place_id, email, source)
                
                if self.verbose:
                    print(f"   [OK] Found {len(emails)} email(s) → saved!")
                
                self.finalize_discovered_url(url_id, 'DONE')
                return True
            else:
                if self.verbose:
                    print(f"   [FAILED] No email found")
                self.finalize_discovered_url(url_id, 'FAILED')
                return False
                
        except Exception as e:
            if self.verbose:
                print(f"   [ERROR] {e}")
            self.finalize_discovered_url(url_id, 'FAILED')
            return False
    
    def run(self, limit=None):
        """Main execution"""
        start_time = time.time()
        
        # Connect DB
        self.connect_db()
        
        try:
            # Get discovered URLs
            urls = self.get_discovered_urls(limit)
            
            if not urls:
                print("[INFO] No discovered URLs to process (status='NEW')")
                return
            
            print(f"[START] Processing {len(urls)} discovered URLs...\n")
            
            # Initialize browser
            self.init_browser()
            
            success_count = 0
            failed_count = 0
            
            # Process each URL
            for idx, (url_id, place_id, url, url_type) in enumerate(urls, 1):
                print(f"[{idx}/{len(urls)}] ", end="")
                
                success = self.process_discovered_url(url_id, place_id, url, url_type)
                
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            
            elapsed = time.time() - start_time
            
            print(f"\n{'='*60}")
            print(f"[SUCCESS] {success_count} URLs")
            print(f"[FAILED] {failed_count} URLs")
            print(f"[TIME] {elapsed:.2f} seconds ({elapsed/len(urls):.2f}s per URL)")
            print(f"{'='*60}")
            
        finally:
            self.close_browser()
            self.close_db()


def main():
    parser = argparse.ArgumentParser(description='Stage 4: Cross-Reference Scraper')
    parser.add_argument('--db', default='pipeline.db', help='SQLite database path')
    parser.add_argument('--limit', type=int, help='จำกัดจำนวน URLs')
    parser.add_argument('--verbose', '-v', action='store_true', help='แสดงข้อความละเอียด')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Stage 4: Cross-Reference Scraper 🔗")
    print("=" * 60)
    
    scraper = CrossRefScraper(args.db, verbose=args.verbose)
    scraper.run(limit=args.limit)
    
    print("\n[DONE] Stage 4 completed! ✅")


if __name__ == "__main__":
    main()
