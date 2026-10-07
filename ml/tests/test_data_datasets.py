import json
import pytest
import pandas as pd
from agriscope_ml.data.datasets import (
    compute_dataframe_hash,
    save_versioned_dataset,
    validate_user_csv,
)
from agriscope_ml.features import (
    BASIC_FEATURE_NAMES,
    EXTENDED_FEATURE_NAMES,
    encode_cyclic_doy,
    extract_features,
    prepare_training_xy,
)


def test_dataframe_hash_determinism():
    """Verify that hash is deterministic and invariant to row order if data is equal."""
    df1 = pd.DataFrame(
        {
            "temperature": [25.0, 30.0],
            "humidity": [50.0, 60.0],
            "wind_speed": [2.0, 3.0],
            "solar_radiation": [15.0, 20.0],
            "et": [4.0, 5.5],
        }
    )
    df2 = df1.copy()

    h1 = compute_dataframe_hash(df1)
    h2 = compute_dataframe_hash(df2)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256


def test_user_csv_schema_validation():
    """Test validation of user CSV uploads."""
    # 1. Valid DataFrame
    valid_df = pd.DataFrame(
        {
            "temperature": [22.0, 28.5],
            "humidity": [45.0, 70.0],
            "wind_speed": [1.5, 3.2],
            "solar_radiation": [18.0, 24.0],
            "et": [3.8, 5.2],
        }
    )
    rep1 = validate_user_csv(valid_df)
    assert rep1.is_valid
    assert len(rep1.errors) == 0

    # 2. Missing required columns
    missing_col_df = pd.DataFrame(
        {
            "temperature": [22.0],
            "humidity": [45.0],
        }
    )
    rep2 = validate_user_csv(missing_col_df)
    assert not rep2.is_valid
    assert any("Missing required columns" in err for err in rep2.errors)

    # 3. Physically invalid values (e.g. humidity = 150%, temperature = 80 °C)
    invalid_phys_df = pd.DataFrame(
        {
            "temperature": [85.0],
            "humidity": [150.0],
            "wind_speed": [2.0],
            "solar_radiation": [20.0],
            "et": [4.0],
        }
    )
    rep3 = validate_user_csv(invalid_phys_df)
    assert not rep3.is_valid
    assert any("outside physical range" in err for err in rep3.errors)


def test_save_versioned_dataset(tmp_path):
    """Test saving dataset as Parquet, CSV, and metadata JSON."""
    df = pd.DataFrame(
        {
            "temperature": [25.0, 30.0, 22.0],
            "humidity": [50.0, 60.0, 75.0],
            "wind_speed": [2.0, 3.0, 1.2],
            "solar_radiation": [15.0, 20.0, 12.0],
            "et": [4.0, 5.5, 3.2],
        }
    )

    pq_path, csv_path, meta = save_versioned_dataset(
        df=df,
        output_dir=tmp_path,
        dataset_name="test_et",
        version="v1",
        provenance="synthetic",
        is_synthetic=True,
    )

    assert pq_path.exists()
    assert csv_path.exists()
    assert (tmp_path / "test_et_v1_metadata.json").exists()

    with open(tmp_path / "test_et_v1_metadata.json", "r") as f:
        meta_json = json.load(f)
    assert meta_json["row_count"] == 3
    assert meta_json["is_synthetic"] is True
    assert meta_json["content_hash"] == meta.content_hash


def test_feature_engineering_basic_and_extended():
    """Verify basic 4-feature and extended feature extraction."""
    df = pd.DataFrame(
        {
            "temperature": [25.0, 30.0],
            "humidity": [50.0, 60.0],
            "wind_speed": [2.0, 3.0],
            "solar_radiation": [15.0, 20.0],
            "et": [4.0, 5.5],
            "doy": [100, 200],
        }
    )

    # Basic schema
    x_basic = extract_features(df, schema="basic")
    assert list(x_basic.columns) == BASIC_FEATURE_NAMES

    # Extended schema
    x_ext = extract_features(df, schema="extended")
    assert all(col in x_ext.columns for col in EXTENDED_FEATURE_NAMES)
    assert "sin_doy" in x_ext.columns
    assert "cos_doy" in x_ext.columns

    # Check cyclic properties: sin^2 + cos^2 = 1
    sin_val, cos_val = encode_cyclic_doy(180)
    assert (sin_val**2 + cos_val**2) == pytest.approx(1.0, abs=1e-4)

    # Prepare training X, y
    x, y = prepare_training_xy(df, schema="basic")
    assert len(x) == 2
    assert len(y) == 2
