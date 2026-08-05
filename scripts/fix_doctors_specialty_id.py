# Path: scripts/fix_doctors_specialty_id.py

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


MIGRATION_SQL = """
BEGIN;

-- ============================================================
-- 1) Create specialties table if it does not exist
-- ============================================================

CREATE TABLE IF NOT EXISTS specialties (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE
);

-- ============================================================
-- 2) Seed default specialties
-- ============================================================

INSERT INTO specialties (id, name, slug)
VALUES
    (1, 'پزشک عمومی', 'general-practitioner'),
    (2, 'متخصص قلب و عروق', 'cardiology'),
    (3, 'متخصص پوست و مو', 'dermatology'),
    (4, 'متخصص مغز و اعصاب', 'neurology'),
    (5, 'متخصص ارتوپدی', 'orthopedics'),
    (6, 'متخصص اطفال', 'pediatrics'),
    (7, 'متخصص زنان و زایمان', 'gynecology'),
    (8, 'متخصص داخلی', 'internal-medicine'),
    (9, 'دندانپزشک', 'dentistry'),
    (10, 'روانپزشک', 'psychiatry')
ON CONFLICT (id) DO NOTHING;

INSERT INTO specialties (name, slug)
VALUES
    ('پزشک عمومی', 'general-practitioner'),
    ('متخصص قلب و عروق', 'cardiology'),
    ('متخصص پوست و مو', 'dermatology'),
    ('متخصص مغز و اعصاب', 'neurology'),
    ('متخصص ارتوپدی', 'orthopedics'),
    ('متخصص اطفال', 'pediatrics'),
    ('متخصص زنان و زایمان', 'gynecology'),
    ('متخصص داخلی', 'internal-medicine'),
    ('دندانپزشک', 'dentistry'),
    ('روانپزشک', 'psychiatry')
ON CONFLICT DO NOTHING;

SELECT setval(
    pg_get_serial_sequence('specialties', 'id'),
    COALESCE((SELECT MAX(id) FROM specialties), 1),
    true
);

-- ============================================================
-- 3) Add specialty_id column to doctors if missing
-- ============================================================

ALTER TABLE doctors
ADD COLUMN IF NOT EXISTS specialty_id INTEGER;

-- ============================================================
-- 4) Migrate old doctors.specialty text to doctors.specialty_id
-- ============================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'doctors'
          AND column_name = 'specialty'
    ) THEN

        UPDATE doctors d
        SET specialty_id = s.id
        FROM specialties s
        WHERE d.specialty_id IS NULL
          AND d.specialty IS NOT NULL
          AND TRIM(d.specialty) = s.name;

        UPDATE doctors
        SET specialty_id = 1
        WHERE specialty_id IS NULL
          AND specialty IS NOT NULL
          AND TRIM(specialty) IN (
              'عمومی',
              'پزشک عمومی',
              'general',
              'general-practitioner'
          );

        UPDATE doctors
        SET specialty_id = 2
        WHERE specialty_id IS NULL
          AND specialty IS NOT NULL
          AND TRIM(specialty) IN (
              'قلب',
              'قلب و عروق',
              'متخصص قلب',
              'متخصص قلب و عروق',
              'cardiology'
          );

        UPDATE doctors
        SET specialty_id = 3
        WHERE specialty_id IS NULL
          AND specialty IS NOT NULL
          AND TRIM(specialty) IN (
              'پوست',
              'پوست و مو',
              'متخصص پوست',
              'متخصص پوست و مو',
              'dermatology'
          );

        UPDATE doctors
        SET specialty_id = 4
        WHERE specialty_id IS NULL
          AND specialty IS NOT NULL
          AND TRIM(specialty) IN (
              'مغز و اعصاب',
              'نورولوژی',
              'متخصص مغز و اعصاب',
              'neurology'
          );

        UPDATE doctors
        SET specialty_id = 5
        WHERE specialty_id IS NULL
          AND specialty IS NOT NULL
          AND TRIM(specialty) IN (
              'ارتوپدی',
              'متخصص ارتوپدی',
              'orthopedics'
          );

        UPDATE doctors
        SET specialty_id = 6
        WHERE specialty_id IS NULL
          AND specialty IS NOT NULL
          AND TRIM(specialty) IN (
              'اطفال',
              'متخصص اطفال',
              'pediatrics'
          );

        UPDATE doctors
        SET specialty_id = 7
        WHERE specialty_id IS NULL
          AND specialty IS NOT NULL
          AND TRIM(specialty) IN (
              'زنان',
              'زنان و زایمان',
              'متخصص زنان',
              'متخصص زنان و زایمان',
              'gynecology'
          );

        UPDATE doctors
        SET specialty_id = 8
        WHERE specialty_id IS NULL
          AND specialty IS NOT NULL
          AND TRIM(specialty) IN (
              'داخلی',
              'متخصص داخلی',
              'internal-medicine'
          );

        UPDATE doctors
        SET specialty_id = 9
        WHERE specialty_id IS NULL
          AND specialty IS NOT NULL
          AND TRIM(specialty) IN (
              'دندان',
              'دندانپزشک',
              'دندان پزشکی',
              'dentistry'
          );

        UPDATE doctors
        SET specialty_id = 10
        WHERE specialty_id IS NULL
          AND specialty IS NOT NULL
          AND TRIM(specialty) IN (
              'روانپزشک',
              'روان پزشکی',
              'psychiatry'
          );

    END IF;
END $$;

-- fallback for existing doctors
UPDATE doctors
SET specialty_id = 1
WHERE specialty_id IS NULL;

-- ============================================================
-- 5) Add foreign key safely
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_doctors_specialty_id'
    ) THEN
        ALTER TABLE doctors
        ADD CONSTRAINT fk_doctors_specialty_id
        FOREIGN KEY (specialty_id)
        REFERENCES specialties(id)
        ON DELETE RESTRICT;
    END IF;
END $$;

-- ============================================================
-- 6) Make specialty_id NOT NULL
-- ============================================================

ALTER TABLE doctors
ALTER COLUMN specialty_id SET NOT NULL;

-- ============================================================
-- 7) Helpful index
-- ============================================================

CREATE INDEX IF NOT EXISTS ix_doctors_specialty_id
ON doctors (specialty_id);

COMMIT;
"""


CHECK_SQL = """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'doctors'
  AND column_name IN ('specialty', 'specialty_id')
ORDER BY column_name;
"""


SPECIALTIES_SQL = """
SELECT id, name, slug
FROM specialties
ORDER BY id;
"""


def normalize_database_url(database_url: str) -> str:
    """
    بعضی سرویس‌ها URL را با postgres:// می‌دهند.
    SQLAlchemy جدید postgresql:// را ترجیح می‌دهد.
    """
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)

    return database_url


def main() -> None:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        print("This script must be run on Render Shell or with DATABASE_URL configured.")
        sys.exit(1)

    database_url = normalize_database_url(database_url)

    print("Connecting to database...")
    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            print("Running migration...")
            connection.execute(text(MIGRATION_SQL))
            connection.commit()

            print("\nMigration completed successfully.")

            print("\nDoctors specialty columns:")
            result = connection.execute(text(CHECK_SQL))
            for row in result:
                print(dict(row._mapping))

            print("\nSpecialties:")
            result = connection.execute(text(SPECIALTIES_SQL))
            for row in result:
                print(dict(row._mapping))

    except SQLAlchemyError as exc:
        print("\nMigration failed.")
        print(type(exc).__name__)
        print(str(exc))
        sys.exit(1)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
