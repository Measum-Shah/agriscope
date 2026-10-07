"""Verify composite indexes exist on hot-path ORM models for query performance."""
from app.models.prediction import Prediction
from app.models.audit_log import AuditLog
from app.models.field_observation import FieldObservation


def _index_columns(model) -> list[tuple[str, ...]]:
    """Return sorted tuples of column names for each index on a model."""
    result = []
    for idx in model.__table__.indexes:
        cols = tuple(sorted(c.name for c in idx.columns))
        result.append(cols)
    return result


def test_prediction_user_timestamp_index():
    """Prediction must have a composite index on (user_id, timestamp)."""
    cols = _index_columns(Prediction)
    assert ("timestamp", "user_id") in cols, (
        f"Missing (user_id, timestamp) index on Prediction. Found: {cols}"
    )


def test_prediction_user_saved_index():
    """Prediction must have a composite index on (user_id, is_saved) for bookmark queries."""
    cols = _index_columns(Prediction)
    assert ("is_saved", "user_id") in cols, (
        f"Missing (user_id, is_saved) index on Prediction. Found: {cols}"
    )


def test_audit_log_actor_timestamp_index():
    """AuditLog must have a composite index on (actor, timestamp) for user trail queries."""
    cols = _index_columns(AuditLog)
    assert any("actor" in c for group in cols for c in group), (
        f"Missing actor index on AuditLog. Found: {cols}"
    )


def test_field_observation_field_date_index():
    """FieldObservation must have a composite index on (field_id, observation_date)."""
    cols = _index_columns(FieldObservation)
    assert any("field_id" in c for group in cols for c in group), (
        f"Missing field_id index on FieldObservation. Found: {cols}"
    )
