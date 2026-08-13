# Path: C:/PythonProject/PythonProject/doctime-backend-clean/create_mock_data.py
import sqlite3
from datetime import datetime

DB_NAME = "doctime.db"


def run():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        # 1. مطمئن شویم یک بیمار داریم (اگر patient_id=1 وجود ندارد)
        cursor.execute("SELECT id FROM users WHERE id = 1")
        if not cursor.fetchone():
            print("Creating mock patient...")
            cursor.execute(
                "INSERT INTO users (id, name, phone, hashed_password, role, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                (1, "Patient One", "09120000001", "dummy_hash", "patient", 1)
            )

        # 2. ساخت یک Availability برای دکتر 2 (امروز)
        print("Creating availability for doctor 2...")
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "INSERT INTO availabilities (doctor_id, date, start_time, end_time, is_available, is_booked) VALUES (?, ?, ?, ?, ?, ?)",
            (2, today, "10:00:00", "11:00:00", 0, 1)  # is_available=0, is_booked=1 یعنی رزرو شده
        )
        avail_id = cursor.lastrowid

        # 3. ساخت Appointment برای این Availability
        print(f"Creating appointment linked to availability {avail_id}...")
        cursor.execute(
            "INSERT INTO appointments (doctor_id, patient_id, availability_id, status, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (2, 1, avail_id, "booked", "این یک نوبت تستی است", datetime.now())
        )

        conn.commit()
        print("Success! Mock data inserted.")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    run()
