# Book Verification 2026 — வேகமான version

இந்த version-ல் database password source code-ல் இல்லை.

## Replit Secrets

இந்த 4 secrets-ஐ Replit Secrets-ல் அமைக்கவும்:

```text
DATABASE_URL
AUTH_ADMIN_PASSWORD
AUTH_DCL_STAFF_PASSWORD
AUTH_LIBRARIAN_PASSWORD
```

முதல் run-ல் `submitted_reports`, `dispatch_records`, `librarian_records`,
`app_users` tables தானாக உருவாகும். புதிய password குறைந்தது 8 எழுத்துகள் இருக்க வேண்டும்.

## Run

```bash
pip install -r requirements.txt
streamlit run app_new.py
```

## Existing Excel data

`2025-2026.xlsx` மற்றும் `Book Supply-2026.xlsx` போன்ற files-ஐ
`📂 Excel அப்லோடு` menu மூலம் upload செய்யலாம். Upload row-by-row அல்ல;
`execute_values` bulk insert பயன்படுத்துகிறது.

Command line upload:

```bash
DATABASE_URL='postgresql://...' python upload_to_neon.py 2025-2026.xlsx
```

## முக்கிய performance மாற்றங்கள்

- Login / menu load-க்கு முன் பெரிய `books` table query செய்யாது.
- Neon connection pool: அதிகபட்சம் 5 reusable connections.
- `books` cache TTL: 180 seconds.
- reports / dispatch queries cache TTL: 30 seconds.
- Writes முடிந்ததும் தேவையான cache மட்டும் clear செய்யப்படுகிறது.
- Upload ஒரு row-க்கு ஒரு INSERT செய்வதற்குப் பதிலாக bulk insert செய்கிறது.
- PostgreSQL identifiers validated மற்றும் quoted ஆகின்றன.
- Database connection timeout 10 seconds.