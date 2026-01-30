# 📧 Google Maps Email Scraper Pipeline

4-Stage automated pipeline สำหรับดึงข้อมูลร้านค้าและอีเมลจาก Google Maps, Websites และ Facebook

## ✨ Features

### 🚀 Stage 1: Google Maps Scraper
- ดึงข้อมูลร้านค้าจาก Google Maps
- ใช้ Docker (gosom/google-maps-scraper)
- รองรับ Depth 1-5 (20-300 results)
- ได้ข้อมูล: ชื่อ, ที่อยู่, เบอร์โทร, เว็บไซต์, พิกัด

### 📧 Stage 2: Website Email Finder
- Scrape อีเมลจากเว็บไซต์ของร้านค้า
- ค้นหา Facebook URLs พร้อมกัน
- รองรับ concurrent requests
- เก็บ discovered URLs ไว้สำหรับ Stage 4

### 📘 Stage 3: Facebook Scraper
- Scrape อีเมลจาก Facebook About page
- ใช้ Playwright
- ค้นหา Website URLs พร้อมกัน
- เก็บ discovered URLs ไว้สำหรับ Stage 4

### 🔗 Stage 4: Cross-Reference Scraper
- Scrape URLs ที่ค้นพบจาก Stage 2 & 3
- Facebook URLs → หาอีเมล + เว็บไซต์
- Website URLs → หาอีเมล + Facebook
- เพิ่มโอกาสหาอีเมลได้มากขึ้น

### 🧹 กรองอีเมลไม่ถูกต้อง (หลัง Pipeline)
- รันอัตโนมัติหลัง Stage 4 เสร็จ
- ลบอีเมลที่รูปแบบไม่ถูกต้อง (ไม่มี @ หรือโดเมน) ออกจาก DB

### 🔐 Login Gmail (OAuth)
- ลงชื่อเข้าใช้ด้วย Google — เลือกบัญชี (OAuth)
- ใช้ส่งอีเมลจากหน้า Results Explorer → Emails ได้
- ตั้งค่า GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET ใน .env

### 🤖 AI Keyword Generator
- สร้าง search query variations ด้วย Gemini AI
- ปรับแต่งคำค้นหาให้หลากหลาย
- เพิ่มโอกาสหาร้านค้าได้มากขึ้น

### 📊 GUI Dashboard (Streamlit)
- รัน Pipeline แบบ GUI (Stage 1–4 + กรองอีเมลไม่ถูกต้อง)
- แสดง Statistics แบบ real-time
- **Emails:** ฟิลเตอร์ (ค้นหา, Source, Category, ความถูกต้องอีเมล), แก้ไขในตาราง, บันทึกลง DB, Download CSV, ส่งอีเมล (OAuth)
- Export ข้อมูลเป็น CSV

## 🛠️ Installation

### 1. ติดตั้ง Dependencies

```bash
# GUI & Core
pip install -r requirements_gui.txt

# Stage 2 (Email Finder)
pip install -r requirements_stage2.txt
```

### 2. ติดตั้ง Docker

