"""store resource sync import results

Revision ID: e81b4f239a70
Revises: c4a8d9197e52
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e81b4f239a70"
down_revision: Union[str, None] = "c4a8d9197e52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("resource_sync_jobs")}
    if "result" not in columns:
        with op.batch_alter_table("resource_sync_jobs") as batch:
            batch.add_column(sa.Column("result", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    with op.batch_alter_table("resource_sync_jobs") as batch:
        batch.drop_column("result")
