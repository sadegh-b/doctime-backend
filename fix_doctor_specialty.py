# Path: C:/PythonProject/PythonProject/doctime-backend-clean/fix_doctor_specialty.py
import sqlite3
import os

# The actual database file we found in your folder
DB_NAME = "doctime.db"


def main():
    if not os.path.exists(DB_NAME):
        print(f"Error: {DB_NAME} not found in {os.getcwd()}")
        return

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Check if User ID 5 exists
        cursor.execute("SELECT id, name, role FROM users WHERE id = 5")
        user = cursor.fetchone()

        if not user:
            print("Error: User with ID 5 not found in 'users' table.")
            return

        print(f"User Found: {user[1]} (Role: {user[2]})")

        # Check if they have a doctor profile
        cursor.execute("SELECT * FROM doctors WHERE user_id = 5")
        doctor = cursor.fetchone()

        if doctor:
            # Update existing profile
            cursor.execute(
                "UPDATE doctors SET specialty = ?, city = ?, experience_years = ? WHERE user_id = ?",
                ("General Physician", "Zahedan", 5, 5)
            )
            print("Action: Doctor profile updated.")
        else:
            # Create new profile
            cursor.execute(
                "INSERT INTO doctors (user_id, specialty, city, experience_years, consultation_fee) VALUES (?, ?, ?, ?, ?)",
                (5, "General Physician", "Zahedan", 5, 150000)
            )
            print("Action: New doctor profile created.")

        conn.commit()
        print("Success: Database updated and committed.")

    except sqlite3.Error as e:
        print(f"Database Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
