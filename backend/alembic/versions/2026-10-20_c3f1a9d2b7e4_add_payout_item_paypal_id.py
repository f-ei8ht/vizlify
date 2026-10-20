"""add payout item paypal id

Revision ID: c3f1a9d2b7e4
Revises: a1dc76bf447b
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3f1a9d2b7e4"
down_revision: str | None = "a1dc76bf447b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("payout_items", sa.Column("paypal_item_id", sa.String(length=255), nullable=True))
    op.create_index(
        op.f("ix_payout_items_paypal_item_id"), "payout_items", ["paypal_item_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_payout_items_paypal_item_id"), table_name="payout_items")
    op.drop_column("payout_items", "paypal_item_id")
