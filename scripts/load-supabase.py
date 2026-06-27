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
    """Parse district enrollment data from AskTED export format."""
    enroll_file = find_latest_file("district-enrollment*.tsv")
    log_msg(f"Reading enrollment data from: {enroll_file}")

    districts = {}

    with open(enroll_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header_row = next(reader, None)  # Skip header
        
        for row in reader:
            if len(row) < 10:
                continue
            
            # AskTED format: each row has:
            # [0]=source, [1]=source, [2]=title, [3]="County", [4]=COUNTY (NNN),
            # [5]="Region", [6]=region_num, [7]="District", [8]=DISTRICT NAME (NNN-NNN),
            # [9]="District Type", [10]=type_label, [11]=type_value, [12]=enrollment_label, [13]=enrollment_value, ...
            
            try:
                # Extract county code from field [4] format: "COUNTY NAME (NNN)"
                county_field = row[4] if len(row) > 4 else ""
                county_code = None
                county_name = None
                county_match = re.search(r'\((\d{3})\)$', county_field)
                if county_match:
                    county_code = county_match.group(1)
                    county_name = county_field[:county_match.start()].strip()
                
                # Extract region from field [6]
                region = None
                if len(row) > 6 and row[6].isdigit():
                    region = int(row[6])
                
                # Extract district code from field [8] format: "NAME (NNN-NNN)"
                district_field = row[8] if len(row) > 8 else ""
                district_code = None
                district_name = None
                district_match = re.search(r'\((\d{3}-\d{3})\)$', district_field)
                if district_match:
                    district_code = district_match.group(1)
                    district_name = district_field[:district_match.start()].strip()
                
                # Extract district type and enrollment
                # Format: [9]="District Type", [10]="Enrollment as of Oct 2025", [11]=TYPE, [12]=ENROLLMENT
                dtype = None
                enroll = None
                if len(row) > 11:
                    dtype = row[11] if row[11] in ["INDEPENDENT", "CHARTER"] else None
                
                # Enrollment is at [12] in AskTED format
                if len(row) > 12 and dtype:
                    val = row[12].replace(",", "").replace('"', "").strip()
                    if val.isdigit():
                        enroll = int(val)
                
                if region and district_code and district_code not in districts:
                    districts[district_code] = {
                        "name": district_name,
                        "region": region,
                        "county": county_name,
                        "county_code": county_code,
                        "type": dtype,
                        "enrollment": enroll,
                    }
            except (IndexError, ValueError):
                continue

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
        log_msg(f"WARNING: {len(missing)} districts in mapping but not enrollment data (expected for some edge cases)")
    
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
