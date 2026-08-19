from pathlib import Path
import sqlite3
from datetime import datetime


# مسیر پروژه اصلی:
# scripts/promote_user_to_doctor.py
# بنابراین parent.parent به ریشه پروژه می‌رسد.
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "doctime.db"

PHONE = "09120000001"


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Make sure doctime.db is located in the project root."
        )

    # پشتیبان‌گیری دستی قبل از تغییر دیتابیس توصیه می‌شود.
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        user = cursor.execute(
            """
            SELECT id, phone, role, is_active
            FROM users
            WHERE phone = ?
            """,
            (PHONE,),
        ).fetchone()

        if user is None:
            raise RuntimeError(
                f"User with phone {PHONE} was not found."
            )

        user_id = user["id"]

        print(f"User found: id={user_id}, phone={user['phone']}")
        print(f"Current role: {user['role']}")

        doctor = cursor.execute(
            """
            SELECT id, user_id
            FROM doctors
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        if doctor is not None:
            doctor_id = doctor["id"]
            print(
                f"Doctor profile already exists. "
                f"doctor_id={doctor_id}"
            )
        else:
            cursor.execute(
                """
                INSERT INTO doctors (
                    user_id,
                    medical_council_number,
                    specialty_id,
                    sub_specialty,
                    work_shift,
                    province,
                    city,
                    address,
                    latitude,
                    longitude,
                    bio,
                    experience_years,
                    consultation_fee,
                    waiting_time_estimate
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    None,
                    None,
                    None,
                    "morning",
                    None,
                    "Tehran",
                    "Vanak Square, No 10",
                    None,
                    None,
                    "Experienced doctor.",
                    0,
                    0,
                    None,
                ),
            )

            doctor_id = cursor.lastrowid

            print(
                f"Doctor profile created. "
                f"doctor_id={doctor_id}"
            )

        wallet = cursor.execute(
            """
            SELECT id, doctor_id, balance, currency, is_active
            FROM doctor_wallets
            WHERE doctor_id = ?
            """,
            (doctor_id,),
        ).fetchone()

        if wallet is not None:
            print(
                f"Wallet already exists. "
                f"wallet_id={wallet['id']}"
            )
        else:
            now = datetime.utcnow().isoformat(sep=" ")

            cursor.execute(
                """
                INSERT INTO doctor_wallets (
                    doctor_id,
                    balance,
                    currency,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    doctor_id,
                    "0.00",
                    "IRR",
                    1,
                    now,
                    now,
                ),
            )

            print("Doctor wallet created.")

        cursor.execute(
            """
            UPDATE users
            SET role = ?, is_active = ?
            WHERE id = ?
            """,
            ("doctor", 1, user_id),
        )

        conn.commit()

        print("User role updated successfully.")
        print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    main()
