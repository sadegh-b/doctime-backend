from pathlib import Path
import sqlite3

DB = Path(__file__).resolve().parent / "doctime.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

# ensure we are on the correct database
print("DB:", DB)
print("tables:", [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")])

try:
    cols = [r[1] for r in cur.execute("PRAGMA table_info(doctor_wallets)")]
    print("قبل:", cols)

    if not cols:
        raise RuntimeError("doctor_wallets table not found in this database")

    if "is_active" not in cols:
        cur.execute("ALTER TABLE doctor_wallets ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1")
    if "currency" not in cols:
        cur.execute("ALTER TABLE doctor_wallets ADD COLUMN currency VARCHAR(10) NOT NULL DEFAULT 'IRR'")
    if "created_at" not in cols:
        cur.execute("ALTER TABLE doctor_wallets ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    if "updated_at" not in cols:
        cur.execute("ALTER TABLE doctor_wallets ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")

    conn.commit()

    cols = [r[1] for r in cur.execute("PRAGMA table_info(doctor_wallets)")]
    print("بعد:", cols)

except Exception as e:
    conn.rollback()
    raise
finally:
    conn.close()
