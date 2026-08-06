# scripts/fix_doctors_waiting_time_estimate_nullable.py

import os
from sqlalchemy import create_engine, text


def normalize_database_url(url: str) -> str:
    if not url:
        raise RuntimeError("DATABASE_URL is not set")

    # Render sometimes gives postgres:// but SQLAlchemy prefers postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url


def main() -> None:
    database_url = normalize_database_url(os.getenv("DATABASE_URL", ""))

    engine = create_engine(database_url, pool_pre_ping=True)

    statements = [
        """
        ALTER TABLE doctors
        ALTER COLUMN waiting_time_estimate DROP NOT NULL;
        """,
        """
        ALTER TABLE doctors
        ALTER COLUMN waiting_time_estimate SET DEFAULT 15;
        """,
        """
        UPDATE doctors
        SET waiting_time_estimate = 15
        WHERE waiting_time_estimate IS NULL;
        """,
    ]

    with engine.begin() as conn:
        for stmt in statements:
            print("Running:")
            print(stmt.strip())
            conn.execute(text(stmt))

        result = conn.execute(
            text(
                """
                SELECT column_name, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'doctors'
                  AND column_name = 'waiting_time_estimate';
                """
            )
        ).mappings().all()

        print("Column status:")
        for row in result:
            print(dict(row))

    print("Done. doctors.waiting_time_estimate is now nullable and has default 15.")


if __name__ == "__main__":
    main()
