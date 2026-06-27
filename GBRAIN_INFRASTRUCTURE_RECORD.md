# Texas ESC-Districts Infrastructure — G-Brain Record

**Last Updated:** 2026-06-26  
**Status:** ✓ PRODUCTION LIVE  
**Owner:** Forge (Infrastructure)

---

## Project Overview

**Single source of truth for all ~1,200 Texas school districts across 20 Education Service Centers (ESCs).**

This is the canonical data infrastructure that enables district-level operations, ESC partnership strategy, and enrollment tracking across all of Texas public education.

**GitHub Repo:** https://github.com/BookmarkED-Corp/texas-esc-districts  
**Supabase Project:** texas-esc-districts (NEW, separate from G-Brain)  
**Project ID:** `fdnncloyxjsxwdhpfkjj`  
**Confluence Hub:** ESC Strategic Partnership (E1SP) space, "Texas ESC and School District Data Hub"

---

## Data Inventory

### Source Files (GitHub `/data/raw/`)

| File | Size | Rows | Last Updated | Format |
|------|------|------|--------------|--------|
| `esc-districts_2026-06-26.tsv` | 628 KB | 1,219 | 2026-06-26 | TSV (Tab-separated, AskTED export) |
| `district-enrollment-oct2025_2026-06-26.tsv` | 291 KB | 1,219 | 2026-06-26 | TSV (Wide format, AskTED export) |

**Source:** AskTED (Texas Education Data) public export  
**Data Quality:** All 1,219 districts present, 1,196 with Oct 2025 enrollment, all 20 ESC regions represented

### Canonical Tables (Supabase)

#### `escs` (Education Service Centers)
```sql
CREATE TABLE escs (
  region_number INTEGER PRIMARY KEY,           -- 1-20
  esc_code VARCHAR(20) UNIQUE,                 -- e.g., "01-01"
  esc_name VARCHAR(255),                       -- e.g., "Region 1 Education Service Center"
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```
**Rows:** 20  
**Primary Key:** `region_number` (1-20)

#### `districts` (School Districts)
```sql
CREATE TABLE districts (
  district_id VARCHAR(20) PRIMARY KEY,         -- e.g., "057-829" (county-district)
  district_name VARCHAR(255),                  -- e.g., "A+ ACADEMY"
  region_number INTEGER REFERENCES escs(region_number),  -- ESC assignment
  county_code VARCHAR(10),                     -- e.g., "057" (DALLAS)
  county_name VARCHAR(255),
  district_type VARCHAR(50),                   -- "INDEPENDENT" or "CHARTER"
  enrollment_oct2025 INTEGER,                  -- Oct 2025 enrollment (some NULL)
  nces_district_id VARCHAR(20),                -- National Center for Ed Statistics ID
  phone VARCHAR(20),
  email VARCHAR(255),
  mailing_address TEXT,
  web_address VARCHAR(500),
  data_last_verified DATE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```
**Rows:** 1,219  
**Primary Key:** `district_id` (district code NNNNNN-NNN format)  
**Foreign Key:** `region_number` → `escs.region_number`  
**Indexes:**
- `idx_districts_region` — Fast ESC region lookups
- `idx_districts_name` — Full-text search on district name
- `idx_districts_county` — County code lookups
- `idx_districts_enrollment` — Sorted by enrollment

### Row-Level Security (RLS)

Both tables have RLS enabled with public read access:
```sql
ALTER TABLE escs ENABLE ROW LEVEL SECURITY;
ALTER TABLE districts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all authenticated to read escs" ON escs FOR SELECT USING (true);
CREATE POLICY "Allow all authenticated to read districts" ON districts FOR SELECT USING (true);
```

**Access Model:**
- Currently: All authenticated Supabase users can read
- Future: Extend to role-based access (team read-only, Steve read-write)

---

## Infrastructure Details

### Supabase Project Configuration

| Property | Value |
|----------|-------|
| **Project Name** | texas-esc-districts |
| **Project ID** | fdnncloyxjsxwdhpfkjj |
| **Database Host** | db.fdnncloyxjsxwdhpfkjj.supabase.co |
| **Database Port (Direct)** | 5432 ← **USE THIS** |
| **Database Port (Pooler)** | 6543 (not reliable from this environment) |
| **Database User** | postgres |
| **Database Name** | postgres |
| **SSL Mode** | require |
| **Region** | [Supabase default] |

### Connection String (Python/psycopg)

