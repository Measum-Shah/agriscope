import subprocess
import sys
import pandas as pd


def test_cli_build_dataset_synthetic(tmp_path):
    """Test running CLI build-dataset with synthetic fallback source."""
    out_dir = str(tmp_path)
    cmd = [
        sys.executable,
        "-m",
        "agriscope_ml.cli",
        "build-dataset",
        "--source",
        "synthetic",
        "--num-samples",
        "100",
        "--output-dir",
        out_dir,
        "--name",
        "test_run",
        "--version",
        "v01",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "Dataset build complete!" in result.stdout

    pq = tmp_path / "test_run_v01.parquet"
    csv = tmp_path / "test_run_v01.csv"
    meta = tmp_path / "test_run_v01_metadata.json"

    assert pq.exists()
    assert csv.exists()
    assert meta.exists()

    df = pd.read_parquet(pq)
    assert len(df) == 100
    assert (df["provenance"] == "synthetic").all()


def test_cli_validate_csv(tmp_path):
    """Test running CLI validate-csv on a valid file."""
    valid_csv = tmp_path / "sample.csv"
    df = pd.DataFrame(
        {
            "temperature": [25.0, 30.0],
            "humidity": [50.0, 60.0],
            "wind_speed": [2.0, 3.0],
            "solar_radiation": [15.0, 20.0],
            "et": [4.0, 5.5],
        }
    )
    df.to_csv(valid_csv, index=False)

    cmd = [
        sys.executable,
        "-m",
        "agriscope_ml.cli",
        "validate-csv",
        "--file",
        str(valid_csv),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "CSV is VALID!" in result.stdout