ดาวน์โหลดและติดตั้ง [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### 3. Pull Docker Image

```bash
docker pull gosom/google-maps-scraper
```

### 4. ตั้งค่า Environment Variables

สร้างไฟล์ `.env`:

```bash
cp .env.example .env
```

แก้ไข `.env`:

```
# AI Keywords (Tools → AI Keywords)
GEMINI_API_KEY=your_gemini_api_key_here

# Login Gmail (OAuth — ใช้ส่งอีเมลจาก Results → Emails)
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
# GOOGLE_REDIRECT_URI=http://localhost:8501/   # ไม่ใส่ก็ใช้ localhost:8501/
```

- **GEMINI_API_KEY:** https://makersuite.google.com/app/apikey  
- **Google OAuth:** สร้างที่ [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → OAuth 2.0 Client ID (Web), กำหนด Redirect URI เป็น `http://localhost:8501/` และเพิ่ม Test users ใน OAuth consent screen

## 🚀 Usage

### วิธีที่ 1: GUI (แนะนำ)

```bash
streamlit run gui_app.py
```

เปิด browser: http://localhost:8501

**หรือรันด้วย Docker Compose:**

```bash
docker compose up -d --build
```

เปิด browser: http://localhost:8501 (สร้าง `.env` จาก `.env.example` ก่อน)

### วิธีที่ 2: Command Line

#### Stage 1: Google Maps

```bash
docker run --rm -v $(pwd):/work gosom/google-maps-scraper \
  -input /work/config/queries.txt \
  -results /work/output/results.csv \
  -depth 2
```

#### Stage 2: Website Email Finder

```bash
python scripts/csv_to_sqlite.py output/results.csv pipeline.db
python stage2_email_finder.py --db pipeline.db --verbose
```

#### Stage 3: Facebook Scraper

```bash
python facebook_about_scraper.py --verbose
```

#### Stage 4: Cross-Reference

```bash
python stage4_crossref_scraper.py --verbose
```

### วิธีที่ 3: Parallel Execution (เร็วกว่า 20-40%)

```bash
python scripts/run_parallel.py
```

## 📁 Project Structure

```
.
├── gui_app.py                    # Streamlit GUI (จุดเข้าใช้งานหลัก)
├── stage2_email_finder.py        # Stage 2: Website scraper
├── facebook_about_scraper.py    # Stage 3: Facebook scraper
├── stage4_crossref_scraper.py    # Stage 4: Cross-reference
├── keyword_generator.py         # AI keyword generator
├── requirements_gui.txt         # GUI dependencies
├── requirements_stage2.txt      # Stage 2 dependencies
├── config/
│   └── queries.txt               # คำค้นหา (ใช้กับ Stage 1)
├── data/
│   └── th_locations.json         # ข้อมูลภาค/จังหวัด/อำเภอ
├── output/
│   └── results.csv               # ผลจาก Google Maps + export จาก GUI
├── scripts/
│   ├── migrations/               # Database migrations
│   ├── run_migrations.py        # รัน migrations
│   ├── run_parallel.py           # รัน Stage 2 & 3 พร้อมกัน
│   └── csv_to_sqlite.py         # แปลง CSV → SQLite (หลัง Stage 1)
├── .env.example                  # ตัวอย่างตัวแปรสภาพแวดล้อม
└── README.md
```

## ⚙️ Configuration

### Search Depth

| Depth | Results | Time |
|-------|---------|------|
| 1 | ~20-30 | 1-2 min |
| 2 | ~50-100 | 3-5 min |
| 3 | ~100-150 | 6-8 min |
| 4 | ~150-200 | 10-15 min |
| 5 | ~200-300 | 15-20 min |

### Queries Format

`config/queries.txt`:
```
ร้านอาหาร ในกรุงเทพ
ร้านกาแฟ ในเชียงใหม่
ร้านขนม ในภูเก็ต
```

## 📊 Database Schema

### Tables

- **places**: ข้อมูลร้านค้าจาก Google Maps
- **emails**: อีเมลที่พบ (source: WEBSITE, FACEBOOK, CROSSREF)
- **discovered_urls**: URLs ที่พบระหว่าง scrape

## 🔧 Utilities

### View Statistics

```bash
python show_overview.py
```

### Clear Database

```bash
python clear_database.py
```

### Database Migrations

```bash
python scripts/run_migrations.py
```

## 📝 Documentation

- [AI Keyword Generator Guide](AI_KEYWORD_GENERATOR.md)
- [Gemini API Setup](GEMINI_README.md)
- [Location & Radius Guide](LOCATION_RADIUS_GUIDE.md)
- [Playwright Scraper](PLAYWRIGHT_SCRAPER_README.md)
- [Docker](README_DOCKER.md) — รัน GUI ด้วย Docker Compose
- **[เตรียมความพร้อมอัพขึ้นโดเมน](DEPLOY.md)** — ตั้งค่า OAuth, Redirect URI, และ deploy บน production

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available under the MIT License.

## ⚠️ Disclaimer

This tool is for educational purposes only. Please respect website terms of service and robots.txt. Use responsibly and ethically.

## 🙏 Credits

- Google Maps Scraper: [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper)
- Playwright: [microsoft/playwright](https://github.com/microsoft/playwright)
- Streamlit: [streamlit/streamlit](https://github.com/streamlit/streamlit)