```bash
# DO NOT hardcode — use environment variable
export DATABASE_URL='postgresql://postgres:[PASSWORD]@db.fdnncloyxjsxwdhpfkjj.supabase.co:5432/postgres?sslmode=require'

# Always use port 5432 (direct), not 6543 (pooler)
# Special characters in password (! ? etc.) require single quotes in bash
```

**Credentials:**
- User: `postgres`
- Password: [Store securely — ask Steve or check Supabase dashboard]
- **NOTE:** Password contains special characters (`!?`) — use single quotes when exporting to bash

### Connection Test

```python
import psycopg

conn = psycopg.connect(
    "postgresql://postgres:[PASSWORD]@db.fdnncloyxjsxwdhpfkjj.supabase.co:5432/postgres?sslmode=require"
)
print(conn.info)  # Should print connection info
conn.close()
```

---

## Data Flow & Load Process

### Step 1: Extract (GitHub)
Raw AskTED export files committed to `/data/raw/` with datestamp in filename.

### Step 2: Transform (Python)
**Script:** `/scripts/load-supabase.py`

**Parser Functions:**
- `parse_esc_districts()` — Extracts 20 ESCs from `esc-districts_*.tsv`
- `parse_district_enrollment()` — Extracts 1,219 districts from `district-enrollment-*.tsv` (AskTED wide format)
- **Parser Fix (2026-06-26):** Enrollment field is at column [12] in AskTED export (not [13])

**Data Mapping:**
- ESC region (1-20) from `esc-districts_` file
- District code (NNN-NNN), name, county, type, enrollment from `district-enrollment_` file
- All fields validated, nulls allowed for optional fields (e.g., enrollment not always present)

### Step 3: Load (Supabase)
```bash
cd /Users/stevewandler/texas-esc-districts
export DATABASE_URL='postgresql://postgres:[PASSWORD]@db.fdnncloyxjsxwdhpfkjj.supabase.co:5432/postgres?sslmode=require'
python3 scripts/load-supabase.py
```

**Output:**
```
[timestamp] === Texas ESC & District Data Loader ===
[timestamp] Parsed 20 ESCs
[timestamp] Parsed 1219 districts
[timestamp] Connected to Supabase
[timestamp] Truncated existing data
[timestamp] Loaded 20 ESCs and 1219 districts
[timestamp] === Load Complete ===
```

---

## Verification & Data Quality

### Verified on 2026-06-26

| Check | Result |
|-------|--------|
| ESC regions (1-20) | ✓ All 20 present |
| Total districts | ✓ 1,219 loaded |
| Enrollment data coverage | ✓ 1,196/1,219 have Oct 2025 enrollment |
| Complete records (name + region + type) | ✓ 1,210/1,219 |
| All required FK constraints | ✓ Pass |
| RLS policies | ✓ Enabled |
| Indexes | ✓ Created |

### Sample Data (Verification)
```
057-829: A+ ACADEMY (Region 10, CHARTER, Enrollment: 1,703)
101-871: A+ UNLIMITED POTENTIAL (Region 4, CHARTER, Enrollment: 190)
109-901: ABBOTT ISD (Region 12, INDEPENDENT, Enrollment: 285)
```

### Verification Queries

```sql
-- Count escs and districts
SELECT 
  'ESCs' as table_name, COUNT(*) as row_count FROM escs
UNION ALL
SELECT 'Districts', COUNT(*) FROM districts;

-- Districts per ESC region
SELECT region_number, COUNT(*) as district_count
FROM districts
GROUP BY region_number
ORDER BY region_number;

-- Districts by type
SELECT district_type, COUNT(*) as count
FROM districts
WHERE district_type IS NOT NULL
GROUP BY district_type;

-- Enrollment statistics
SELECT 
  COUNT(*) as total_districts,
  COUNT(enrollment_oct2025) as with_enrollment,
  SUM(enrollment_oct2025) as total_enrollment,
  AVG(enrollment_oct2025) as avg_enrollment,
  MAX(enrollment_oct2025) as max_enrollment
FROM districts;
```

---

## File Locations

### Local Development

```
/Users/stevewandler/texas-esc-districts/
├── README.md                          # Project overview
├── GBRAIN_INFRASTRUCTURE_RECORD.md   # This file
├── MANUAL_SETUP_STEPS.md             # Step-by-step setup guide
├── SUPABASE_SETUP.md                 # Supabase manual guide
│
├── docs/
│   └── supabase-schema.sql           # Full schema (CREATE TABLE, indexes, RLS)
│
├── data/raw/
│   ├── esc-districts_2026-06-26.tsv             # 20 ESCs
│   └── district-enrollment-oct2025_2026-06-26.tsv  # 1,219 districts
│
├── scripts/
│   ├── load-supabase.py              # Main loader (uses psycopg)
│   ├── setup-supabase-api.py         # Alternative REST API approach
│   └── load-supabase.log             # Load execution log
│
└── .gitignore
```

