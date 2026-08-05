"""sync specialty schema

Revision ID: 2026_08_05_sync
Revises: f3de37c22046
Create Date: 2026-08-05 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2026_08_05_sync'
down_revision = 'f3de37c22046'
branch_labels = None
depends_on = None


def upgrade():
    # 1. ایجاد جدول تخصص‌ها اگر وجود ندارد
    op.execute("""
               CREATE TABLE IF NOT EXISTS specialties
               (
                   id
                   SERIAL
                   PRIMARY
                   KEY,
                   name
                   VARCHAR
               (
                   120
               ) NOT NULL,
                   slug VARCHAR
               (
                   120
               ) UNIQUE NOT NULL,
                   description TEXT
                   )
               """)

    # 2. بررسی وجود ستون specialty_id در جدول doctors
    # اگر وجود ندارد آن را اضافه می‌کنیم
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('doctors')]

    if 'specialty_id' not in columns:
        op.add_column('doctors',
                      sa.Column('specialty_id', sa.Integer(), sa.ForeignKey('specialties.id', ondelete='SET NULL'),
                                nullable=True))
        op.create_index(op.f('ix_doctors_specialty_id'), 'doctors', ['specialty_id'], unique=False)

    # 3. انتقال داده‌ها از ستون قدیمی specialty به جدول جدید و ستون جدید
    # این بخش بسیار مهم است تا اطلاعات پزشکان پاک نشود
    if 'specialty' in columns:
        # وارد کردن تخصص‌های منحصربفرد به جدول specialties
        op.execute("""
                   INSERT INTO specialties (name, slug)
                   SELECT DISTINCT specialty, LOWER(REPLACE(specialty, ' ', '-'))
                   FROM doctors
                   WHERE specialty IS NOT NULL ON CONFLICT (slug) DO NOTHING
                   """)

        # آپدیت کردن specialty_id بر اساس نام تخصص
        op.execute("""
                   UPDATE doctors
                   SET specialty_id = specialties.id FROM specialties
                   WHERE doctors.specialty = specialties.name
                   """)

        # حالا که داده‌ها منتقل شدند، ستون قدیمی را حذف می‌کنیم تا خطا ندهد
        op.drop_column('doctors', 'specialty')


def downgrade():
    # در صورت بازگشت، ستون قدیمی را برمی‌گردانیم (اختیاری)
    op.add_column('doctors', sa.Column('specialty', sa.String(length=120), nullable=True))
