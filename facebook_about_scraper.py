#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Facebook Playwright Scraper - FAST VERSION
ใช้ Playwright scrape Facebook โดยไม่ต้อง login (เร็วกว่า Selenium 3.3 เท่า)
"""

import sys
import argparse
import sqlite3
import re
import time
from playwright.sync_api import sync_playwright

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass


class FacebookPlaywrightScraper:
    def __init__(self, db_path='pipeline.db', verbose=True):
        """Initialize scraper"""
        self.db_path = db_path
        self.verbose = verbose
        
        # Database
        self.conn = None
        self.cursor = None
        
        # Regex patterns
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'\b(?:0\d{1,2}[\s-]?\d{3}[\s-]?\d{4}|\+66[\s-]?\d{1,2}[\s-]?\d{3}[\s-]?\d{4})\b'
        # Website URL pattern (NOT Facebook)
        self.website_pattern = r'https?://(?!(?:www\.|m\.|mobile\.)?facebook\.com)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s\"\'>]*'
        
        # Stats
        self.stats = {
            'total': 0,
            'success': 0,
            'emails_found': 0,
            'phones_found': 0
        }
    
    def log(self, message):
        """Print log message"""
        if self.verbose:
            print(message)
    
    # ==================== Database ====================
    
    def connect_db(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.log(f"[DB] Connected: {self.db_path}")
    
    def get_facebook_urls(self):
        """Get Facebook URLs from places"""
        query = """
            SELECT place_id, name, website 
            FROM places 
            WHERE website LIKE '%facebook.com%'
            ORDER BY name
        """
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        self.log(f"[DB] Found {len(results)} Facebook pages")
        return results
    
    def save_email(self, place_id, email):
        """Save email to database"""
        if not email:
            return
        
        try:
            self.cursor.execute("""
                INSERT OR IGNORE INTO emails (place_id, email, source, created_at)
                VALUES (?, ?, 'FACEBOOK_PLAYWRIGHT', strftime('%s', 'now'))
            """, (place_id, email))
            self.conn.commit()
            self.log(f"   [SAVE] {email}")
        except Exception as e:
            self.log(f"   [ERROR] Save failed: {e}")
    
    def find_website_urls(self, html):
        """หา Website URLs ใน HTML (ไม่รวม Facebook)"""
        website_urls = re.findall(self.website_pattern, html, re.IGNORECASE)
        
        # Clean and filter URLs
        cleaned_urls = set()
        for url in website_urls:
            # Remove trailing characters
            url = re.sub(r'[)\]\}\>\"\'\s]+$', '', url)
            url = url.rstrip('/')
            
            # Skip common non-business domains
            skip_domains = ['javascript:', 'mailto:', 'tel:', 'sms:', '#']
            if any(skip in url.lower() for skip in skip_domains):
                continue
            
            # Must be valid URL with TLD
            if url and len(url) > 10 and '.' in url:
                cleaned_urls.add(url)
        
        return list(cleaned_urls)[:5]  # Max 5 URLs
    
    def save_discovered_url(self, place_id, url, url_type):
        """บันทึก discovered URL ลง database"""
        try:
            self.cursor.execute("""
                INSERT OR IGNORE INTO discovered_urls 
                (place_id, url, url_type, found_by_stage, status)
                VALUES (?, ?, ?, 'STAGE3', 'NEW')
            """, (place_id, url, url_type))
            self.conn.commit()
            return True
        except Exception as e:
            self.log(f"   [WARNING] Save discovered URL error: {e}")
            return False
    
    def close_db(self):
        """Close database"""
        if self.conn:
            self.conn.close()
            self.log("[DB] Closed")
    
    # ==================== Scraping ====================
    
    def extract_data(self, html):
        """Extract email and phone from HTML"""
        data = {'email': None, 'phone': None}
        
        # Find emails
        emails = re.findall(self.email_pattern, html)
        emails = [e for e in emails if 'facebook' not in e.lower() and 'fb.com' not in e.lower()]
        if emails:
            data['email'] = emails[0]
        
        # Find phones
        phones = re.findall(self.phone_pattern, html)
        if phones:
            data['phone'] = phones[0]
        
        return data
    
    def _facebook_about_url(self, fb_url):
        """ไปที่หน้า About ของ Facebook (มีอีเมล/เบอร์อยู่ที่แท็บ About)"""
        url = (fb_url or "").strip().rstrip("/")
        if "/about" in url and ("/about?" in url or url.endswith("/about")):
            return url
        return f"{url}/about" if url else url

    def scrape_page(self, page, fb_url, place_id):
        """Scrape Facebook page - ไปที่หน้า About เพื่อดึงอีเมล/เบอร์"""
        try:
            about_url = self._facebook_about_url(fb_url)
            self.log(f"   [SCRAPE] {about_url}")
            
            # Navigate to About page (email/phone อยู่ที่แท็บ About)
            page.goto(about_url, wait_until='domcontentloaded', timeout=12000)
            page.wait_for_timeout(2500)  # รอให้ About โหลด
            
            # Get content
            html = page.content()
            data = self.extract_data(html)
            
            # 🔗 NEW: Find and save Website URLs
            website_urls = self.find_website_urls(html)
            if website_urls:
                self.log(f"   [FOUND] {len(website_urls)} Website URL(s) → saving to discovered_urls")
                for web_url in website_urls[:5]:  # Save max 5 URLs
                    self.save_discovered_url(place_id, web_url, 'WEBSITE')
            
            return data
            
        except Exception as e:
            self.log(f"   [ERROR] {e}")
            return {'email': None, 'phone': None}
    
    # ==================== Main ====================
    
    def run(self):
        """Main execution"""
        print("="*70)
        print("[START] Facebook Playwright Scraper (FAST) 🚀")
        print("="*70)
        
        # Connect DB
        self.connect_db()
        
        # Get URLs
        fb_urls = self.get_facebook_urls()
        if not fb_urls:
            print("[INFO] No Facebook pages found")
            return
        
        self.stats['total'] = len(fb_urls)
        
        # Start measuring time
        start_time = time.time()
        
        # Launch Playwright
        with sync_playwright() as p:
            self.log("[BROWSER] Launching Chromium (headless + optimized)...")
            
            browser = p.chromium.launch(
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
            
            # Create context
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                bypass_csp=True,
            )
            
            # Block images/CSS for speed
            context.route("**/*.{png,jpg,jpeg,gif,svg,webp,mp4,avi,mov}", lambda route: route.abort())
            context.route("**/*.css", lambda route: route.abort())
            
            page = context.new_page()
            
            self.log("[BROWSER] Started")
            self.log("[INFO] Running without login (for public pages)")
            
            # Process each page
            print()
            print("-"*70)
            
            for i, (place_id, name, fb_url) in enumerate(fb_urls, 1):
                print(f"\n[{i}/{len(fb_urls)}] {name}")
                
                data = self.scrape_page(page, fb_url, place_id)  # Pass place_id
                
                if data['email']:
                    print(f"   [FOUND] Email: {data['email']}")
                    self.save_email(place_id, data['email'])
                    self.stats['emails_found'] += 1
                    self.stats['success'] += 1
                else:
                    print(f"   [NOT FOUND] No email")
                
                if data['phone']:
                    print(f"   [FOUND] Phone: {data['phone']}")
                    self.stats['phones_found'] += 1
                
                # Small delay
                if i < len(fb_urls):
                    time.sleep(0.5)
            
            # Close browser
            browser.close()
            self.log("\n[BROWSER] Closed")
        
        # Calculate time
        elapsed = time.time() - start_time
        
        # Summary
        print()
        print("="*70)
        print("[SUMMARY]")
        print("="*70)
        print(f"Total pages:   {self.stats['total']}")
        print(f"Emails found:  {self.stats['emails_found']}")
        print(f"Phones found:  {self.stats['phones_found']}")
        if self.stats['total'] > 0:
            success_rate = self.stats['emails_found']/self.stats['total']*100
            print(f"Success rate:  {self.stats['emails_found']}/{self.stats['total']} ({success_rate:.1f}%)")
        print(f"Total time:    {elapsed:.1f} seconds")
        print(f"Average/page:  {elapsed/self.stats['total']:.1f} seconds")
        print("="*70)
        
        # Cleanup
        self.close_db()
        
        print("[DONE] ✅ 🚀")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Stage 3: Facebook About Scraper')
    parser.add_argument('--db', default='pipeline.db', help='SQLite database path')
    parser.add_argument('--verbose', '-v', action='store_true', default=True, help='แสดงข้อความละเอียด')
    args = parser.parse_args()

    print()
    print("="*70)
    print("[INFO] Playwright FAST - No login required")
    print("="*70)
    print()

    scraper = FacebookPlaywrightScraper(
        db_path=args.db,
        verbose=args.verbose
    )

    try:
        scraper.run()
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted")
        scraper.close_db()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        scraper.close_db()
        sys.exit(1)


if __name__ == "__main__":
    main()
