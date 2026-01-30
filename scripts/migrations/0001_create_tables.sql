-- SQLite Schema for Google Maps Email Pipeline
-- Stage 1: Docker scraper → CSV → SQLite
-- Stage 2: Python email finder → SQLite

-- Places table (แปลงจาก CSV)
CREATE TABLE IF NOT EXISTS places (
    place_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    website TEXT,
    phone TEXT,
    google_maps_url TEXT NOT NULL,
    address TEXT,
    category TEXT,
    review_count INTEGER,
    review_rating REAL,
    latitude REAL,
    longitude REAL,
    raw_data TEXT NOT NULL,  -- JSON ของทุก fields จาก CSV
    status TEXT NOT NULL DEFAULT 'NEW',  -- NEW, PROCESSING, DONE, FAILED
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

-- Index สำหรับ query ข้อมูล
CREATE INDEX IF NOT EXISTS idx_places_status ON places(status);
CREATE INDEX IF NOT EXISTS idx_places_name ON places(name);

-- Emails table (รองรับ source: MAPS, WEBSITE, FACEBOOK)
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT NOT NULL,
    email TEXT NOT NULL,
    source TEXT NOT NULL,  -- MAPS, WEBSITE, FACEBOOK
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    UNIQUE(place_id, email),  -- ป้องกันอีเมลซ้ำสำหรับแต่ละ place
    FOREIGN KEY (place_id) REFERENCES places(place_id)
);

-- Index สำหรับ query ข้อมูล
CREATE INDEX IF NOT EXISTS idx_emails_place_id ON emails(place_id);
CREATE INDEX IF NOT EXISTS idx_emails_email ON emails(email);
CREATE INDEX IF NOT EXISTS idx_emails_source ON emails(source);
