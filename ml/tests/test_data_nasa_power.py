from unittest.mock import MagicMock, patch
from agriscope_ml.data.nasa_power import NasaPowerClient, QCReport


def make_mock_nasa_json():
    """Build mock NASA POWER JSON payload for two days."""
    return {
        "properties": {
            "parameter": {
                "T2M": {"20220601": 32.5, "20220602": -999.0},
                "T2M_MAX": {"20220601": 38.0, "20220602": -999.0},
                "T2M_MIN": {"20220601": 27.0, "20220602": -999.0},
                "RH2M": {"20220601": 55.0, "20220602": -999.0},
                "WS2M": {"20220601": 2.5, "20220602": -999.0},
                "ALLSKY_SFC_SW_DWN": {"20220601": 24.5, "20220602": -999.0},
                "PRECTOTCORR": {"20220601": 0.0, "20220602": 0.0},
            }
        }
    }


def test_nasa_power_processing_and_qc(tmp_path):
    """Test JSON parsing, QC clipping of -999 fill values, and ET calculation."""
    client = NasaPowerClient(cache_dir=tmp_path)
    mock_json = make_mock_nasa_json()
    station = {
        "name": "Faisalabad",
        "lat": 31.4187,
        "lon": 73.0791,
        "elevation": 184.0,
        "country": "Pakistan",
    }

    report = QCReport()
    df = client.process_station_dataframe(mock_json, station, qc_report=report)

    # Day 20220601 should pass, Day 20220602 should be clipped as fill value
    assert len(df) == 1
    assert report.records_total == 2
    assert report.records_valid == 1
    assert report.outliers_clipped == 1

    row = df.iloc[0]
    assert row["location_name"] == "Faisalabad"
    assert row["country"] == "Pakistan"
    assert row["temperature"] == 32.5
    assert row["tmax"] == 38.0
    assert row["tmin"] == 27.0
    assert row["humidity"] == 55.0
    assert row["wind_speed"] == 2.5
    assert row["solar_radiation"] == 24.5
    assert row["provenance"] == "nasa_power"
    assert not row["is_synthetic"]

    # ET0 should be computed via FAO-56 Penman-Monteith
    assert 5.0 <= row["et"] <= 8.5


@patch("httpx.Client")
def test_nasa_power_fetch_with_mocked_network(mock_client_class, tmp_path):
    """Test offline fetch with mocked HTTP response and caching."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = make_mock_nasa_json()
    mock_resp.raise_for_status.return_value = None

    mock_client = MagicMock()
    mock_client.__enter__.return_value.get.return_value = mock_resp
    mock_client_class.return_value = mock_client

    client = NasaPowerClient(cache_dir=tmp_path, rate_limit_delay=0.0)
    data = client.fetch_station_daily(lat=31.4187, lon=73.0791, use_cache=True)

    assert "properties" in data
    # Cache file should now exist on disk
    cache_files = list(tmp_path.glob("*.json"))
    assert len(cache_files) == 1
