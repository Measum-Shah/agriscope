"""Test migration script upgrade and downgrade definition."""

import app.models  # noqa: F401
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.db.base import Base


def test_alembic_script_directory_and_revisions():
    """Verify that Alembic discovers the migration chain correctly."""
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    revisions = list(script.walk_revisions())
    assert len(revisions) >= 1
    assert revisions[-1].revision == "0001_initial"


def test_all_models_registered_in_base_metadata():
    """Verify all 20 tables are present in Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    required_tables = {
        "users",
        "sessions",
        "audit_logs",
        "crops",
        "crop_stages",
        "fields",
        "field_observations",
        "training_datasets",
        "ml_models",
        "batch_jobs",
        "predictions",
        "irrigation_events",
        "shadow_results",
        "notifications",
        "notification_preferences",
        "api_keys",
        "reports",
        "subscriptions",
        "feature_flags",
        "announcements",
    }
    missing = required_tables - table_names
    assert not missing, f"Missing tables in Base.metadata: {missing}"
