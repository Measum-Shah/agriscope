# AgriScope Architecture

This document describes the high-level system architecture, service topology, and data model.

---

## Entity Relationship (ER) Diagram

The diagram below reflects all 20 domain models implemented in `backend/app/models/` and registered with SQLAlchemy 2.0 / Alembic.

```mermaid
erDiagram
    users ||--o{ sessions : "has"
    users ||--o{ predictions : "creates"
    users ||--o{ fields : "owns"
    users ||--o{ batch_jobs : "submits"
    users ||--o{ api_keys : "owns"
    users ||--o{ reports : "generates"
    users ||--o{ subscriptions : "holds"
    users ||--o{ notifications : "receives"
    users ||--o| notification_preferences : "configures"

    crops ||--o{ crop_stages : "defines"
    crops ||--o{ fields : "planted_in"

    fields ||--o{ field_observations : "monitors"
    fields ||--o{ irrigation_events : "records"
    fields ||--o{ predictions : "associated_with"

    training_datasets ||--o{ ml_models : "trains"

    ml_models ||--o{ predictions : "generates"
    ml_models ||--o{ shadow_results : "evaluates"

    predictions ||--o{ shadow_results : "compared_in"
    batch_jobs ||--o{ predictions : "produces"

    users {
        uuid id PK
        string name
        string email UK
        string password_hash
        string role
        string plan
        string status
        boolean email_verified
        string totp_secret
        boolean totp_enabled
        int failed_attempts
        datetime locked_until
        datetime registration_date
        datetime last_login
    }

    sessions {
        uuid id PK
        uuid user_id FK
        uuid token_family
        string hashed_token UK
        string ip_address
        string user_agent
        datetime expires_at
        boolean revoked
        boolean reuse_detected
    }

    audit_logs {
        uuid id PK
        string actor
        string action
        string target
        jsonb metadata_json
        string ip_address
        string user_agent
        datetime timestamp
    }

    crops {
        uuid id PK
        string name UK
        string scientific_name
        float kc_ini
        float kc_mid
        float kc_end
        string description
    }

    crop_stages {
        uuid id PK
        uuid crop_id FK
        string stage_name
        int duration_days
    }

    fields {
        uuid id PK
        uuid user_id FK
        string name
        uuid crop_id FK
        date planting_date
        float area_ha
        geometry geometry
    }

    field_observations {
        uuid id PK
        uuid field_id FK
        date observation_date
        float ndvi
        float evi
        float ndwi
        float cloud_cover_pct
        float et0
        float kc
        float etc
        float rain_mm
    }

    predictions {
        uuid id PK
        uuid user_id FK
        uuid model_id FK
        uuid field_id FK
        uuid batch_job_id FK
        string source
        float temperature
        float humidity
        float wind_speed
        float solar_radiation
        float tmin
        float tmax
        float latitude
        float elevation_m
        float day_of_year
        float et_value
        float interval_low
        float interval_high
        string classification
        boolean is_saved
        string_array tags
        string note
        jsonb feature_contributions
        datetime timestamp
    }

    batch_jobs {
        uuid id PK
        uuid user_id FK
        string status
        string input_file_uri
        string output_file_uri
        int total_rows
        int processed_rows
        jsonb error_summary
    }

    training_datasets {
        uuid id PK
        string name
        string version
        string file_uri
        string file_hash
        string status
        string data_provenance
        jsonb stats_json
        string description
    }

    ml_models {
        uuid id PK
        string name
        string algorithm
        string version UK
        uuid dataset_id FK
        jsonb feature_schema
        jsonb metrics_json
        string artifact_uri
        string status
        string trained_by
        string data_provenance
    }

    shadow_results {
        uuid id PK
        uuid prediction_id FK
        uuid model_id FK
        float candidate_et_value
        float difference_from_active
        float latency_ms
    }

    irrigation_events {
        uuid id PK
        uuid field_id FK
        date event_date
        float water_applied_mm
        string method
        string notes
    }

    notifications {
        uuid id PK
        uuid user_id FK
        string title
        string message
        string type
        boolean is_read
        jsonb metadata_json
    }

    notification_preferences {
        uuid id PK
        uuid user_id FK
        boolean email_enabled
        boolean sms_enabled
        boolean in_app_enabled
        boolean irrigation_alerts
        boolean system_announcements
    }

    api_keys {
        uuid id PK
        uuid user_id FK
        string name
        string key_prefix
        string hashed_key UK
        int rate_limit_per_min
        boolean is_active
        datetime expires_at
        datetime last_used_at
    }

    reports {
        uuid id PK
        uuid user_id FK
        string title
        string format
        string file_uri
        int file_size_bytes
        jsonb parameters
        string status
    }

    subscriptions {
        uuid id PK
        uuid user_id FK
        string plan
        string status
        string stripe_customer_id
        string stripe_subscription_id
        datetime current_period_start
        datetime current_period_end
        boolean cancel_at_period_end
    }

    feature_flags {
        uuid id PK
        string name UK
        string description
        boolean is_enabled
        jsonb rules_json
    }

    announcements {
        uuid id PK
        string title
        string message
        string type
        boolean is_active
        datetime starts_at
        datetime ends_at
    }
```
