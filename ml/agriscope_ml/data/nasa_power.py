"""NASA POWER API client for agroclimatology daily data fetching and QC.

Fetches meteorological variables:
- T2M: Temperature at 2 Meters (°C)
- T2M_MAX: Maximum Temperature at 2 Meters (°C)
- T2M_MIN: Minimum Temperature at 2 Meters (°C)
- RH2M: Relative Humidity at 2 Meters (%)
- WS2M: Wind Speed at 2 Meters (m/s)
- ALLSKY_SFC_SW_DWN: All Sky Surface Shortwave Downward Irradiance (MJ/m²/day)
- PRECTOTCORR: Precipitation Corrected (mm/day)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pandas as pd

from ..physics.penman_monteith import fao56_penman_monteith_full

logger = logging.getLogger(__name__)

NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# 50 diverse agricultural and climatological reference stations
GLOBAL_STATIONS = [
    # Pakistan (Agricultural heartlands and arid zones)
    {
        "name": "Faisalabad",
        "lat": 31.4187,
        "lon": 73.0791,
        "elevation": 184.0,
        "country": "Pakistan",
    },
    {"name": "Multan", "lat": 30.1575, "lon": 71.5249, "elevation": 122.0, "country": "Pakistan"},
    {"name": "Lahore", "lat": 31.5204, "lon": 74.3587, "elevation": 217.0, "country": "Pakistan"},
    {
        "name": "Hyderabad_PK",
        "lat": 25.3960,
        "lon": 68.3578,
        "elevation": 13.0,
        "country": "Pakistan",
    },
    {"name": "Quetta", "lat": 30.1798, "lon": 66.9750, "elevation": 1680.0, "country": "Pakistan"},
    {"name": "Peshawar", "lat": 34.0151, "lon": 71.5249, "elevation": 359.0, "country": "Pakistan"},
    {"name": "Sukkur", "lat": 27.7052, "lon": 68.8574, "elevation": 67.0, "country": "Pakistan"},
    {"name": "Nawabshah", "lat": 26.2483, "lon": 68.4096, "elevation": 37.0, "country": "Pakistan"},
    {
        "name": "Bahawalpur",
        "lat": 29.3956,
        "lon": 71.6836,
        "elevation": 117.0,
        "country": "Pakistan",
    },
    {"name": "Sargodha", "lat": 32.0836, "lon": 72.6711, "elevation": 190.0, "country": "Pakistan"},
    {
        "name": "Gujranwala",
        "lat": 32.1877,
        "lon": 74.1945,
        "elevation": 226.0,
        "country": "Pakistan",
    },
    {"name": "Sialkot", "lat": 32.4945, "lon": 74.5229, "elevation": 256.0, "country": "Pakistan"},
    {
        "name": "Mirpur_Khas",
        "lat": 25.5269,
        "lon": 69.0111,
        "elevation": 15.0,
        "country": "Pakistan",
    },
    # South Asia (Indo-Gangetic & Deccan agricultural regions)
    {"name": "New_Delhi", "lat": 28.6139, "lon": 77.2090, "elevation": 216.0, "country": "India"},
    {"name": "Ludhiana", "lat": 30.9010, "lon": 75.8573, "elevation": 244.0, "country": "India"},
    {"name": "Roorkee", "lat": 29.8543, "lon": 77.8880, "elevation": 268.0, "country": "India"},
    {"name": "Karnal", "lat": 29.6857, "lon": 76.9905, "elevation": 250.0, "country": "India"},
    {"name": "Nagpur", "lat": 21.1458, "lon": 79.0882, "elevation": 310.0, "country": "India"},
    {"name": "Varanasi", "lat": 25.3176, "lon": 82.9739, "elevation": 81.0, "country": "India"},
    {
        "name": "Hyderabad_IN",
        "lat": 17.3850,
        "lon": 78.4867,
        "elevation": 542.0,
        "country": "India",
    },
    {"name": "Pune", "lat": 18.5204, "lon": 73.8567, "elevation": 560.0, "country": "India"},
    {"name": "Dhaka", "lat": 23.8103, "lon": 90.4125, "elevation": 4.0, "country": "Bangladesh"},
    {
        "name": "Rajshahi",
        "lat": 24.3636,
        "lon": 88.6241,
        "elevation": 18.0,
        "country": "Bangladesh",
    },
    # Southeast Asia (Rice & tropical agriculture)
    {"name": "Bangkok", "lat": 13.7563, "lon": 100.5018, "elevation": 2.0, "country": "Thailand"},
    {
        "name": "Chiang_Mai",
        "lat": 18.7883,
        "lon": 98.9853,
        "elevation": 310.0,
        "country": "Thailand",
    },
    {"name": "Can_Tho", "lat": 10.0452, "lon": 105.7469, "elevation": 3.0, "country": "Vietnam"},
    {
        "name": "Central_Luzon",
        "lat": 15.4828,
        "lon": 120.7120,
        "elevation": 25.0,
        "country": "Philippines",
    },
    # Middle East & Central Asia (Irrigated river basins)
    {
        "name": "Tashkent",
        "lat": 41.2995,
        "lon": 69.2401,
        "elevation": 450.0,
        "country": "Uzbekistan",
    },
    {"name": "Almaty", "lat": 43.2220, "lon": 76.8512, "elevation": 785.0, "country": "Kazakhstan"},
    {"name": "Nile_Delta", "lat": 30.7865, "lon": 31.0004, "elevation": 12.0, "country": "Egypt"},
    {"name": "Aswan", "lat": 24.0889, "lon": 32.8998, "elevation": 106.0, "country": "Egypt"},
    {"name": "Baghdad", "lat": 33.3152, "lon": 44.3661, "elevation": 34.0, "country": "Iraq"},
    # Mediterranean & Southern Europe
    {"name": "Seville", "lat": 37.3891, "lon": -5.9845, "elevation": 7.0, "country": "Spain"},
    {"name": "Bologna", "lat": 44.4949, "lon": 11.3426, "elevation": 54.0, "country": "Italy"},
    {"name": "Montpellier", "lat": 43.6108, "lon": 3.8767, "elevation": 27.0, "country": "France"},
    {"name": "Foggia", "lat": 41.4622, "lon": 15.5446, "elevation": 76.0, "country": "Italy"},
    {"name": "Alentejo", "lat": 38.5714, "lon": -7.9135, "elevation": 240.0, "country": "Portugal"},
    {"name": "Larissa", "lat": 39.6390, "lon": 22.4191, "elevation": 70.0, "country": "Greece"},
    # North & South America
    {"name": "Fresno_CA", "lat": 36.7468, "lon": -119.7726, "elevation": 90.0, "country": "USA"},
    {"name": "Salinas_CA", "lat": 36.6777, "lon": -121.6555, "elevation": 16.0, "country": "USA"},
    {"name": "Ames_IA", "lat": 42.0308, "lon": -93.6319, "elevation": 287.0, "country": "USA"},
    {"name": "Lubbock_TX", "lat": 33.5779, "lon": -101.8552, "elevation": 992.0, "country": "USA"},
    {
        "name": "Pergamino",
        "lat": -33.8931,
        "lon": -60.5736,
        "elevation": 65.0,
        "country": "Argentina",
    },
    {"name": "Petrolina", "lat": -9.3891, "lon": -40.5028, "elevation": 376.0, "country": "Brazil"},
    {"name": "Culiacan", "lat": 24.8091, "lon": -107.3940, "elevation": 55.0, "country": "Mexico"},
    # Africa & Oceania
    {"name": "Gezira", "lat": 14.4000, "lon": 33.5167, "elevation": 405.0, "country": "Sudan"},
    {"name": "Nakuru", "lat": -0.3031, "lon": 36.0800, "elevation": 1850.0, "country": "Kenya"},
    {"name": "Agadir", "lat": 30.4278, "lon": -9.5981, "elevation": 31.0, "country": "Morocco"},
    {
        "name": "Griffith",
        "lat": -34.2889,
        "lon": 146.0444,
        "elevation": 128.0,
        "country": "Australia",
    },
    {
        "name": "Shepparton",
        "lat": -36.3833,
        "lon": 145.4000,
        "elevation": 114.0,
        "country": "Australia",
    },
]


@dataclass
class QCReport:
    """Quality control summary report for fetched dataset."""

    records_total: int = 0
    records_valid: int = 0
    missing_imputed: int = 0
    outliers_clipped: int = 0
    locations_processed: int = 0
    flagged_reasons: Dict[str, int] = field(default_factory=dict)


class NasaPowerClient:
    """Client for downloading, caching, and preprocessing NASA POWER daily agroclimatology data."""

    def __init__(
        self,
        cache_dir: Optional[str | Path] = None,
        rate_limit_delay: float = 0.5,
        timeout: float = 15.0,
    ) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./data/cache/nasa_power")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout

    def fetch_station_daily(
        self,
        lat: float,
        lon: float,
        start_date: str = "20140101",
        end_date: str = "20231231",
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Fetch daily NASA POWER agroclimatology data for a point location.

        Args:
            lat: Latitude (-90 to 90).
            lon: Longitude (-180 to 180).
            start_date: Format YYYYMMDD.
            end_date: Format YYYYMMDD.
            use_cache: If True, reads from disk cache if present.
        """
        cache_file = self.cache_dir / f"power_{lat:.4f}_{lon:.4f}_{start_date}_{end_date}.json"

        if use_cache and cache_file.exists():
            import json

            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Corrupted cache file {cache_file}: {e}. Refetching.")

        params = {
            "parameters": "T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR",
            "community": "AG",
            "longitude": f"{lon:.4f}",
            "latitude": f"{lat:.4f}",
            "start": start_date,
            "end": end_date,
            "format": "JSON",
        }

        # Polite backoff retry
        max_retries = 3
        last_error = None
        for attempt in range(max_retries):
            try:
                time.sleep(self.rate_limit_delay)
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(NASA_POWER_BASE_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()

                    # Save to cache
                    import json

                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(data, f)
                    return data
            except Exception as e:
                last_error = e
                time.sleep(1.0 * (2**attempt))

        raise RuntimeError(
            f"Failed to fetch NASA POWER data for ({lat}, {lon}) after {max_retries} attempts: {last_error}"
        )

    def process_station_dataframe(
        self,
        raw_json: Dict[str, Any],
        station_meta: Dict[str, Any],
        qc_report: Optional[QCReport] = None,
    ) -> pd.DataFrame:
        """Parse raw JSON response into a clean pandas DataFrame with FAO-56 ET0 and QC."""
        props = raw_json.get("properties", {}).get("parameter", {})
        if not props:
            return pd.DataFrame()

        t2m = props.get("T2M", {})
        t2m_max = props.get("T2M_MAX", {})
        t2m_min = props.get("T2M_MIN", {})
        rh2m = props.get("RH2M", {})
        ws2m = props.get("WS2M", {})
        sw = props.get("ALLSKY_SFC_SW_DWN", {})
        precip = props.get("PRECTOTCORR", {})

        dates = sorted(t2m.keys())
        rows = []

        lat = station_meta["lat"]
        elevation = station_meta.get("elevation", 100.0)
        station_name = station_meta.get("name", "Unknown")
        country = station_meta.get("country", "")

        for d_str in dates:
            if qc_report:
                qc_report.records_total += 1

            # Raw values (-999 represents fill/missing in NASA POWER)
            v_t = t2m.get(d_str, -999.0)
            v_tmax = t2m_max.get(d_str, -999.0)
            v_tmin = t2m_min.get(d_str, -999.0)
            v_rh = rh2m.get(d_str, -999.0)
            v_ws = ws2m.get(d_str, -999.0)
            v_sw = sw.get(d_str, -999.0)
            v_pr = precip.get(d_str, 0.0)

            # Filter fill values
            vals = [v_t, v_tmax, v_tmin, v_rh, v_ws, v_sw]
            if any(val is None or val <= -900.0 for val in vals):
                if qc_report:
                    qc_report.outliers_clipped += 1
                    qc_report.flagged_reasons["missing_fill_value"] = (
                        qc_report.flagged_reasons.get("missing_fill_value", 0) + 1
                    )
                continue

            # Physical range QC filters:
            # - temperature: -10 to 50 °C
            # - humidity: 0 to 100 %
            # - wind: 0 to 30 m/s
            # - solar radiation: 0 to 35 MJ/m²/day
            if not (-10.0 <= v_t <= 50.0):
                continue
            if not (0.0 <= v_rh <= 100.0):
                continue
            if not (0.0 <= v_ws <= 30.0):
                continue
            if not (0.0 <= v_sw <= 35.0):
                continue

            # Parse date and DOY
            try:
                parsed_date = pd.to_datetime(d_str, format="%Y%m%d")
                doy = parsed_date.timetuple().tm_yday
            except Exception:
                doy = 150

            # Compute FAO-56 Penman-Monteith target
            pm_res = fao56_penman_monteith_full(
                tmin=v_tmin,
                tmax=v_tmax,
                humidity=v_rh,
                wind_speed=v_ws,
                solar_radiation=v_sw,
                latitude=lat,
                elevation=elevation,
                doy=doy,
            )

            rows.append(
                {
                    "date": d_str,
                    "location_name": station_name,
                    "country": country,
                    "latitude": lat,
                    "longitude": station_meta.get("lon", 0.0),
                    "elevation": elevation,
                    "doy": doy,
                    "temperature": round(v_t, 2),
                    "tmin": round(v_tmin, 2),
                    "tmax": round(v_tmax, 2),
                    "humidity": round(v_rh, 2),
                    "wind_speed": round(v_ws, 2),
                    "solar_radiation": round(v_sw, 2),
                    "precipitation": round(max(0.0, v_pr), 2),
                    "et": pm_res.et0,
                    "vpd": pm_res.vpd,
                    "net_radiation": pm_res.rn,
                    "provenance": "nasa_power",
                    "is_synthetic": False,
                }
            )

            if qc_report:
                qc_report.records_valid += 1

        df = pd.DataFrame(rows)
        return df

    def fetch_multi_station_dataset(
        self,
        stations: Optional[List[Dict[str, Any]]] = None,
        start_date: str = "20200101",
        end_date: str = "20231231",
        max_stations: Optional[int] = None,
    ) -> Tuple[pd.DataFrame, QCReport]:
        """Fetch and assemble unified multi-location agroclimatology dataset."""
        station_list = stations or GLOBAL_STATIONS
        if max_stations:
            station_list = station_list[:max_stations]

        report = QCReport()
        dfs = []

        for st in station_list:
            try:
                raw = self.fetch_station_daily(
                    lat=st["lat"],
                    lon=st["lon"],
                    start_date=start_date,
                    end_date=end_date,
                )
                df = self.process_station_dataframe(raw, st, qc_report=report)
                if not df.empty:
                    dfs.append(df)
                    report.locations_processed += 1
            except Exception as e:
                logger.warning(f"Could not fetch {st.get('name')}: {e}")

        if not dfs:
            return pd.DataFrame(), report

        combined = pd.concat(dfs, ignore_index=True)
        return combined, report
