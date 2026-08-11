"""Create patients table."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("patient_id", sa.Uuid(), primary_key=True),
        sa.Column("first_name", sa.String(50), nullable=False),
        sa.Column("last_name", sa.String(50), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("sex", sa.Enum("male", "female", "other", "decline", name="sex", native_enum=False), nullable=False),
        sa.Column("phone_number", sa.String(16), nullable=False),
        sa.Column("email", sa.String(254)),
        sa.Column("address_line_1", sa.String(200), nullable=False),
        sa.Column("address_line_2", sa.String(100)),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("zip_code", sa.String(10), nullable=False),
        sa.Column("insurance_provider", sa.String(150)),
        sa.Column("insurance_member_id", sa.String(100)),
        sa.Column("preferred_language", sa.String(50), nullable=False, server_default="English"),
        sa.Column("emergency_contact_name", sa.String(100)),
        sa.Column("emergency_contact_phone", sa.String(16)),
        sa.Column("idempotency_key", sa.String(150), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_patients_last_name", "patients", ["last_name"])
    op.create_index("ix_patients_date_of_birth", "patients", ["date_of_birth"])
    op.create_index("ix_patients_phone_number", "patients", ["phone_number"])


def downgrade() -> None:
    op.drop_table("patients")

