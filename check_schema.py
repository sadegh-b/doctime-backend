# check_schema.py
import sqlite3

DB_NAME = "doctime.db"
TABLES = ["users", "doctors", "availabilities", "appointments"]

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

for table in TABLES:
    print(f"\n--- Schema for table: {table} ---")
    cursor.execute(f"PRAGMA table_info({table});")
    columns = cursor.fetchall()

    for col in columns:
        # col format: cid, name, type, notnull, default_value, pk
        cid, name, col_type, notnull, default_value, pk = col
        print(
            f"{name} | type={col_type} | notnull={notnull} | "
            f"default={default_value} | pk={pk}"
        )

conn.close()
