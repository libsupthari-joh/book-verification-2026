# -*- coding: utf-8 -*-
"""
2025-2026-Revised_Vendar_Data.xlsx கோப்பில் உள்ள, ஆனால் தற்போது 'books'
table-ல் இல்லாத வரிசைகளை மட்டும் (இரண்டாம் பிரதிகள் — legitimate 2-copy
orders) கண்டறிந்து INSERT செய்யும் script.

இது ஏற்கனவே உள்ள எந்த வரிசையையும் UPDATE/DELETE செய்யாது — புதிதாக
INSERT மட்டுமே செய்யும். எனவே இதை எத்தனை முறை வேண்டுமானாலும் பாதுகாப்பாக
மீண்டும் இயக்கலாம் (idempotent) — ஏற்கனவே சேர்க்கப்பட்ட வரிசைகள் மீண்டும்
சேர்க்கப்படாது.

இயக்கும் முறை:
    python backfill_missing_copies.py            # DRY RUN
    python backfill_missing_copies.py --commit    # உண்மையாகச் சேமிக்கும்
"""

import sys
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

DB_URL = "postgresql://neondb_owner:npg_y1mObIUlc2ox@ep-odd-pine-b39tu9yu-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"   # <-- இதை மாற்றவும்
EXCEL_FILE = "2025-2026-Revised_Vendar_Data.xlsx"

COMMIT = "--commit" in sys.argv

RENAME = {
    "Book Id": "book_id", "Title": "title", "Language": "language",
    "Author Name": "author", "Isbn": "isbn", "Year": "year_of_publication",
    "Publication Name": "publication_name", "Vendor Name": "vendor_name",
    "Original Price": "price", "Acccepted Price": "accepted_price",
    "library Type": "library_type", "librarianId": "librarian_id",
    "Library Name": "library_name", "Library Tam Name": "library_name_tm",
    "State Accession Number": "state_accession_number", "Quantity": "quantity",
    "Received": "received", "Not Received": "not_received",
    "Central Accession Number": "central_accession_number",
    "DCL / FTB / BL / VL Accession Number": "dcl_ftb_bl_vl_accession_number",
}
FULL_COLS = [
    "book_id", "title", "author", "isbn", "publication_name", "vendor_name",
    "library_type", "librarian_id", "library_name", "year_of_publication",
    "library_name_tm", "price", "accepted_price", "state_accession_number",
    "language", "quantity", "received", "not_received",
    "central_accession_number", "dcl_ftb_bl_vl_accession_number",
]


def to_native_python(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


print("📖 Excel கோப்பைப் படிக்கிறேன்...")
df = pd.read_excel(EXCEL_FILE).rename(columns=RENAME)
df["librarian_id"] = df["librarian_id"].astype(str).str.strip()
df["book_id"] = pd.to_numeric(df["book_id"], errors="coerce").astype("Int64")
df["occurrence_no"] = df.groupby(["book_id", "librarian_id"]).cumcount() + 1
for c in FULL_COLS:
    if c not in df.columns:
        df[c] = None
print(f"   மொத்த வரிசைகள்: {len(df)}")

print("\n🔌 Database-உடன் இணைக்கிறேன்...")
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

print("📥 Excel தரவை temp table-க்குள் ஏற்றுகிறேன்...")
cur.execute("""
    CREATE TEMP TABLE staging_backfill (
        book_id BIGINT, title TEXT, author TEXT, isbn TEXT,
        publication_name TEXT, vendor_name TEXT, library_type TEXT,
        librarian_id TEXT, library_name TEXT, year_of_publication BIGINT,
        library_name_tm TEXT, price BIGINT, accepted_price BIGINT,
        state_accession_number DOUBLE PRECISION, language TEXT,
        quantity DOUBLE PRECISION, received DOUBLE PRECISION,
        not_received DOUBLE PRECISION, central_accession_number DOUBLE PRECISION,
        dcl_ftb_bl_vl_accession_number DOUBLE PRECISION, occurrence_no INT
    ) ON COMMIT PRESERVE ROWS;
""")
staging_cols = FULL_COLS + ["occurrence_no"]
records = [
    tuple(to_native_python(v) for v in row)
    for row in df[staging_cols].itertuples(index=False, name=None)
]
execute_values(cur, f"INSERT INTO staging_backfill ({', '.join(staging_cols)}) VALUES %s;", records)
print(f"   ✅ {len(records)} வரிசைகள் staging-ல் ஏற்றப்பட்டன.")

RANKED_CTE = """
    WITH books_ranked AS (
        SELECT id, book_id, librarian_id,
               ROW_NUMBER() OVER (PARTITION BY book_id, librarian_id ORDER BY id) AS occurrence_no
        FROM books
    )
"""

cur.execute(RANKED_CTE + """
    SELECT COUNT(*) FROM staging_backfill s
    LEFT JOIN books_ranked br ON br.book_id = s.book_id AND br.librarian_id = s.librarian_id
                               AND br.occurrence_no = s.occurrence_no
    WHERE br.id IS NULL;
""")
missing_count = cur.fetchone()[0]
print(f"\n📊 DRY-RUN: Neon-ல் இப்போது இல்லாத, புதிதாக INSERT செய்யப்படும் வரிசைகள்: {missing_count}")

if not COMMIT:
    print("\n🟡 இது DRY RUN மட்டும் — எதுவும் சேமிக்கப்படவில்லை.")
    print("   எண்ணிக்கை சரி எனத் தோன்றினால்: python backfill_missing_copies.py --commit")
    conn.rollback()
    cur.close()
    conn.close()
    sys.exit(0)

print("\n📥 விடுபட்ட வரிசைகளை INSERT செய்கிறேன்...")
upload_cols = FULL_COLS + ["uploaded_at"]
cur.execute(RANKED_CTE + f"""
    INSERT INTO books ({', '.join(upload_cols)})
    SELECT {', '.join('s.' + c for c in FULL_COLS)}, NOW()
    FROM staging_backfill s
    LEFT JOIN books_ranked br ON br.book_id = s.book_id AND br.librarian_id = s.librarian_id
                               AND br.occurrence_no = s.occurrence_no
    WHERE br.id IS NULL;
""")
print(f"   ✅ {cur.rowcount} வரிசைகள் INSERT செய்யப்பட்டன.")

conn.commit()
cur.close()
conn.close()
print("\n✅ முடிந்தது.")
