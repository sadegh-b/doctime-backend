# C:\PythonProject\PythonProject\doctime-backend-clean\check_users_schema.py
import sqlite3


def check_schema():
    # اتصال مستقیم به فایل دیتابیس محلی
    conn = sqlite3.connect("doctime.db")
    cursor = conn.cursor()
    try:
        # اجرای دستور PRAGMA برای گرفتن اطلاعات ستون‌های جدول users
        cursor.execute("PRAGMA table_info(users);")
        columns = cursor.fetchall()

        print("\n=== Actual Database Schema for 'users' Table ===")
        print(f"{'ID':<5} | {'Column Name':<15} | {'Data Type':<10} | {'Not Null?':<10} | {'PK':<5}")
        print("-" * 55)

        for col in columns:
            # ساختار خروجی PRAGMA: (cid, name, type, notnull, dflt_value, pk)
            cid, name, type_name, notnull, _, pk = col
            # اگر notnull برابر 1 باشد یعنی مقدار NULL قبول نمی‌کند (اجباری است)
            # اگر notnull برابر 0 باشد یعنی مقدار NULL قبول می‌کند (اختیاری است)
            not_null_status = "Yes (1)" if notnull == 1 else "No (0)"
            print(f"{cid:<5} | {name:<15} | {type_name:<10} | {not_null_status:<10} | {pk:<5}")

    except Exception as e:
        print(f"Error checking database schema: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    check_schema()
