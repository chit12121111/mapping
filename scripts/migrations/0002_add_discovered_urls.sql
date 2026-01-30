-- Migration 0002: Add discovered_urls table for cross-reference scraping
-- Created: 2026-01-27

CREATE TABLE IF NOT EXISTS discovered_urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT NOT NULL,
    url TEXT NOT NULL,
    url_type TEXT NOT NULL,  -- 'FACEBOOK' or 'WEBSITE'
    found_by_stage TEXT NOT NULL,  -- 'STAGE2' or 'STAGE3'
    status TEXT DEFAULT 'NEW',  -- 'NEW', 'PROCESSING', 'DONE', 'FAILED'
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (place_id) REFERENCES places(place_id),
    UNIQUE(place_id, url)  -- ป้องกัน duplicate URLs
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_discovered_urls_status 
ON discovered_urls(status);

CREATE INDEX IF NOT EXISTS idx_discovered_urls_place_id 
ON discovered_urls(place_id);

CREATE INDEX IF NOT EXISTS idx_discovered_urls_type 
ON discovered_urls(url_type);
