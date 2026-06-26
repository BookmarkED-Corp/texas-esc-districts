# Setup Instructions

## Prerequisites

- GitHub account (to host the repo)
- Supabase project access (db.vaevjtfxbduyqcfuvzfv)
- Python 3.9+
- `psycopg` Python library (`pip install psycopg`)

---

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Create repository named `texas-esc-districts`
3. Set visibility to **Public** (team can access without login)
4. Copy the HTTPS URL from GitHub (e.g., `https://github.com/stevewandler/texas-esc-districts.git`)

---

## Step 2: Push Local Repo to GitHub

```bash
cd /Users/stevewandler/texas-esc-districts

# Add GitHub remote
git remote add origin https://github.com/stevewandler/texas-esc-districts.git
git branch -M main
git push -u origin main
```

---

## Step 3: Set Up Supabase Tables

1. Log into Supabase dashboard: https://app.supabase.com/
2. Navigate to your project (db.vaevjtfxbduyqcfuvzfv)
3. Open **SQL Editor**
4. Copy & paste the contents of [`docs/supabase-schema.sql`](supabase-schema.sql)
5. Click **Run** to create the tables

**Verify:**
```sql
-- Check tables exist
SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename IN ('escs', 'districts');
```

---

## Step 4: Load Initial Data

Set the Supabase connection string and run the ingest script:

```bash
# Set DATABASE_URL (replace with your actual connection string)
export DATABASE_URL="postgresql://[user]:[password]@db.vaevjtfxbduyqcfuvzfv.supabase.co:6543/postgres"

# Run the loader
cd /Users/stevewandler/texas-esc-districts
python scripts/load-supabase.py

# Check logs
tail -20 scripts/load-supabase.log
```

**Verify in Supabase:**
```sql
SELECT COUNT(*) FROM escs;       -- Should be > 10
SELECT COUNT(*) FROM districts;  -- Should be > 8000
```

---

## Step 5: Update Confluence

Add a page in Bookmarked Confluence (ESC Strategic Hub) with a link to this repo and instructions on accessing the data:

**Title:** "Texas ESC & School District Data Hub"

**Content:**
- Link to GitHub repo: https://github.com/stevewandler/texas-esc-districts
- Link to Supabase tables (you have read access)
- Brief overview: What data is included, when it was last updated
- Quick query examples (how to filter by ESC, by enrollment, etc.)

---

## Step 6: Wire Up the Data for Future Updates

When TEA releases new data:

1. Download the two reports from AskTED
2. Place the TSV files in `data/raw/` following the naming convention
3. Run `python scripts/load-supabase.py`
4. Commit & push to GitHub

See [`docs/how-to-update.md`](how-to-update.md) for detailed instructions.

---

## Troubleshooting

### "ERROR: Connection refused"
- Check DATABASE_URL is correct
- Verify Supabase IP whitelist allows your IP
- Test manually: `psql $DATABASE_URL -c "SELECT 1;"`

### "No module named psycopg"
- Install: `pip install psycopg`

### Tables already exist (import error)
- The schema.sql includes `CREATE TABLE IF NOT EXISTS` — safe to re-run
- Or drop & recreate: `DROP TABLE IF EXISTS districts CASCADE; DROP TABLE IF EXISTS escs CASCADE;`

### Enrollment data is NULL in loaded rows
- The parser may need adjustment for the TSV format
- Check a few rows manually to understand the structure
- Edit `scripts/load-supabase.py` to add debug logging
