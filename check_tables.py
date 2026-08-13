# Path: C:/PythonProject/PythonProject/doctime-backend-clean/check_tables.py
import sqlite3
import os

DB_NAME = "doctime.db"


def main():
    if not os.path.exists(DB_NAME):
        print(f"Error: {DB_NAME} not found.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # گرفتن لیست تمام جدول‌ها
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print("--- List of Tables ---")
    for t in tables:
        print(f"Table found: {t[0]}")

    conn.close()


if __name__ == "__main__":
    main()