### Remote

- **GitHub:** https://github.com/BookmarkED-Corp/texas-esc-districts
- **Supabase Dashboard:** https://app.supabase.com/project/fdnncloyxjsxwdhpfkjj
- **Supabase SQL Editor:** https://app.supabase.com/project/fdnncloyxjsxwdhpfkjj/sql
- **Confluence:** ESC Strategic Partnership (E1SP) space

---

## Access & Permissions

### Who Can Access

| Role | Access | Method |
|------|--------|--------|
| Steve | Read-write | SQL console + Python scripts |
| Team (Future) | Read-only | RLS via authenticated Supabase users |
| Public | None | Not exposed |

### Credentials Storage

- **Database Password:** Stored in Supabase dashboard (Settings → Database)
- **Connection String:** Use environment variable `DATABASE_URL` (bash single quotes required)
- **Sensitive Note:** Password contains `!?` special characters — bash history expansion will fail without single quotes

### Environment Setup

```bash
# Add to ~/.bashrc or ~/.zshrc if using this frequently
export DATABASE_URL='postgresql://postgres:[PASSWORD]@db.fdnncloyxjsxwdhpfkjj.supabase.co:5432/postgres?sslmode=require'
```

---

## Known Issues & Resolutions

### Issue 1: Bash History Expansion on Password
**Symptom:** `bash: !?@db.fdnncloyxjsxwdhpfkjj.supabase.co:5432/postgres?: event not found`  
**Cause:** Password contains `!?` which bash interprets as history expansion  
**Resolution:** Use single quotes: `export DATABASE_URL='postgresql://...'`

### Issue 2: Connection Refused on Port 6543
**Symptom:** `connection to server at ... port 6543 failed: Connection refused`  
**Cause:** Pooler port (6543) not reachable from certain environments  
**Resolution:** Use direct port 5432 instead: `postgresql://...@db.fdnncloyxjsxwdhpfkjj.supabase.co:5432/postgres`

### Issue 3: AskTED Format Parser Failures
**Symptom:** `Parsed 0 districts` error  
**Cause:** Parser was looking for enrollment at wrong column index ([13] vs [12])  
**Resolution:** Fixed 2026-06-26 — enrollment now correctly extracted from column [12]

---

## Next Steps

### Phase 1: Immediate (Already Done)
- ✓ Extract raw data from AskTED
- ✓ Set up Supabase project (separate from G-Brain)
- ✓ Create schema (escs, districts, indexes, RLS)
- ✓ Load 1,219 districts + 20 ESCs
- ✓ Verify data integrity

### Phase 2: District Intelligence UI (Pending)
- Build query layer to expose districts by ESC region
- Create district lookup/search interface
- Integrate into Bookmarked platform for ESC partnership strategy
- Share with team for operations

### Phase 3: Canonical Source Validation (Pending)
- Deep research: Verify all 1,200 districts correctly mapped to ESCs
- Cross-reference with official TEA (Texas Education Agency) sources
- Document any corrections needed
- Update data if discrepancies found

### Phase 4: Team Access & Governance (Pending)
- Grant read-only access to team members via RLS
- Document query patterns for common use cases
- Set up automated refresh schedule for enrollment data
- Monitoring/alerting for data staleness

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview and quick start |
| `supabase-schema.sql` | Full SQL schema (DDL) |
| `load-supabase.py` | Data loading logic |
| `MANUAL_SETUP_STEPS.md` | Step-by-step setup if automated fails |

---

## Contacts & Ownership

| Role | Person | Details |
|------|--------|---------|
| **Infrastructure Owner** | Forge | CTO agent — builds & maintains infrastructure |
| **Data Owner** | Steve Wandler | Makes decisions on data scope/accuracy |
| **Confluence Liaison** | TBD | Updates E1SP space with changes |

---

## Change Log

| Date | Change | Actor |
|------|--------|-------|
| 2026-06-26 | Initial load: 20 ESCs + 1,219 districts; fixed AskTED parser (enrollment column [12]) | Forge |
| 2026-06-26 | Created Supabase project (separate from G-Brain); verified all data | Forge |
| 2026-06-26 | Documented infrastructure in GBRAIN_INFRASTRUCTURE_RECORD.md | Forge |

---

**This record is the authoritative source for Texas ESC-Districts infrastructure. Keep in sync with G-Brain.**
