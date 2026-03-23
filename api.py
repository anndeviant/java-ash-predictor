from __future__ import annotations

import math
import json
from urllib.parse import urlencode
from urllib.request import urlopen
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "outputs" / "best_multioutput_model.pkl"
DATA_PATH = BASE_DIR / "java-ash-hysplit.csv"
EXPECTED_MODEL_NAME = "xgboost"
EARTH_RADIUS_KM = 6371.0

DEFAULT_IMPACT_STATS = {
    "radius_min": 2.0,
    "radius_max": 120.0,
    "area_min": 50.0,
    "area_max": 8000.0,
}

SECTOR_SPREAD_DEG = 35.0
SECTOR_STEPS = 32

LEVEL_SPECS = [
    (1, "Sangat Rendah", 1.00, [46, 139, 87, 90]),
    (2, "Rendah", 0.85, [154, 205, 50, 95]),
    (3, "Sedang", 0.65, [255, 215, 0, 105]),
    (4, "Tinggi", 0.45, [255, 140, 0, 120]),
    (5, "Sangat Tinggi", 0.25, [178, 34, 34, 130]),
]

DEFAULT_VOLCANO_MAPPING = {
    "Bromo": (-7.941944, 112.950000, 2329.0),
    "Merapi": (-7.541940, 110.441940, 2968.0),
    "Raung": (-8.125000, 114.041944, 3332.0),
    "Semeru": (-8.108050, 112.920000, 3676.0),
    "Slamet": (-7.241944, 109.208056, 3432.0),
}
DEFAULT_ALERT_LEVELS = ["Normal", "Waspada", "Siaga", "Awas"]


class PredictionRequest(BaseModel):
    volcano_name: str = Field(min_length=1)
    tinggi_letusan_m: float = Field(ge=0)
    amplitudo: float = Field(ge=0)
    duration: float = Field(ge=0)
    alert_level: str = Field(min_length=1)
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    day: int = Field(ge=1, le=31)
    hour: int = Field(ge=0, le=23)
    timezone_name: Optional[str] = Field(default=None, min_length=1)
    timezone_offset_minutes: Optional[int] = Field(default=None, ge=-840, le=840)


def load_volcano_mapping(data_path: Path) -> Dict[str, Tuple[float, float, float]]:
    if not data_path.exists():
        return DEFAULT_VOLCANO_MAPPING.copy()

    raw_df = pd.read_csv(data_path)
    mapping_df = (
        raw_df[["volcano_filter", "latitude", "longitude", "elevation"]]
        .dropna()
        .drop_duplicates()
        .sort_values("volcano_filter")
    )

    mapping: Dict[str, Tuple[float, float, float]] = {}
    for _, row in mapping_df.iterrows():
        mapping[str(row["volcano_filter"])] = (
            float(row["latitude"]),
            float(row["longitude"]),
            float(row["elevation"]),
        )

    return mapping


def load_impact_reference_stats(data_path: Path) -> Dict[str, float]:
    if not data_path.exists():
        return default_impact_stats()

    try:
        df = pd.read_csv(data_path, usecols=["radius_km", "luas_km2"])
        radius = pd.to_numeric(df["radius_km"], errors="coerce").dropna()
        area = pd.to_numeric(df["luas_km2"], errors="coerce").dropna()

        if radius.empty or area.empty:
            return default_impact_stats()

        return {
            "radius_min": float(radius.quantile(0.05)),
            "radius_max": float(radius.quantile(0.95)),
            "area_min": float(area.quantile(0.05)),
            "area_max": float(area.quantile(0.95)),
        }
    except Exception:
        return default_impact_stats()


def load_alert_level_options(data_path: Path) -> List[str]:
    if not data_path.exists():
        return default_alert_levels()

    try:
        df = pd.read_csv(data_path, usecols=["alert_level"])
        options = sorted(
            {
                str(v)
                for v in df["alert_level"].dropna().astype(str).tolist()
                if str(v).strip()
            }
        )
        return options if options else default_alert_levels()
    except Exception:
        return default_alert_levels()


def load_feature_defaults(
    data_path: Path, expected_input_columns: List[str]
) -> Dict[str, object]:
    defaults: Dict[str, object] = {}

    if not data_path.exists():
        return defaults

    try:
        usecols = [
            col
            for col in expected_input_columns
            if col in pd.read_csv(data_path, nrows=0).columns
        ]
        if not usecols:
            return defaults

        df = pd.read_csv(data_path, usecols=usecols)
        for col in usecols:
            series = df[col].dropna()
            if series.empty:
                continue

            if pd.api.types.is_numeric_dtype(series):
                defaults[col] = float(pd.to_numeric(series, errors="coerce").median())
            else:
                defaults[col] = str(series.astype(str).mode().iloc[0])
    except Exception:
        return {}

    return defaults


