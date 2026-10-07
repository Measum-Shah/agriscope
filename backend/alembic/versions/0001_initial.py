"""create initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-10-06 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='free'),
        sa.Column('plan', sa.String(length=50), nullable=False, server_default='free'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('totp_secret', sa.String(length=255), nullable=True),
        sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('failed_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('registration_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 2. sessions
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_family', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hashed_token', sa.String(length=255), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('reuse_detected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('ix_sessions_token_family', 'sessions', ['token_family'])
    op.create_index('ix_sessions_hashed_token', 'sessions', ['hashed_token'], unique=True)

    # 3. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('actor', sa.String(length=255), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('target', sa.String(length=255), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_audit_logs_actor_timestamp', 'audit_logs', ['actor', 'timestamp'])

    # 4. crops
    op.create_table(
        'crops',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('scientific_name', sa.String(length=150), nullable=True),
        sa.Column('kc_ini', sa.Float(), nullable=False),
        sa.Column('kc_mid', sa.Float(), nullable=False),
        sa.Column('kc_end', sa.Float(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_crops_name', 'crops', ['name'], unique=True)

    # 5. crop_stages
    op.create_table(
        'crop_stages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('crop_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('crops.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stage_name', sa.String(length=50), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=False),
    )
    op.create_index('ix_crop_stages_crop_id', 'crop_stages', ['crop_id'])

    # 6. fields
    op.create_table(
        'fields',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('crop_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('crops.id', ondelete='SET NULL'), nullable=True),
        sa.Column('planting_date', sa.Date(), nullable=True),
        sa.Column('area_ha', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('geometry', geoalchemy2.types.Geometry(geometry_type='GEOMETRY', srid=4326, spatial_index=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_fields_user_id', 'fields', ['user_id'])
    op.create_index('ix_fields_crop_id', 'fields', ['crop_id'])
    op.create_index('ix_fields_user_name', 'fields', ['user_id', 'name'])
    op.create_index('idx_fields_geometry', 'fields', ['geometry'], postgresql_using='gist')

    # 7. field_observations
    op.create_table(
        'field_observations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('field_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fields.id', ondelete='CASCADE'), nullable=False),
        sa.Column('observation_date', sa.Date(), nullable=False),
        sa.Column('ndvi', sa.Float(), nullable=True),
        sa.Column('evi', sa.Float(), nullable=True),
        sa.Column('ndwi', sa.Float(), nullable=True),
        sa.Column('cloud_cover_pct', sa.Float(), nullable=True),
        sa.Column('et0', sa.Float(), nullable=True),
        sa.Column('kc', sa.Float(), nullable=True),
        sa.Column('etc', sa.Float(), nullable=True),
        sa.Column('rain_mm', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('cloud_cover_pct >= 0 AND cloud_cover_pct <= 100', name='chk_obs_cloud_pct'),
    )
    op.create_index('ix_field_observations_field_id', 'field_observations', ['field_id'])
    op.create_index('ix_field_observations_field_date', 'field_observations', ['field_id', 'observation_date'])

    # 8. training_datasets
    op.create_table(
        'training_datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('file_uri', sa.String(length=500), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ready'),
        sa.Column('data_provenance', sa.String(length=50), nullable=False, server_default='real_derived'),
        sa.Column('stats_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 9. ml_models
    op.create_table(
        'ml_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('algorithm', sa.String(length=100), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('training_datasets.id', ondelete='SET NULL'), nullable=True),
        sa.Column('feature_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('metrics_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('artifact_uri', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending_approval'),
        sa.Column('trained_by', sa.String(length=255), nullable=True),
        sa.Column('data_provenance', sa.String(length=50), nullable=False, server_default='real_derived'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_ml_models_version', 'ml_models', ['version'], unique=True)
    op.create_index('ix_ml_models_dataset_id', 'ml_models', ['dataset_id'])
    op.create_index('ix_ml_models_status', 'ml_models', ['status'])

    # 10. batch_jobs
    op.create_table(
        'batch_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('input_file_uri', sa.String(length=500), nullable=False),
        sa.Column('output_file_uri', sa.String(length=500), nullable=True),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_batch_jobs_user_id', 'batch_jobs', ['user_id'])

    # 11. predictions
    op.create_table(
        'predictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ml_models.id', ondelete='SET NULL'), nullable=True),
        sa.Column('field_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fields.id', ondelete='SET NULL'), nullable=True),
        sa.Column('batch_job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('batch_jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='manual'),
        sa.Column('temperature', sa.Float(), nullable=False),
        sa.Column('humidity', sa.Float(), nullable=False),
        sa.Column('wind_speed', sa.Float(), nullable=False),
        sa.Column('solar_radiation', sa.Float(), nullable=False),
        sa.Column('tmin', sa.Float(), nullable=True),
        sa.Column('tmax', sa.Float(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('elevation_m', sa.Float(), nullable=True),
        sa.Column('day_of_year', sa.Float(), nullable=True),
        sa.Column('et_value', sa.Float(), nullable=False),
        sa.Column('interval_low', sa.Float(), nullable=True),
        sa.Column('interval_high', sa.Float(), nullable=True),
        sa.Column('classification', sa.String(length=50), nullable=False, server_default='moderate'),
        sa.Column('is_saved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('note', sa.String(length=1000), nullable=True),
        sa.Column('feature_contributions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('temperature >= -10 AND temperature <= 50', name='chk_pred_temp_range'),
        sa.CheckConstraint('humidity >= 0 AND humidity <= 100', name='chk_pred_humidity_range'),
        sa.CheckConstraint('wind_speed >= 0 AND wind_speed <= 30', name='chk_pred_wind_range'),
        sa.CheckConstraint('solar_radiation >= 0 AND solar_radiation <= 35', name='chk_pred_solar_range'),
    )
    op.create_index('ix_predictions_user_id', 'predictions', ['user_id'])
    op.create_index('ix_predictions_user_timestamp', 'predictions', ['user_id', 'timestamp'])

    # 12. irrigation_events
    op.create_table(
        'irrigation_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('field_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('fields.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('water_applied_mm', sa.Float(), nullable=False),
        sa.Column('method', sa.String(length=50), nullable=False, server_default='drip'),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_irrigation_events_field_id', 'irrigation_events', ['field_id'])

    # 13. shadow_results
    op.create_table(
        'shadow_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('prediction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('predictions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ml_models.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_et_value', sa.Float(), nullable=False),
        sa.Column('difference_from_active', sa.Float(), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_shadow_results_prediction_id', 'shadow_results', ['prediction_id'])
    op.create_index('ix_shadow_results_model_id', 'shadow_results', ['model_id'])

    # 14. notifications
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.String(length=1000), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False, server_default='info'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])

    # 15. notification_preferences
    op.create_table(
        'notification_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sms_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('in_app_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('irrigation_alerts', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('system_announcements', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_notification_preferences_user_id', 'notification_preferences', ['user_id'], unique=True)

    # 16. api_keys
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('key_prefix', sa.String(length=8), nullable=False),
        sa.Column('hashed_key', sa.String(length=255), nullable=False),
        sa.Column('rate_limit_per_min', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('scopes', sa.String(length=255), nullable=False, server_default='predict:read,predict:write,batch:write,weather:read,fields:read'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])
    op.create_index('ix_api_keys_hashed_key', 'api_keys', ['hashed_key'], unique=True)

    # 17. reports
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('format', sa.String(length=20), nullable=False),
        sa.Column('file_uri', sa.String(length=500), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='completed'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_reports_user_id', 'reports', ['user_id'])

    # 18. subscriptions
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan', sa.String(length=50), nullable=False, server_default='pro'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('stripe_customer_id', sa.String(length=100), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(length=100), nullable=True),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_stripe_customer_id', 'subscriptions', ['stripe_customer_id'])
    op.create_index('ix_subscriptions_stripe_subscription_id', 'subscriptions', ['stripe_subscription_id'])

    # 19. feature_flags
    op.create_table(
        'feature_flags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rules_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_feature_flags_name', 'feature_flags', ['name'], unique=True)

    # 20. announcements
    op.create_table(
        'announcements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.String(length=2000), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False, server_default='info'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('announcements')
    op.drop_table('feature_flags')
    op.drop_table('subscriptions')
    op.drop_table('reports')
    op.drop_table('api_keys')
    op.drop_table('notification_preferences')
    op.drop_table('notifications')
    op.drop_table('shadow_results')
    op.drop_table('irrigation_events')
    op.drop_table('predictions')
    op.drop_table('batch_jobs')
    op.drop_table('ml_models')
    op.drop_table('training_datasets')
    op.drop_table('field_observations')
    op.drop_table('fields')
    op.drop_table('crop_stages')
    op.drop_table('crops')
    op.drop_table('audit_logs')
    op.drop_table('sessions')
    op.drop_table('users')
