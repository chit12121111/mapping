#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 2: Email Finder - PLAYWRIGHT VERSION 🚀
- ใช้ Playwright แทน requests
- หลบ bot detection ได้ดีกว่า
- รัน JavaScript ได้
"""
import sys
import sqlite3
import json
import re
import time
import argparse
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from email_validator import validate_email, EmailNotValidError
from playwright.sync_api import sync_playwright

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass


class EmailFinderPlaywright:
    def __init__(self, db_path, verbose=False):
        self.db_path = db_path
        self.verbose = verbose
        
        # Settings
        self.page_timeout = 8000  # 8 seconds
        self.wait_time = 1500  # 1.5 seconds after load
        
        # Email regex patterns
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.encoded_email_pattern = r'\b[A-Za-z0-9._%+-]+\s*[\[\(]?\s*at\s*[\]\)]?\s*[A-Za-z0-9.-]+\s*[\[\(]?\s*dot\s*[\]\)]?\s*[A-Z|a-z]{2,}\b'
        
        # Facebook URL pattern
        self.facebook_pattern = r'https?://(?:www\.|m\.|mobile\.)?facebook\.com/[^\s\"\'>]+'
        
        # Playwright objects (will be initialized in run())
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def connect_db(self):
        """Connect to SQLite database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        if self.verbose:
            print(f"[OK] Connected to database: {self.db_path}")
    
    def close_db(self):
        """Close database connection"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            if self.verbose:
                print("[OK] Closed database connection")
    
    def init_browser(self):
        """Initialize Playwright browser"""
        if self.verbose:
            print("[BROWSER] Launching Chromium...")
        
        self.playwright = sync_playwright().start()
        
        # Launch browser with optimizations
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        
        # Create context with optimizations
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            bypass_csp=True,
        )
        
        # Block images and CSS to speed up
        self.context.route("**/*.{png,jpg,jpeg,gif,svg,webp,mp4,avi,mov}", lambda route: route.abort())
        self.context.route("**/*.css", lambda route: route.abort())
        
        # Create page
        self.page = self.context.new_page()
        
        if self.verbose:
            print("[BROWSER] Ready!")
    
    def close_browser(self):
        """Close Playwright browser"""
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
    
    # ==================== Invalid Website Check ====================
    
    def is_invalid_website(self, website_url):
        """ตรวจสอบว่า website เป็น Facebook/LINE หรือไม่"""
        if not website_url or not isinstance(website_url, str):
            return True
        
        url_lower = website_url.lower()
        
        # Skip Facebook/LINE/Instagram
        invalid_domains = ['facebook.com', 'fb.com', 'fb.me', 'line.me', 'lin.ee', 'instagram.com']
        for domain in invalid_domains:
            if domain in url_lower:
                return True
        
        return False
    
    # ==================== Phase 1: Read & Lock ====================
    
    def get_new_records(self, limit=None):
        """Get records with status='NEW'"""
        sql = "SELECT place_id, name, website, raw_data FROM places WHERE status='NEW'"
        if limit:
            sql += f" LIMIT {limit}"
        
        self.cursor.execute(sql)
        records = self.cursor.fetchall()
        
        if self.verbose:
            print(f"[INFO] Found {len(records)} records with status='NEW'")
        
        return records
    
    def lock_record(self, place_id):
        """UPDATE status='PROCESSING'"""
        self.cursor.execute(
            "UPDATE places SET status='PROCESSING', updated_at=strftime('%s', 'now') WHERE place_id=?",
            (place_id,)
        )
        self.conn.commit()
    
    # ==================== Phase 2: Extract from Maps Data ====================
    
    def extract_from_maps_data(self, raw_data_json):
        """Parse raw_data JSON และดึงอีเมล"""
        try:
            raw_data = json.loads(raw_data_json)
            emails_str = raw_data.get('emails', '')
            
            if emails_str and isinstance(emails_str, str) and emails_str.strip():
                raw_emails = re.split(r'[,;]', emails_str)
                valid_emails = []
                
                for email in raw_emails:
                    email = email.strip()
                    if email and self.validate_email(email):
                        valid_emails.append(email)
                
                if valid_emails:
                    if self.verbose:
                        print(f"   [OK] Phase 2 (Maps): Found {len(valid_emails)} emails")
                    return valid_emails
            
            return []
            
        except Exception as e:
            if self.verbose:
                print(f"   [WARNING] Phase 2 error: {e}")
            return []
    
    # ==================== Phase 3: Crawl Website (PLAYWRIGHT) ====================
    
    def decode_email(self, text):
        """แปลง encoded email"""
        decoded = text.lower()
        decoded = re.sub(r'\s*[\[\(]?\s*at\s*[\]\)]?\s*', '@', decoded)
        decoded = re.sub(r'\s*[\[\(]?\s*dot\s*[\]\)]?\s*', '.', decoded)
        return decoded.strip()
    
    def find_facebook_urls(self, html):
        """หา Facebook URLs ใน HTML"""
        facebook_urls = re.findall(self.facebook_pattern, html, re.IGNORECASE)
        
        # Clean and filter URLs
        cleaned_urls = set()
        for url in facebook_urls:
            # Remove ALL trailing non-alphanumeric characters
            url = re.sub(r'[^a-zA-Z0-9]+$', '', url)
            
            # Skip groups, events, hashtags, share links, photos
            skip_patterns = ['/groups/', '/events/', '/hashtag/', '/share/', '/photos/', '/posts/']
            if any(skip in url.lower() for skip in skip_patterns):
                continue
            
            # Must be a valid Facebook page/profile URL
            # Format: facebook.com/pagename or facebook.com/profile.php?id=123
            if url and len(url) > 25:
                # Check if it's a valid format
                if '/profile.php?id=' in url or re.search(r'facebook\.com/[a-zA-Z0-9._-]+$', url):
                    cleaned_urls.add(url)
        
        return list(cleaned_urls)
    
    def save_discovered_url(self, place_id, url, url_type):
        """บันทึก discovered URL ลง database"""
        try:
            self.cursor.execute("""
                INSERT OR IGNORE INTO discovered_urls 
                (place_id, url, url_type, found_by_stage, status)
                VALUES (?, ?, ?, 'STAGE2', 'NEW')
            """, (place_id, url, url_type))
            self.conn.commit()
            return True
        except Exception as e:
            if self.verbose:
                print(f"   [WARNING] Save discovered URL error: {e}")
            return False
    
    def crawl_page(self, url, place_id=None):
        """ดึงอีเมลจากหน้า URL ด้วย Playwright"""
        try:
            # Navigate with fast settings
            self.page.goto(url, wait_until='commit', timeout=self.page_timeout)
            
            # Wait for content
            self.page.wait_for_timeout(self.wait_time)
            
            # Get page content
            html = self.page.content()
            
            # 🔗 NEW: Find and save Facebook URLs
            if place_id:
                facebook_urls = self.find_facebook_urls(html)
                if facebook_urls:
                    if self.verbose:
                        print(f"   [FOUND] {len(facebook_urls)} Facebook URL(s) → saving to discovered_urls")
                    for fb_url in facebook_urls:
                        self.save_discovered_url(place_id, fb_url, 'FACEBOOK')
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            text = soup.get_text()
            
            # Find normal emails
            raw_emails = set()
            raw_emails.update(re.findall(self.email_pattern, text, re.IGNORECASE))
            raw_emails.update(re.findall(self.email_pattern, html, re.IGNORECASE))
            
            # Find encoded emails
            encoded_emails = re.findall(self.encoded_email_pattern, text, re.IGNORECASE)
            for encoded in encoded_emails:
                decoded = self.decode_email(encoded)
                raw_emails.add(decoded)
            
            # Validate emails
            valid_emails = []
            for email in raw_emails:
                email = email.strip().lower()
                validated = self.validate_email(email)
                if validated:
                    valid_emails.append(validated)
            
            return list(set(valid_emails))
            
        except Exception as e:
            if self.verbose:
                print(f"   [WARNING] Error: {str(e)[:50]}")
            return []
    
    def crawl_website(self, website_url, place_id):
        """Crawl website - PLAYWRIGHT VERSION"""
        if not website_url or not isinstance(website_url, str):
            return []
        
        # Check invalid websites
        if self.is_invalid_website(website_url):
            if self.verbose:
                print(f"   [SKIP] Invalid website: {website_url}")
            return []
        
        # Fix URL format
        if not website_url.startswith(('http://', 'https://')):
            website_url = 'https://' + website_url
        
        emails = []
        
        # Phase 3.1: Homepage
        if self.verbose:
            print(f"   [SEARCH] Phase 3.1 (Homepage): {website_url}")
        homepage_emails = self.crawl_page(website_url, place_id)  # Pass place_id
        if homepage_emails:
            emails.extend(homepage_emails)
            if self.verbose:
                print(f"   [OK] Phase 3.1: Found {len(homepage_emails)} emails")
            return emails
        
        time.sleep(0.5)
        
        # Phase 3.2: Contact Page
        contact_urls = [
            urljoin(website_url, '/contact'),
            urljoin(website_url, '/contact-us'),
        ]
        
        for contact_url in contact_urls:
            if self.verbose:
                print(f"   [SEARCH] Phase 3.2 (Contact): {contact_url}")
            contact_emails = self.crawl_page(contact_url, place_id)  # Pass place_id
            if contact_emails:
                emails.extend(contact_emails)
                if self.verbose:
                    print(f"   [OK] Phase 3.2: Found {len(contact_emails)} emails")
                return emails
            time.sleep(0.5)
        
        # Phase 3.3: About Page
        about_urls = [
            urljoin(website_url, '/about'),
            urljoin(website_url, '/about-us'),
        ]
        
        for about_url in about_urls:
            if self.verbose:
                print(f"   [SEARCH] Phase 3.3 (About): {about_url}")
            about_emails = self.crawl_page(about_url, place_id)  # Pass place_id
            if about_emails:
                emails.extend(about_emails)
                if self.verbose:
                    print(f"   [OK] Phase 3.3: Found {len(about_emails)} emails")
                return emails
            time.sleep(0.5)
        
        return emails
    
    # ==================== Email Management ====================
    
    def validate_email(self, email):
        """Validate และ normalize email"""
        try:
            validated = validate_email(email, check_deliverability=False)
            return validated.normalized
        except EmailNotValidError:
            return None
    
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
    
    # ==================== Phase 5: Finalize ====================
    
    def finalize_record(self, place_id, status):
        """UPDATE status"""
        self.cursor.execute(
            "UPDATE places SET status=?, updated_at=strftime('%s', 'now') WHERE place_id=?",
            (status, place_id)
        )
        self.conn.commit()
    
    # ==================== Main Processing ====================
    
    def process_record(self, place_id, name, website, raw_data_json):
        """Process 1 record"""
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"[PROCESSING] {name} (ID: {place_id})")
        
        try:
            # Phase 1: Lock
            self.lock_record(place_id)
            if self.verbose:
                print(f"   [LOCK] Phase 1: Set status=PROCESSING")
            
            emails_found = []
            source = None
            
            # Phase 2: Extract from Maps Data
            if self.verbose:
                print(f"   [SEARCH] Phase 2: Maps Data...")
            maps_emails = self.extract_from_maps_data(raw_data_json)
            if maps_emails:
                emails_found = maps_emails
                source = 'MAPS'
            
            # Phase 3: Crawl Website (if not found yet)
            if not emails_found and website:
                if self.verbose:
                    print(f"   [SEARCH] Phase 3: Website...")
                website_emails = self.crawl_website(website, place_id)  # Pass place_id
                if website_emails:
                    emails_found = website_emails
                    source = 'WEBSITE'
            
            # Save emails
            if emails_found:
                for email in emails_found:
                    self.save_email(place_id, email, source)
                
                if self.verbose:
                    print(f"   [OK] Saved {len(emails_found)} emails (source: {source})")
                
                self.finalize_record(place_id, 'DONE')
                if self.verbose:
                    print(f"   [OK] Phase 5: DONE")
                return True
            else:
                self.finalize_record(place_id, 'FAILED')
                if self.verbose:
                    print(f"   [FAILED] Phase 5: No email found")
                return False
            
        except Exception as e:
            if self.verbose:
                print(f"   [ERROR] {e}")
            self.finalize_record(place_id, 'FAILED')
            return False
    
    def run(self, limit=None):
        """Main run method"""
        start_time = time.time()
        
        # Connect to database
        self.connect_db()
        
        try:
            # Get records
            records = self.get_new_records(limit)
            
            if not records:
                print("[INFO] No records to process (status='NEW')")
                return
            
            print(f"[START] Processing {len(records)} records...\n")
            
            # Initialize browser
            self.init_browser()
            
            success_count = 0
            failed_count = 0
            
            # Process records sequentially
            for idx, (place_id, name, website, raw_data_json) in enumerate(records, 1):
                print(f"[{idx}/{len(records)}] ", end="")
                
                success = self.process_record(place_id, name, website, raw_data_json)
                
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            
            elapsed = time.time() - start_time
            
            print(f"\n{'='*60}")
            print(f"[SUCCESS] {success_count} records")
            print(f"[FAILED] {failed_count} records")
            print(f"[TIME] {elapsed:.2f} seconds ({elapsed/len(records):.2f}s per record)")
            print(f"{'='*60}")
            
        finally:
            # Cleanup
            self.close_browser()
            self.close_db()


def main():
    parser = argparse.ArgumentParser(description='Stage 2: Email Finder (Playwright)')
    parser.add_argument('--db', default='pipeline.db', help='SQLite database path')
    parser.add_argument('--limit', type=int, help='จำกัดจำนวน records')
    parser.add_argument('--verbose', '-v', action='store_true', help='แสดงข้อความละเอียด')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Stage 2: Email Finder - PLAYWRIGHT VERSION 🚀")
    print("=" * 60)
    
    finder = EmailFinderPlaywright(args.db, verbose=args.verbose)
    finder.run(limit=args.limit)
    
    print("\n[DONE] Stage 2 completed! ✅")


if __name__ == "__main__":
    main()