def destination_point(
    lat: float, lon: float, distance_km: float, bearing_deg: float
) -> Tuple[float, float]:
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    bearing = math.radians(bearing_deg % 360)
    angular_distance = distance_km / EARTH_RADIUS_KM

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )

    return math.degrees(lat2), math.degrees(lon2)


def build_sector_polygon(
    origin_lat: float,
    origin_lon: float,
    radius_km: float,
    center_bearing_deg: float,
    spread_deg: float = SECTOR_SPREAD_DEG,
    steps: int = SECTOR_STEPS,
) -> List[List[float]]:
    start_bearing = center_bearing_deg - (spread_deg / 2)
    end_bearing = center_bearing_deg + (spread_deg / 2)

    points = [[origin_lon, origin_lat]]
    for i in range(steps + 1):
        t = i / steps
        bearing = start_bearing + t * (end_bearing - start_bearing)
        lat_pt, lon_pt = destination_point(origin_lat, origin_lon, radius_km, bearing)
        points.append([lon_pt, lat_pt])

    points.append([origin_lon, origin_lat])
    return points


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def build_impact_visual_data(
    origin_lat: float,
    origin_lon: float,
    center_bearing_deg: float,
    radius_km: float,
    area_km2: float,
    stats: Dict[str, float],
) -> Tuple[List[dict], List[dict], List[dict], List[dict], Dict[str, float]]:
    radius_span = max(1e-6, stats["radius_max"] - stats["radius_min"])
    area_span = max(1e-6, stats["area_max"] - stats["area_min"])
    radius_norm = clamp01((radius_km - stats["radius_min"]) / radius_span)
    area_norm = clamp01((area_km2 - stats["area_min"]) / area_span)

    spread_deg = SECTOR_SPREAD_DEG
    directional_weight = clamp01(45.0 / spread_deg)
    base_severity = clamp01((0.6 * radius_norm) + (0.4 * area_norm))

    polygons: List[dict] = []
    summary_rows: List[dict] = []
    max_distance = 0.0

    for level, label, radius_factor, color in LEVEL_SPECS:
        zone_radius = max(1.0, radius_km * radius_factor)
        max_distance = max(max_distance, zone_radius)

        proximity_weight = clamp01(1.15 - radius_factor)
        level_score = clamp01(
            base_severity * (0.75 + 0.5 * proximity_weight) * directional_weight
        )

        polygons.append(
            {
                "level": level,
                "label": label,
                "radius_km": round(zone_radius, 2),
                "impact_score": round(level_score, 3),
                "coordinates": build_sector_polygon(
                    origin_lat=origin_lat,
                    origin_lon=origin_lon,
                    radius_km=zone_radius,
                    center_bearing_deg=center_bearing_deg,
                    spread_deg=spread_deg,
                ),
                "fill_color": color,
            }
        )

        center_lat, center_lon = destination_point(
            origin_lat,
            origin_lon,
            max(0.5, zone_radius * 0.7),
            center_bearing_deg,
        )
        summary_rows.append(
            {
                "level": level,
                "kategori": label,
                "radius_km": round(zone_radius, 2),
                "estimasi_luas_km2": round(area_km2 * (radius_factor**2), 2),
                "impact_score": round(level_score, 3),
                "pusat_lat": round(center_lat, 6),
                "pusat_lon": round(center_lon, 6),
            }
        )

    centerline_lat, centerline_lon = destination_point(
        origin_lat, origin_lon, radius_km, center_bearing_deg
    )
    centerline = [
        {
            "path": [[origin_lon, origin_lat], [centerline_lon, centerline_lat]],
            "name": "Arah utama sebaran abu",
        }
    ]

    points = [
        {
            "name": "Pusat erupsi",
            "lat": origin_lat,
            "lon": origin_lon,
            "color": [20, 20, 20, 255],
            "radius": 550,
        },
        {
            "name": "Arah dominan abu",
            "lat": centerline_lat,
            "lon": centerline_lon,
            "color": [178, 34, 34, 240],
            "radius": 420,
        },
    ]

    metadata = {
        "spread_deg": spread_deg,
        "directional_weight": directional_weight,
        "max_distance": max_distance,
        "base_severity": base_severity,
    }

    summary = sorted(summary_rows, key=lambda row: row["level"], reverse=True)
    return polygons, summary, points, centerline, metadata


