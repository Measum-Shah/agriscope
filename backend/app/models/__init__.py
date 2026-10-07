"""Import all models for SQLAlchemy and Alembic metadata discovery."""

from app.db.base import Base
from app.models.announcement import Announcement
from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.models.batch_job import BatchJob
from app.models.crop import Crop, CropStage
from app.models.feature_flag import FeatureFlag
from app.models.field import Field
from app.models.field_observation import FieldObservation
from app.models.irrigation_event import IrrigationEvent
from app.models.ml_model import MLModel
from app.models.notification import Notification, NotificationPreference
from app.models.prediction import Prediction
from app.models.report import Report
from app.models.session import Session
from app.models.shadow_result import ShadowResult
from app.models.subscription import Subscription
from app.models.training_dataset import TrainingDataset
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Session",
    "AuditLog",
    "Crop",
    "CropStage",
    "Field",
    "FieldObservation",
    "TrainingDataset",
    "MLModel",
    "BatchJob",
    "Prediction",
    "IrrigationEvent",
    "ShadowResult",
    "Notification",
    "NotificationPreference",
    "ApiKey",
    "Report",
    "Subscription",
    "FeatureFlag",
    "Announcement",
]
