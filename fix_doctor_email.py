# Path: C:/PythonProject/PythonProject/doctime-backend-clean/fix_doctor_email.py
import sqlite3

DB_NAME = "doctime.db"


def fix():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # آپدیت ایمیل برای یوزری که دکتر است (id=5)
    print("Updating doctor email in users table...")
    cursor.execute(
        "UPDATE users SET email = ? WHERE id = 5",
        ("sedna@example.com",)
    )

    conn.commit()
    print("Success: Doctor email updated in users table.")
    conn.close()


if __name__ == "__main__":
    fix()