def infer_expected_input_columns(
    model, artifact_feature_columns: List[str]
) -> List[str]:
    if hasattr(model, "named_steps") and "preprocessor" in model.named_steps:
        preprocessor = model.named_steps["preprocessor"]
        if hasattr(preprocessor, "feature_names_in_"):
            return [str(col) for col in preprocessor.feature_names_in_.tolist()]

    return artifact_feature_columns


def build_input_row(
    expected_input_columns: List[str],
    feature_defaults: Dict[str, object],
    volcano_coords: Tuple[float, float, float],
    request: PredictionRequest,
    wind_speed_km_h: float,
    wind_direction_deg: float,
) -> Tuple[pd.DataFrame, List[str]]:
    latitude, longitude, elevation = volcano_coords

    event_dt = datetime(request.year, request.month, request.day, request.hour, 0, 0)
    day_of_week = event_dt.weekday()

    hour_angle = 2 * math.pi * (float(request.hour) / 24.0)

    row = {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "elevation": float(elevation),
        "volcano_filter": request.volcano_name,
        "alert_level": request.alert_level,
        "tinggi_letusan_m": float(request.tinggi_letusan_m),
        "kec_angin_km_jam": float(wind_speed_km_h),
        "arah_angin_deg": float(wind_direction_deg),
        "amplitudo": float(request.amplitudo),
        "duration": float(request.duration),
        "year": int(request.year),
        "month": int(request.month),
        "day": int(request.day),
        "hour": int(request.hour),
        "day_of_week": int(day_of_week),
        "hour_sin": math.sin(hour_angle),
        "hour_cos": math.cos(hour_angle),
    }

    warnings: List[str] = []
    for col in expected_input_columns:
        if col not in row:
            row[col] = feature_defaults.get(col, 0)
            warnings.append(col)

    return pd.DataFrame([row], columns=list(row.keys())), warnings


@lru_cache(maxsize=1)
def load_runtime_bundle() -> dict:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model tidak ditemukan di: {MODEL_PATH}")

    artifact = joblib.load(MODEL_PATH)
    if not isinstance(artifact, dict):
        raise ValueError("Format artifact tidak valid.")

    model_name = str(artifact.get("model_name", "")).strip().lower()
    if model_name != EXPECTED_MODEL_NAME:
        raise ValueError("Artifact bukan model final xgboost.")

    model = artifact["model"]
    feature_columns = artifact["feature_columns"]
    target_columns = artifact["target_columns"]
    expected_input_columns = infer_expected_input_columns(model, feature_columns)

    return {
        "artifact": artifact,
        "model": model,
        "target_columns": target_columns,
        "expected_input_columns": expected_input_columns,
        "feature_defaults": load_feature_defaults(DATA_PATH, expected_input_columns),
        "volcano_mapping": load_volcano_mapping(DATA_PATH),
        "alert_levels": load_alert_level_options(DATA_PATH),
        "impact_stats": load_impact_reference_stats(DATA_PATH),
    }


app = FastAPI(title="Volcanic Ash Prediction API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://java-ash-predictor.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


def load_runtime_bundle_or_http_error() -> dict:
    try:
        return load_runtime_bundle()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def to_records(value: object) -> List[dict]:
    return value.to_dict(orient="records") if hasattr(value, "to_dict") else []


def default_impact_stats() -> Dict[str, float]:
    return DEFAULT_IMPACT_STATS.copy()


def default_alert_levels() -> List[str]:
    return DEFAULT_ALERT_LEVELS.copy()


def resolve_user_timezone(
    timezone_name: Optional[str], timezone_offset_minutes: Optional[int]
):
    if timezone_name:
        try:
            return ZoneInfo(str(timezone_name))
        except Exception:
            pass

    if timezone_offset_minutes is not None:
        return timezone(timedelta(minutes=int(timezone_offset_minutes)))

    return timezone.utc


def fetch_wind_from_open_meteo(
    latitude: float, longitude: float, event_dt: datetime
) -> Dict[str, float | str]:
    base_url = (
        "https://archive-api.open-meteo.com/v1/archive"
        if event_dt.date() < datetime.now(timezone.utc).date()
        else "https://api.open-meteo.com/v1/forecast"
    )

    day_text = event_dt.strftime("%Y-%m-%d")
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "wind_speed_10m,wind_direction_10m",
        "timezone": "UTC",
        "start_date": day_text,
        "end_date": day_text,
    }

    url = f"{base_url}?{urlencode(params)}"
    try:
        with urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Gagal mengambil data angin Open-Meteo: {exc}"
        ) from exc

    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    speeds = hourly.get("wind_speed_10m", [])
    directions = hourly.get("wind_direction_10m", [])

    if not times or not speeds or not directions:
        raise HTTPException(
            status_code=502, detail="Data angin Open-Meteo tidak lengkap."
        )

    target_time = event_dt.strftime("%Y-%m-%dT%H:00")
    if target_time in times:
        index = times.index(target_time)
    else:
        # Fallback ke jam terdekat dalam hari yang sama.
        target_hour = event_dt.hour
        index = min(
            range(len(times)),
            key=lambda i: abs(
                int(str(times[i]).split("T")[1].split(":")[0]) - target_hour
            ),
        )

    return {
        "wind_speed_km_h": float(speeds[index]),
        "wind_direction_deg": float(directions[index]),
        "observed_time": str(times[index]),
        "source": "open-meteo",
    }


