"""admin settings and resource jobs

Revision ID: c4a8d9197e52
Revises: 8f36c0e53f21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c4a8d9197e52"
down_revision: Union[str, None] = "8f36c0e53f21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("resource_sync_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("requested_by_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False), sa.Column("stage", sa.String(30), nullable=False),
        sa.Column("current_package", sa.String(80), nullable=True),
        sa.Column("downloaded_bytes", sa.Integer(), nullable=False), sa.Column("total_bytes", sa.Integer(), nullable=False),
        sa.Column("packages", sa.JSON(), nullable=False), sa.Column("error", sa.Text(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True), sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_index("ix_resource_sync_jobs_requested_by_id", "resource_sync_jobs", ["requested_by_id"])
    op.create_index("ix_resource_sync_jobs_status", "resource_sync_jobs", ["status"])
    op.create_table("admin_audit_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(80), nullable=False), sa.Column("changed_fields", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_admin_audit_logs_user_id", "admin_audit_logs", ["user_id"])
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"])
    op.execute("UPDATE users SET role='admin' WHERE id=(SELECT id FROM users ORDER BY created_at, id LIMIT 1)")


def downgrade() -> None:
    op.execute("UPDATE users SET role='parent' WHERE role='admin'")
    op.drop_index("ix_admin_audit_logs_action", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_user_id", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
    op.drop_index("ix_resource_sync_jobs_status", table_name="resource_sync_jobs")
    op.drop_index("ix_resource_sync_jobs_requested_by_id", table_name="resource_sync_jobs")
    op.drop_table("resource_sync_jobs")
