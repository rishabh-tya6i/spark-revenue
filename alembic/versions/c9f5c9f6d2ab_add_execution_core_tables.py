"""Add execution core tables

Revision ID: c9f5c9f6d2ab
Revises: fbdeebd62f22
Create Date: 2026-05-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9f5c9f6d2ab"
down_revision: Union[str, Sequence[str], None] = "fbdeebd62f22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # execution_accounts
    op.create_table(
        "execution_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("base_currency", sa.String(), nullable=False),
        sa.Column("initial_balance", sa.Float(), nullable=False),
        sa.Column("cash_balance", sa.Float(), nullable=False),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_ts", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_execution_accounts_id"), "execution_accounts", ["id"], unique=False)

    # execution_positions
    op.create_table(
        "execution_positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("avg_price", sa.Float(), nullable=False),
        sa.Column("updated_ts", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["execution_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_execution_positions_id"), "execution_positions", ["id"], unique=False)
    op.create_index(op.f("ix_execution_positions_symbol"), "execution_positions", ["symbol"], unique=False)

    # execution_orders
    op.create_table(
        "execution_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("decision_id", sa.Integer(), nullable=True),
        sa.Column("created_ts", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["execution_accounts.id"]),
        sa.ForeignKeyConstraint(["decision_id"], ["decision_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_execution_orders_id"), "execution_orders", ["id"], unique=False)
    op.create_index(op.f("ix_execution_orders_symbol"), "execution_orders", ["symbol"], unique=False)

    # execution_pnl
    op.create_table(
        "execution_pnl",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unrealized_pnl", sa.Float(), nullable=False),
        sa.Column("realized_pnl", sa.Float(), nullable=False),
        sa.Column("equity", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["execution_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_execution_pnl_id"), "execution_pnl", ["id"], unique=False)
    op.create_index(op.f("ix_execution_pnl_symbol"), "execution_pnl", ["symbol"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_execution_pnl_symbol"), table_name="execution_pnl")
    op.drop_index(op.f("ix_execution_pnl_id"), table_name="execution_pnl")
    op.drop_table("execution_pnl")

    op.drop_index(op.f("ix_execution_orders_symbol"), table_name="execution_orders")
    op.drop_index(op.f("ix_execution_orders_id"), table_name="execution_orders")
    op.drop_table("execution_orders")

    op.drop_index(op.f("ix_execution_positions_symbol"), table_name="execution_positions")
    op.drop_index(op.f("ix_execution_positions_id"), table_name="execution_positions")
    op.drop_table("execution_positions")

    op.drop_index(op.f("ix_execution_accounts_id"), table_name="execution_accounts")
    op.drop_table("execution_accounts")