@app.get("/meta")
def get_meta():
    runtime = load_runtime_bundle_or_http_error()

    artifact = runtime["artifact"]
    volcano_mapping = runtime["volcano_mapping"]
    alert_levels = runtime["alert_levels"]

    comparison = artifact.get("comparison")
    holdout_metrics = artifact.get("holdout_metrics")

    comparison_rows = to_records(comparison)
    holdout_rows = to_records(holdout_metrics)

    volcanoes = [
        {
            "name": name,
            "latitude": coords[0],
            "longitude": coords[1],
            "elevation": coords[2],
        }
        for name, coords in sorted(volcano_mapping.items(), key=lambda item: item[0])
    ]

    return {
        "model_name": artifact.get("model_name"),
        "target_columns": artifact.get("target_columns", []),
        "comparison": comparison_rows,
        "holdout_metrics": holdout_rows,
        "alert_levels": alert_levels,
        "volcanoes": volcanoes,
    }


@app.post("/predict")
def predict(payload: PredictionRequest):
    runtime = load_runtime_bundle_or_http_error()

    volcano_mapping = runtime["volcano_mapping"]
    expected_input_columns = runtime["expected_input_columns"]
    feature_defaults = runtime["feature_defaults"]
    model = runtime["model"]
    target_columns = runtime["target_columns"]
    impact_stats = runtime["impact_stats"]

    if payload.volcano_name not in volcano_mapping:
        raise HTTPException(status_code=400, detail="Volcano tidak dikenal.")

    latitude, longitude, _ = volcano_mapping[payload.volcano_name]
    user_tz = resolve_user_timezone(
        payload.timezone_name, payload.timezone_offset_minutes
    )
    local_event_dt = datetime(
        payload.year, payload.month, payload.day, payload.hour, 0, 0, tzinfo=user_tz
    )
    event_dt_utc = local_event_dt.astimezone(timezone.utc)

    wind_observation = fetch_wind_from_open_meteo(
        latitude=float(latitude),
        longitude=float(longitude),
        event_dt=event_dt_utc,
    )
    wind_observation.update(
        {
            "requested_time_local": local_event_dt.isoformat(),
            "requested_time_utc": event_dt_utc.isoformat(),
            "user_timezone": str(user_tz),
        }
    )

    try:
        input_row, autofilled = build_input_row(
            expected_input_columns=expected_input_columns,
            feature_defaults=feature_defaults,
            volcano_coords=volcano_mapping[payload.volcano_name],
            request=payload,
            wind_speed_km_h=float(wind_observation["wind_speed_km_h"]),
            wind_direction_deg=float(wind_observation["wind_direction_deg"]),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"Input tanggal/waktu tidak valid: {exc}"
        ) from exc

    input_row = input_row.reindex(columns=expected_input_columns, fill_value=0)

    try:
        prediction_values = model.predict(input_row)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Gagal menjalankan prediksi: {exc}"
        ) from exc

    result_df = pd.DataFrame(prediction_values, columns=target_columns)
    result = result_df.iloc[0]

    radius_km = float(result.get("radius_km", 0.0))
    area_km2 = float(result.get("luas_km2", 0.0))
    center_bearing_deg = float(
        result.get("sudut_deg", wind_observation["wind_direction_deg"])
    )

    polygons, summary, points, centerline, metadata = build_impact_visual_data(
        origin_lat=float(latitude),
        origin_lon=float(longitude),
        center_bearing_deg=center_bearing_deg,
        radius_km=max(1.0, radius_km),
        area_km2=max(1.0, area_km2),
        stats=impact_stats,
    )

    prediction = {
        key: float(result[key]) for key in target_columns if key in result.index
    }

    return {
        "prediction": prediction,
        "weather_observation": wind_observation,
        "autofilled_columns": sorted(autofilled),
        "impact": {
            "polygons": polygons,
            "summary": summary,
            "points": points,
            "centerline": centerline,
            "metadata": metadata,
        },
    }
