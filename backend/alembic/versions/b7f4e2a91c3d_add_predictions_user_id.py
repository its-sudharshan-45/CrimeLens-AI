"""Add predictions.user_id and align report_id nullability

Revision ID: b7f4e2a91c3d
Revises: 1c231ba3e6a3
Create Date: 2026-07-25 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b7f4e2a91c3d"
down_revision: Union[str, Sequence[str], None] = "1c231ba3e6a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("predictions", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_predictions_user_id_users"),
        "predictions",
        "users",
        ["user_id"],
        ["id"],
    )
    op.alter_column("predictions", "report_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    op.alter_column("predictions", "report_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint(
        op.f("fk_predictions_user_id_users"),
        "predictions",
        type_="foreignkey",
    )
    op.drop_column("predictions", "user_id")
