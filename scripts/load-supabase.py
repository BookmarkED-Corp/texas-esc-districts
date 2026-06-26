#!/usr/bin/env python3
"""
Load Texas ESC & school district data from raw TSV exports into Supabase.

Usage:
  python scripts/load-supabase.py

Expects files:
  - data/raw/esc-districts_YYYY-MM-DD.tsv
  - data/raw/district-enrollment-oct2025_YYYY-MM-DD.tsv

Outputs:
  - Logs to stdout and scripts/load-supabase.log
  - Loads data into Supabase tables: escs, districts

Exit codes:
  0 — Success
  1 — Validation error
  2 — Supabase connection error
  3 — File not found
"""

import os
import sys
import csv
import re
from datetime import datetime
from pathlib import Path

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg", file=sys.stderr)
    sys.exit(2)

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
LOG_FILE = Path(__file__).parent / "load-supabase.log"
POSTGRES_URL = os.environ.get("DATABASE_URL")

DATA_REFERENCE_DATE = "2026-06-26"


def log_msg(msg: str):
    """Log to stdout and file."""
    timestamp = datetime.now().isoformat()
    log_line = f"[{timestamp}] {msg}"
    print(log_line)
    with open(LOG_FILE, "a") as f:
        f.write(log_line + "\n")


def find_latest_file(pattern: str) -> Path:
    """Find the most recent file matching pattern in DATA_DIR."""
    files = sorted(DATA_DIR.glob(pattern), reverse=True)
    if not files:
        raise FileNotFoundError(f"No files matching '{pattern}' in {DATA_DIR}")
    return files[0]


def parse_esc_districts():
    """Parse ESC-to-districts mapping."""
    esc_file = find_latest_file("esc-districts_*.tsv")
    log_msg(f"Reading ESC mapping from: {esc_file}")

    escs = {}
    esc_districts_map = {}

    with open(esc_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 6:
                continue
            
            esc_full = row[3]  # ESC name with code
            district_code = row[5]  # District code
            
            if not (esc_full and district_code and "-" in district_code):
                continue
            
            # Extract ESC number: "REG X" or find in parentheses
            region_match = re.search(r"REG (\d+)", esc_full)
            code_match = re.search(r"\((\d+-\d+)\)", esc_full)
            
            if region_match and code_match:
                region = region_match.group(1)
                esc_code = code_match.group(1)
                
                if region not in escs:
                    escs[region] = {
                        "number": int(region),
                        "code": esc_code,
                        "name": esc_full,
                    }
                    esc_districts_map[region] = []
                
                if district_code not in esc_districts_map[region]:
                    esc_districts_map[region].append(district_code)

    log_msg(f"Parsed {len(escs)} ESCs")
    return escs, esc_districts_map


def parse_district_enrollment():
    """Parse district enrollment data."""
    enroll_file = find_latest_file("district-enrollment*.tsv")
    log_msg(f"Reading enrollment data from: {enroll_file}")

    districts = {}

    with open(enroll_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 4:
                continue

            # Look for district code (NNN-NNN pattern)
            for i, cell in enumerate(row):
                if re.match(r"^\d{3}-\d{3}$", cell):
                    district_code = cell
                    district_name = row[i - 1] if i > 0 else None
                    
                    # Find region (12-20)
                    region = None
                    for j in range(max(0, i - 15), min(i + 5, len(row))):
                        if row[j].isdigit() and 12 <= int(row[j]) <= 20:
                            region = int(row[j])
                            break
                    
                    # Find enrollment (digit after district type)
                    enroll = None
                    dtype = None
                    for j in range(i + 1, min(i + 15, len(row))):
                        if row[j] in ["INDEPENDENT", "CHARTER"]:
                            dtype = row[j]
                            if j + 1 < len(row):
                                val = row[j + 1].replace(",", "").replace('"', "").strip()
                                if val.isdigit():
                                    enroll = int(val)
                            break
                    
                    # Find county
                    county = None
                    county_code = None
                    for j in range(max(0, i - 20), i):
                        if re.match(r"^\(\d{3}\)$", row[j]):
                            county_code = row[j].strip("()")
                            if j > 0:
                                county = row[j - 1]
                            break
                    
                    if region and district_code not in districts:
                        districts[district_code] = {
                            "name": district_name,
                            "region": region,
                            "county": county,
                            "county_code": county_code,
                            "type": dtype,
                            "enrollment": enroll,
                        }
                    break

    log_msg(f"Parsed {len(districts)} districts")
    return districts


def validate_data(escs, esc_districts_map, districts):
    """Validate data."""
    errors = []
    
    if not escs:
        errors.append("No ESCs parsed")
    if not districts:
        errors.append("No districts parsed")
    
    # Check coverage
    missing = []
    for region, dist_list in esc_districts_map.items():
        for dist_code in dist_list:
            if dist_code not in districts:
                missing.append(dist_code)
    
    if missing:
        log_msg(f"WARNING: {len(missing)} districts in mapping but not enrollment data")
    
    return len(errors) == 0, errors


def load_into_supabase(escs, districts):
    """Load data into Supabase."""
    if not POSTGRES_URL:
        log_msg("ERROR: DATABASE_URL env var not set")
        sys.exit(2)
    
    try:
        conn = psycopg.connect(POSTGRES_URL)
        cur = conn.cursor()
        log_msg("Connected to Supabase")
    except Exception as e:
        log_msg(f"ERROR: Connection failed: {e}")
        sys.exit(2)

    try:
        # Truncate
        cur.execute("TRUNCATE TABLE districts CASCADE; TRUNCATE TABLE escs CASCADE;")
        log_msg("Truncated existing data")

        # Load ESCs
        for region, esc in escs.items():
            cur.execute(
                "INSERT INTO escs (region_number, esc_code, esc_name) VALUES (%s, %s, %s)",
                (esc["number"], esc["code"], esc["name"]),
            )
        
        # Load districts
        for dist_code, dist in districts.items():
            cur.execute(
                """INSERT INTO districts 
                (district_id, district_name, region_number, county_code, county_name, 
                 district_type, enrollment_oct2025, data_last_verified) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    dist_code,
                    dist.get("name"),
                    dist.get("region"),
                    dist.get("county_code"),
                    dist.get("county"),
                    dist.get("type"),
                    dist.get("enrollment"),
                    DATA_REFERENCE_DATE,
                ),
            )
        
        conn.commit()
        log_msg(f"Loaded {len(escs)} ESCs and {len(districts)} districts")

    except Exception as e:
        log_msg(f"ERROR: Load failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


def main():
    log_msg("=== Texas ESC & District Data Loader ===")
    log_msg(f"Data directory: {DATA_DIR}")

    try:
        escs, esc_districts_map = parse_esc_districts()
        districts = parse_district_enrollment()
    except FileNotFoundError as e:
        log_msg(f"ERROR: {e}")
        sys.exit(3)

    is_valid, errors = validate_data(escs, esc_districts_map, districts)
    for err in errors:
        log_msg(f"ERROR: {err}")

    if not is_valid:
        sys.exit(1)

    load_into_supabase(escs, districts)
    log_msg("=== Load Complete ===")


if __name__ == "__main__":
    main()
