"""Upgrade both Alembic-managed and legacy create_all databases safely."""
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import engine  # noqa: E402
config = Config(str(ROOT / "alembic.ini"))
config.set_main_option("script_location", str(ROOT / "alembic"))
tables = set(inspect(engine).get_table_names())
required_legacy = {"families", "users", "students", "subjects", "courses", "mistakes"}

if tables and "alembic_version" not in tables:
    if not required_legacy.issubset(tables):
        missing = ", ".join(sorted(required_legacy - tables))
        raise RuntimeError(f"Refusing to stamp an unknown partial database; missing: {missing}")
    command.stamp(config, "d06d8292e4e4")
command.upgrade(config, "head")
