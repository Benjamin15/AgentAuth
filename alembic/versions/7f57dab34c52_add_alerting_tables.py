"""add_alerting_tables

Revision ID: 7f57dab34c52
Revises: f4fbc65bd6da
Create Date: 2026-04-02 18:40:41.839069

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "7f57dab34c52"
down_revision: Union[str, Sequence[str], None] = "f4fbc65bd6da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create alert_rules and alert_events tables."""
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("threshold_pct", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("channel", sa.String(), nullable=False, server_default="log"),
        sa.Column("destination", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "alert_events",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("alert_rules.id"), nullable=False),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("triggered_at", sa.DateTime(), nullable=True),
        sa.Column("current_pct", sa.Float(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("delivered", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Drop alert_rules and alert_events tables."""
    op.drop_table("alert_events")
    op.drop_table("alert_rules")
