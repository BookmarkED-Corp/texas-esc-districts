# Texas ESC & District Data

Canonical source of truth for all Texas public school districts and their Education Service Centers (ESCs).

**Last updated:** June 26, 2026

---

## Quick Access

- **GitHub:** https://github.com/stevewandler/texas-esc-districts (source of truth)
- **Supabase:** Query tables directly — requires Supabase access
- **Confluence:** Details and metadata in Bookmarked wiki

---

## What's Included

### ESCs (Education Service Centers)

All 20 regional ESCs in Texas (Regions 1–20):
- ESC identifier code (e.g., "108-950")
- List of all school districts served by each ESC

### School Districts

All ~1,200 public school districts in Texas:
- Official district name and TEA code (e.g., "031-901")
- ESC region assignment
- County location
- District type (INDEPENDENT or CHARTER)
- Enrollment as of October 2025
- Contact info (phone, email, website, address)
- NCES district ID

### Data Sources

- **ESC–District Mapping:** Texas Education Agency AskTED ("Districts Served by Regional Education Service Centers" report)
- **Enrollment & Contact Data:** Texas Education Agency AskTED ("All Public School Districts Sorted by District Name" report)
- **Refresh Cadence:** Annual (when TEA releases new enrollment data)

---

## Using the Data

### Query Supabase Directly

You have read access to these tables:

```sql
-- All ESCs
SELECT * FROM escs ORDER BY region_number;

-- All districts in a specific ESC
SELECT * FROM districts WHERE region_number = 12 ORDER BY district_name;

-- Largest districts by enrollment
SELECT district_name, region_number, enrollment_oct2025 
FROM districts 
WHERE enrollment_oct2025 IS NOT NULL 
ORDER BY enrollment_oct2025 DESC 
LIMIT 50;

-- Districts in a specific county
SELECT * FROM districts WHERE county_name = 'HARRIS COUNTY' ORDER BY district_name;

-- Search by district name
SELECT * FROM districts WHERE district_name LIKE '%HOUSTON%';
```

### Download Raw Data

The TSV source files are in `data/raw/`:
- `esc-districts_YYYY-MM-DD.tsv` — ESC–district mapping
- `district-enrollment-oct2025_YYYY-MM-DD.tsv` — Enrollment & details

---

## Data Quality

**Validation performed on every load:**
- No null values in required fields (district_id, district_name, region_number)
- Region numbers are valid (12–20)
- Enrollment numbers are numeric and ≥ 0
- All districts in mapping also appear in enrollment file

**Known issues:**
- Some entries may have incomplete contact information
- A few special entities are classified as ISDs (e.g., university-affiliated districts)
- Charter school names and classifications reflect TEA's current data; changes may lag

---

## Updating the Data

See [how-to-update.md](docs/how-to-update.md) for detailed instructions on refreshing this database from TEA when new data is released.

**Short version:**
1. Download latest reports from TEA AskTED
2. Place TSV files in `data/raw/`
3. Run `python scripts/load-supabase.py`
4. Verify in Supabase
5. Commit to GitHub

---

## Questions?

For issues or questions about the data:
1. Check the [schema documentation](docs/schema.md)
2. Review the [update process](docs/how-to-update.md)
3. Verify the data in Supabase directly (query the tables)
4. Contact the data steward (Forge)
