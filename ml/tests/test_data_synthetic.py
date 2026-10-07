from agriscope_ml.data.synthetic import generate_synthetic_et_dataset


def test_deterministic_synthetic_generation():
    """Verify that generation with the same seed produces identical datasets."""
    df1 = generate_synthetic_et_dataset(num_samples=100, seed=123)
    df2 = generate_synthetic_et_dataset(num_samples=100, seed=123)

    assert len(df1) == 100
    assert len(df2) == 100
    assert df1.equals(df2)

    # Different seed produces different datasets
    df3 = generate_synthetic_et_dataset(num_samples=100, seed=456)
    assert not df1.equals(df3)


def test_synthetic_provenance_and_boundaries():
    """Verify that all synthetic records are explicitly stamped with synthetic provenance."""
    df = generate_synthetic_et_dataset(num_samples=250, seed=42)

    assert "provenance" in df.columns
    assert "is_synthetic" in df.columns

    # Every single row MUST be stamped as synthetic
    assert (df["provenance"] == "synthetic").all()
    assert df["is_synthetic"].all()

    # Physical meteorological bounds checks
    assert df["temperature"].between(-10.0, 50.0).all()
    assert df["humidity"].between(0.0, 100.0).all()
    assert df["wind_speed"].between(0.0, 30.0).all()
    assert df["solar_radiation"].between(0.0, 35.0).all()
    assert (df["et"] > 0.0).all()
    assert (df["et"] < 20.0).all()
