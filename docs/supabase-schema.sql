-- Create tables for Texas ESC & School District data
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS escs (
  region_number INTEGER NOT NULL PRIMARY KEY,
  esc_code VARCHAR(20) NOT NULL UNIQUE,
  esc_name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS districts (
  district_id VARCHAR(20) NOT NULL PRIMARY KEY,
  district_name VARCHAR(255) NOT NULL,
  region_number INTEGER NOT NULL REFERENCES escs(region_number),
  county_code VARCHAR(10),
  county_name VARCHAR(255),
  district_type VARCHAR(50),  -- 'INDEPENDENT' or 'CHARTER'
  enrollment_oct2025 INTEGER,
  nces_district_id VARCHAR(20),
  phone VARCHAR(20),
  email VARCHAR(255),
  mailing_address TEXT,
  web_address VARCHAR(500),
  data_last_verified DATE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_districts_region ON districts(region_number);
CREATE INDEX IF NOT EXISTS idx_districts_name ON districts USING GIN (to_tsvector('english', district_name));
CREATE INDEX IF NOT EXISTS idx_districts_county ON districts(county_code);
CREATE INDEX IF NOT EXISTS idx_districts_enrollment ON districts(enrollment_oct2025 DESC NULLS LAST);

-- Row-level security (optional: allow read access to all authenticated users)
ALTER TABLE escs ENABLE ROW LEVEL SECURITY;
ALTER TABLE districts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read access to escs" ON escs FOR SELECT USING (true);
CREATE POLICY "Allow read access to districts" ON districts FOR SELECT USING (true);

-- Grant permissions
GRANT SELECT ON escs TO authenticated;
GRANT SELECT ON districts TO authenticated;
