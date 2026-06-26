# How to Update ESC & District Data

## When to Update

Update this database when the Texas Education Agency (TEA) releases new district or enrollment data. Typically:
- Enrollment data is updated annually (October snapshot each fall)
- ESC district mappings update when districts join/leave an ESC

## Steps

### 1. Download from TEA AskTED

1. Go to https://www.askted.org/
2. Run two reports:
   - **Report:** "Districts Served by Regional Education Service Centers"
     - Export as TSV → name it `esc-districts_YYYY-MM-DD.tsv`
   - **Report:** "All Public School Districts Sorted by District Name"
     - Export as TSV → name it `district-enrollment-oct2025_YYYY-MM-DD.tsv` (update the reference year as needed)

### 2. Move Files to Repo

```bash
# Place the two TSV files in data/raw/
mv ~/Downloads/esc-districts_YYYY-MM-DD.tsv /path/to/texas-esc-districts/data/raw/
mv ~/Downloads/district-enrollment-oct2025_YYYY-MM-DD.tsv /path/to/texas-esc-districts/data/raw/
```

### 3. Run Ingestion

```bash
# Make sure DATABASE_URL is set
export DATABASE_URL="postgresql://..."  # Your Supabase connection string

# Run the loader
python scripts/load-supabase.py
```

The script will:
- Parse both TSV files
- Validate coverage (all districts in mapping should appear in enrollment)
- Load data into Supabase (truncates old data first)
- Log results to `scripts/load-supabase.log`

### 4. Verify in Supabase

1. Log into Supabase dashboard
2. Navigate to **SQL Editor** or use the table viewer
3. Check row counts:
   - `SELECT COUNT(*) FROM escs;` — should be 20 (regions 1-20, but database uses 12-20)
   - `SELECT COUNT(*) FROM districts;` — should be ~8,000+
4. Spot-check a few districts:
   ```sql
   SELECT * FROM districts WHERE region_number = 10 LIMIT 5;
   ```

### 5. Commit to GitHub

```bash
cd /path/to/texas-esc-districts
git add data/raw/esc-districts_*.tsv data/raw/district-enrollment*.tsv
git commit -m "Update ESC/district data from TEA AskTED ($(date +%Y-%m-%d))"
git push origin main
```

Also commit any load logs if useful for audit trail:
```bash
git add scripts/load-supabase.log
git commit -m "Load log for data sync"
git push origin main
```

---

## Troubleshooting

### "No files matching 'esc-districts_*.tsv'"
- Make sure the TSV files are in `data/raw/` directory
- Check the exact filenames — they must match the pattern

### "Validation: X districts in mapping but not in enrollment"
- This is usually OK — it means the mapping file has older districts that didn't appear in current enrollment data
- If it's more than 10-20 missing districts, investigate manually

### "Failed to connect to Supabase"
- Verify `DATABASE_URL` is set and correct
- Make sure your Supabase IP is whitelisted
- Test the connection: `psql $DATABASE_URL -c "SELECT 1;"`

### "Enrollment data is all NULL"
- The parser may not be extracting enrollment correctly
- Check the structure of the raw TSV file
- Edit `scripts/load-supabase.py` to print debug info on a few rows

---

## Future Enhancements

- Add checksum tracking to detect silent data corruption
- Export processed JSON files for easy querying
- Auto-detect when TEA publishes new data (RSS feed, email alerts)
