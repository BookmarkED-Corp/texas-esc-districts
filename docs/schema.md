# Texas ESC & School District Data Schema

## Source Data

- **esc-districts_YYYY-MM-DD.tsv** — Direct export from Texas Education Agency (TEA) AskTED
  - **Source:** https://www.askted.org/
  - **Report:** "Districts Served by Regional Education Service Centers"
  - **Format:** Tab-separated, one district per row

- **district-enrollment-oct2025_YYYY-MM-DD.tsv** — Direct export from Texas Education Agency (TEA) AskTED
  - **Source:** https://www.askted.org/
  - **Report:** "All Public School Districts Sorted by District Name"
  - **Format:** Tab-separated, one district per row
  - **Enrollment Reference:** October 2025 snapshot

---

## Supabase Schema

### Table: `escs`
Canonical Education Service Center (Region) metadata

| Column | Type | Description |
|--------|------|-------------|
| region_number | INTEGER NOT NULL PRIMARY KEY | ESC number (12–20). Also called "Region X" by TEA. |
| esc_code | VARCHAR(20) NOT NULL | TEA ESC identifier code (e.g., "108-950") |
| esc_name | VARCHAR(255) NOT NULL | Full ESC name (e.g., "REG 1 EDUCATION SERVICE CENTER") |
| created_at | TIMESTAMP | When this record was created |
| updated_at | TIMESTAMP | When this record was last updated |

### Table: `districts`
All public school districts in Texas, linked to ESCs

| Column | Type | Description |
|--------|------|-------------|
| district_id | VARCHAR(20) NOT NULL PRIMARY KEY | TEA district code (e.g., "031-901"), unique across Texas |
| district_name | VARCHAR(255) NOT NULL | Official district name (e.g., "BROWNSVILLE ISD") |
| region_number | INTEGER NOT NULL | ESC number (12–20); foreign key to `escs.region_number` |
| county_code | VARCHAR(10) | TEA county code (e.g., "031") |
| county_name | VARCHAR(255) | Texas county name (e.g., "CAMERON COUNTY") |
| district_type | VARCHAR(50) | Type: "INDEPENDENT", "CHARTER" |
| enrollment_oct2025 | INTEGER | Student enrollment as of October 2025 |
| nces_district_id | VARCHAR(20) | NCES district ID from TEA |
| phone | VARCHAR(20) | District phone number |
| email | VARCHAR(255) | District contact email |
| mailing_address | TEXT | District mailing address |
| web_address | VARCHAR(500) | District website |
| data_last_verified | DATE | When this district record was last verified against TEA source |
| created_at | TIMESTAMP | When this record was created |
| updated_at | TIMESTAMP | When this record was last updated |

### Indices
- `districts.region_number` — for fast ESC lookups
- `districts.district_name` — for text search
- `districts.county_code` — for county-level queries
- `districts.enrollment_oct2025` — for sorting by size

---

## Data Validation Rules

1. **No null mandatory fields:** `district_id`, `district_name`, `region_number` must always be populated.
2. **Valid region:** `region_number` must be in range [12, 20].
3. **Enrollment must be numeric:** If present, must be ≥ 0.
4. **District mapping must be complete:** Any district appearing in the mapping file must also appear in the enrollment file (or be flagged).
5. **Checksum tracking:** Each load records a checksum of the raw TSV so we can detect silent data corruption.

---

## Update Process

1. Download latest ESC districts and enrollment data from TEA AskTED.
2. Save files to `/data/raw/` with date stamp: `esc-districts_YYYY-MM-DD.tsv`, `district-enrollment-oct2025_YYYY-MM-DD.tsv`.
3. Run `python scripts/load-supabase.py` to validate and load into Supabase.
4. Verify row counts and sample data in Supabase dashboard.
5. Commit raw files + ingest logs to GitHub.

---

## Known Quirks

- **Enrollment field formatting:** Numbers may include commas (e.g., `"1,703"`). Parser strips these.
- **Carriage returns in addresses:** Mailing/site addresses may contain literal `\r` characters; parser preserves these.
- **Charter vs. Independent:** Classification is per TEA; some special charter networks may be listed under their own code.
- **University-affiliated districts:** A few districts are university ISDs (e.g., `031-505` UNIVERSITY OF TEXAS RIO GRANDE VALLEY). These are included per TEA classification.
