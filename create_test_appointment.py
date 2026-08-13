# Path: C:/PythonProject/PythonProject/doctime-backend-clean/create_test_appointment.py
import sqlite3
import os
from datetime import datetime, timedelta

DB_NAME = "doctime.db"


def main():
    if not os.path.exists(DB_NAME):
        print(f"Error: {DB_NAME} not found.")
        return

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Setting time for tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M')

        # 1. Create a Time Slot (Availability) for Doctor ID 5
        cursor.execute("""
                       INSERT INTO availability (doctor_id, start_time, end_time, is_booked)
                       VALUES (?, ?, ?, ?)
                       """, (5, tomorrow, tomorrow, 1))

        availability_id = cursor.lastrowid

        # 2. Create an Appointment (Assume Patient ID 1 exists)
        # If you get a foreign key error, change 1 to an existing user id
        cursor.execute("""
                       INSERT INTO appointments (patient_id, doctor_id, availability_id, status, created_at)
                       VALUES (?, ?, ?, ?, ?)
                       """, (1, 5, availability_id, "scheduled", datetime.now().strftime('%Y-%m-%d %H:%M')))

        conn.commit()
        print(f"Success: Test appointment created for tomorrow at {tomorrow}")
        print(f"Availability ID: {availability_id}")

    except sqlite3.Error as e:
        print(f"Database Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
