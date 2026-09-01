"""composite curriculum, practice, SRS and reading models

Revision ID: 8f36c0e53f21
Revises: d06d8292e4e4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8f36c0e53f21"
down_revision: Union[str, None] = "d06d8292e4e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("exercises") as batch:
        batch.add_column(sa.Column("options", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("explanation", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("score", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("source", sa.String(200), nullable=False, server_default=""))
    with op.batch_alter_table("learning_sessions") as batch:
        batch.add_column(sa.Column("lesson_id", sa.String(), nullable=True))
        batch.create_foreign_key("fk_learning_session_lesson", "lessons", ["lesson_id"], ["id"])
        batch.create_index("ix_learning_sessions_lesson_id", ["lesson_id"])
    with op.batch_alter_table("mistakes") as batch:
        batch.add_column(sa.Column("exercise_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("srs_box", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("review_correct_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("last_reviewed_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("next_review_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("graduated", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_foreign_key("fk_mistake_exercise", "exercises", ["exercise_id"], ["id"])
        batch.create_index("ix_mistakes_exercise_id", ["exercise_id"])
        batch.create_index("ix_mistakes_next_review_at", ["next_review_at"])

    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("student_id", sa.String(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("lesson_id", sa.String(), sa.ForeignKey("lessons.id"), nullable=False),
        sa.Column("best_accuracy", sa.Float(), nullable=False, server_default="0"),
        sa.Column("stars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_completed_at", sa.DateTime(), nullable=True),
        sa.Column("last_completed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("student_id", "lesson_id", name="uq_lesson_progress"),
    )
    op.create_index("ix_lesson_progress_student_id", "lesson_progress", ["student_id"])
    op.create_index("ix_lesson_progress_lesson_id", "lesson_progress", ["lesson_id"])

    op.create_table(
        "stories",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("subject_id", sa.String(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("external_id", sa.String(150), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cover_path", sa.String(500), nullable=True),
        sa.Column("source", sa.String(200), nullable=False, server_default=""),
    )
    op.create_index("ix_stories_subject_id", "stories", ["subject_id"])
    op.create_table(
        "story_sentences",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("story_id", sa.String(), sa.ForeignKey("stories.id"), nullable=False),
        sa.Column("audio_asset_id", sa.String(), sa.ForeignKey("audio_assets.id"), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("translation", sa.Text(), nullable=False, server_default=""),
        sa.Column("image_path", sa.String(500), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.UniqueConstraint("story_id", "position", name="uq_story_sentence"),
    )
    op.create_index("ix_story_sentences_story_id", "story_sentences", ["story_id"])

    with op.batch_alter_table("reading_progress") as batch:
        batch.drop_constraint("uq_reading_progress", type_="unique")
        batch.alter_column("passage_id", existing_type=sa.String(), nullable=True)
        batch.add_column(sa.Column("content_kind", sa.String(20), nullable=False, server_default="passage"))
        batch.add_column(sa.Column("content_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE reading_progress SET content_id = passage_id WHERE content_id IS NULL")
    with op.batch_alter_table("reading_progress") as batch:
        batch.alter_column("content_id", existing_type=sa.String(), nullable=False)
        batch.create_index("ix_reading_progress_content_id", ["content_id"])
        batch.create_unique_constraint("uq_reading_content_progress", ["student_id", "content_kind", "content_id"])


def downgrade() -> None:
    with op.batch_alter_table("reading_progress") as batch:
        batch.drop_constraint("uq_reading_content_progress", type_="unique")
        batch.drop_index("ix_reading_progress_content_id")
        batch.drop_column("completed_at")
        batch.drop_column("content_id")
        batch.drop_column("content_kind")
        batch.alter_column("passage_id", existing_type=sa.String(), nullable=False)
        batch.create_unique_constraint("uq_reading_progress", ["student_id", "passage_id"])
    op.drop_index("ix_story_sentences_story_id", table_name="story_sentences")
    op.drop_table("story_sentences")
    op.drop_index("ix_stories_subject_id", table_name="stories")
    op.drop_table("stories")
    op.drop_index("ix_lesson_progress_lesson_id", table_name="lesson_progress")
    op.drop_index("ix_lesson_progress_student_id", table_name="lesson_progress")
    op.drop_table("lesson_progress")
    with op.batch_alter_table("mistakes") as batch:
        batch.drop_index("ix_mistakes_next_review_at")
        batch.drop_index("ix_mistakes_exercise_id")
        batch.drop_constraint("fk_mistake_exercise", type_="foreignkey")
        for name in ("graduated", "next_review_at", "last_reviewed_at", "review_correct_count", "srs_box", "exercise_id"):
            batch.drop_column(name)
    with op.batch_alter_table("learning_sessions") as batch:
        batch.drop_index("ix_learning_sessions_lesson_id")
        batch.drop_constraint("fk_learning_session_lesson", type_="foreignkey")
        batch.drop_column("lesson_id")
    with op.batch_alter_table("exercises") as batch:
        for name in ("source", "score", "explanation", "options"):
            batch.drop_column(name)
