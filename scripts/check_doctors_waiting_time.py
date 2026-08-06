# doctime-backend/scripts/check_doctors_waiting_time.py

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        print("Set it in PowerShell like this:")
        print('$env:DATABASE_URL = "paste-your-external-database-url-here"')
        sys.exit(1)

    return database_url


def main() -> None:
    database_url = get_database_url()

    try:
        engine = create_engine(database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            print("=" * 80)
            print("COLUMN INFO: doctors.waiting_time_estimate")
            print("=" * 80)

            column_result = conn.execute(
                text(
                    """
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = 'doctors'
                      AND column_name = 'waiting_time_estimate';
                    """
                )
            )

            column_rows = column_result.fetchall()

            if not column_rows:
                print("No column found: doctors.waiting_time_estimate")
            else:
                for row in column_rows:
                    print(dict(row._mapping))

            print()
            print("=" * 80)
            print("CURRENT VALUES: doctors.waiting_time_estimate")
            print("=" * 80)

            values_result = conn.execute(
                text(
                    """
                    SELECT id, waiting_time_estimate
                    FROM doctors
                    ORDER BY id;
                    """
                )
            )

            value_rows = values_result.fetchall()

            if not value_rows:
                print("No doctors found.")
            else:
                for row in value_rows:
                    print(dict(row._mapping))

    except SQLAlchemyError as exc:
        print("DATABASE ERROR:")
        print(exc)
        sys.exit(1)

    except Exception as exc:
        print("UNEXPECTED ERROR:")
        print(exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
