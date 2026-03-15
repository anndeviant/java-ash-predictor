from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import pandas as pd
import pydeck as pdk
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "best_multioutput_model.pkl"
DATA_PATH = BASE_DIR / "java-ash-hysplit.csv"
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
    (1, "Sangat Rendah", 1.00, "#2E8B57"),
    (2, "Rendah", 0.85, "#9ACD32"),
    (3, "Sedang", 0.65, "#FFD700"),
    (4, "Tinggi", 0.45, "#FF8C00"),
    (5, "Sangat Tinggi", 0.25, "#B22222"),
]

MAP_PROVIDER = "carto"
MAP_STYLE = "light"

DEFAULT_ALERT_LEVELS = ["Normal", "Waspada", "Siaga", "Awas"]


def load_volcano_mapping(data_path: Path) -> Dict[str, Tuple[float, float, float]]:
    if not data_path.exists():
        return {
            "Bromo": (-7.941944, 112.950000, 2329.0),
            "Merapi": (-7.541940, 110.441940, 2968.0),
            "Raung": (-8.125000, 114.041944, 3332.0),
            "Semeru": (-8.108050, 112.920000, 3676.0),
            "Slamet": (-7.241944, 109.208056, 3432.0),
        }

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
        return DEFAULT_IMPACT_STATS.copy()

    try:
        df = pd.read_csv(data_path, usecols=["radius_km", "luas_km2"])
        radius = pd.to_numeric(df["radius_km"], errors="coerce").dropna()
        area = pd.to_numeric(df["luas_km2"], errors="coerce").dropna()

        if radius.empty or area.empty:
            return DEFAULT_IMPACT_STATS.copy()

        return {
            "radius_min": float(radius.quantile(0.05)),
            "radius_max": float(radius.quantile(0.95)),
            "area_min": float(area.quantile(0.05)),
            "area_max": float(area.quantile(0.95)),
        }
    except Exception:
        return DEFAULT_IMPACT_STATS.copy()


def load_alert_level_options(data_path: Path) -> List[str]:
    if not data_path.exists():
        return DEFAULT_ALERT_LEVELS.copy()

    try:
        df = pd.read_csv(data_path, usecols=["alert_level"])
        options = sorted({str(v) for v in df["alert_level"].dropna().astype(str).tolist() if str(v).strip()})
        return options if options else DEFAULT_ALERT_LEVELS.copy()
    except Exception:
        return DEFAULT_ALERT_LEVELS.copy()


def load_feature_defaults(data_path: Path, expected_input_columns: List[str]) -> Dict[str, object]:
    defaults: Dict[str, object] = {}

    if not data_path.exists():
        return defaults

    try:
        usecols = [col for col in expected_input_columns if col in pd.read_csv(data_path, nrows=0).columns]
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


def destination_point(lat: float, lon: float, distance_km: float, bearing_deg: float) -> Tuple[float, float]:
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


def hex_to_rgba(hex_color: str, alpha: int) -> List[int]:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return [r, g, b, alpha]


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def resolve_map_config() -> Dict[str, str]:
    return {"map_provider": MAP_PROVIDER, "map_style": MAP_STYLE}


def build_map_layers(
    polygons_df: pd.DataFrame,
    centerline_df: pd.DataFrame,
    points_df: pd.DataFrame,
) -> List[pdk.Layer]:
    return [
        pdk.Layer(
            "PolygonLayer",
            data=polygons_df,
            get_polygon="coordinates",
            get_fill_color="fill_color",
            get_line_color=[60, 60, 60, 140],
            line_width_min_pixels=1,
            pickable=True,
        ),
        pdk.Layer(
            "PathLayer",
            data=centerline_df,
            get_path="path",
            get_color=[180, 30, 30, 220],
            width_scale=1,
            width_min_pixels=2,
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=points_df,
            get_position="[lon, lat]",
            get_fill_color="color",
            get_radius="radius",
            pickable=True,
        ),
    ]


def build_impact_visual_data(
    origin_lat: float,
    origin_lon: float,
    center_bearing_deg: float,
    radius_km: float,
    area_km2: float,
    stats: Dict[str, float],
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    radius_span = max(1e-6, stats["radius_max"] - stats["radius_min"])
    area_span = max(1e-6, stats["area_max"] - stats["area_min"])
    radius_norm = clamp01((radius_km - stats["radius_min"]) / radius_span)
    area_norm = clamp01((area_km2 - stats["area_min"]) / area_span)

    spread_deg = SECTOR_SPREAD_DEG
    directional_weight = clamp01(45.0 / spread_deg)
    base_severity = clamp01((0.6 * radius_norm) + (0.4 * area_norm))

    polygons = []
    summary_rows = []
    max_distance = 0.0

    for level, label, radius_factor, color_hex in LEVEL_SPECS:
        zone_radius = max(1.0, radius_km * radius_factor)
        max_distance = max(max_distance, zone_radius)

        proximity_weight = clamp01(1.15 - radius_factor)
        level_score = clamp01(base_severity * (0.75 + 0.5 * proximity_weight) * directional_weight)

        polygon_coords = build_sector_polygon(
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            radius_km=zone_radius,
            center_bearing_deg=center_bearing_deg,
            spread_deg=spread_deg,
        )
        polygons.append(
            {
                "level": level,
                "label": label,
                "radius_km": round(zone_radius, 2),
                "impact_score": round(level_score, 3),
                "coordinates": polygon_coords,
                "fill_color": hex_to_rgba(color_hex, 90),
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

    centerline_lat, centerline_lon = destination_point(origin_lat, origin_lon, radius_km, center_bearing_deg)
    centerline_df = pd.DataFrame(
        [
            {
                "path": [[origin_lon, origin_lat], [centerline_lon, centerline_lat]],
                "name": "Arah utama sebaran abu",
            }
        ]
    )

    points_df = pd.DataFrame(
        [
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
    )

    metadata = {
        "spread_deg": spread_deg,
        "directional_weight": directional_weight,
        "max_distance": max_distance,
        "base_severity": base_severity,
    }

    polygons_df = pd.DataFrame(polygons).sort_values("level")
    summary_df = pd.DataFrame(summary_rows).sort_values("level", ascending=False)
    return polygons_df, summary_df, points_df, centerline_df, metadata


@st.cache_resource
def load_artifact(model_path: Path):
    if not model_path.exists():
        raise FileNotFoundError(f"Model tidak ditemukan di: {model_path}")
    return joblib.load(model_path)


def build_input_row(
    expected_input_columns,
    feature_defaults: Dict[str, object],
    volcano_coords: Tuple[float, float, float],
    volcano_name: str,
    form_values: dict,
) -> Tuple[pd.DataFrame, List[str]]:
    latitude, longitude, elevation = volcano_coords

    event_dt = datetime(
        int(form_values["year"]),
        int(form_values["month"]),
        int(form_values["day"]),
        int(form_values["hour"]),
        0,
        0,
    )
    day_of_week = event_dt.weekday()

    hour_float = float(form_values["hour"])
    hour_angle = 2 * math.pi * (hour_float / 24.0)

    row = {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "elevation": float(elevation),
        "volcano_filter": str(volcano_name),
        "alert_level": str(form_values["alert_level"]),
        "tinggi_letusan_m": float(form_values["tinggi_letusan_m"]),
        "kec_angin_km_jam": float(form_values["kec_angin_km_jam"]),
        "arah_angin_deg": float(form_values["arah_angin_deg"]),
        "amplitudo": float(form_values["amplitudo"]),
        "duration": float(form_values["duration"]),
        "year": int(form_values["year"]),
        "month": int(form_values["month"]),
        "day": int(form_values["day"]),
        "hour": int(form_values["hour"]),
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


def infer_expected_input_columns(model, artifact_feature_columns: List[str]) -> List[str]:
    if hasattr(model, "named_steps") and "preprocessor" in model.named_steps:
        preprocessor = model.named_steps["preprocessor"]
        if hasattr(preprocessor, "feature_names_in_"):
            return [str(col) for col in preprocessor.feature_names_in_.tolist()]

    # Fallback for artifacts that store original features directly.
    return artifact_feature_columns


def main() -> None:
    st.set_page_config(page_title="Multi-Output Volcano Predictor", layout="wide")
    st.title("Prediksi Multi-Output Abu Vulkanik")
    st.caption("Model: best_multioutput_model.pkl")

    try:
        artifact = load_artifact(MODEL_PATH)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    model = artifact["model"]
    feature_columns = artifact["feature_columns"]
    target_columns = artifact["target_columns"]
    expected_input_columns = infer_expected_input_columns(model, feature_columns)
    feature_defaults = load_feature_defaults(DATA_PATH, expected_input_columns)

    volcano_mapping = load_volcano_mapping(DATA_PATH)
    alert_level_options = load_alert_level_options(DATA_PATH)
    impact_stats = load_impact_reference_stats(DATA_PATH)
    if not volcano_mapping:
        st.error("Mapping gunung tidak tersedia.")
        st.stop()

    st.subheader("Fitur Model")
    st.caption(
        f"Input yang diharapkan model: {len(expected_input_columns)} kolom | "
        f"Fitur internal hasil transformasi: {len(feature_columns)} kolom"
    )
    st.write(expected_input_columns[:12])

    left, right = st.columns([1.2, 1])

    with left:
        st.subheader("Input Prediksi (Manual)")
        with st.form("prediction_form"):
            volcano_name = st.selectbox("Pilih Gunung", options=list(volcano_mapping.keys()))
            latitude, longitude, elevation = volcano_mapping[volcano_name]

            st.number_input("Latitude (otomatis)", value=latitude, disabled=True, format="%.6f")
            st.number_input("Longitude (otomatis)", value=longitude, disabled=True, format="%.6f")
            st.number_input("Elevation (otomatis)", value=elevation, disabled=True, format="%.2f")

            tinggi_letusan_m = st.number_input("tinggi_letusan_m", min_value=0.0, value=1000.0, step=10.0)
            kec_angin_km_jam = st.number_input("kec_angin_km_jam", min_value=0.0, value=5.0, step=0.1)
            arah_angin_deg = st.number_input("arah_angin_deg", min_value=0.0, max_value=360.0, value=90.0, step=1.0)
            amplitudo = st.number_input("amplitudo", min_value=0.0, value=30.0, step=0.1)
            duration = st.number_input("duration", min_value=0.0, value=300.0, step=1.0)
            alert_level = st.selectbox("alert_level", options=alert_level_options)

            year = st.number_input("year", min_value=2000, max_value=2100, value=2024, step=1)
            month = st.number_input("month", min_value=1, max_value=12, value=1, step=1)
            day = st.number_input("day", min_value=1, max_value=31, value=1, step=1)
            hour = st.number_input("hour", min_value=0, max_value=23, value=0, step=1)

            submitted = st.form_submit_button("Prediksi")

        if submitted:
            try:
                values = {
                    "tinggi_letusan_m": tinggi_letusan_m,
                    "kec_angin_km_jam": kec_angin_km_jam,
                    "arah_angin_deg": arah_angin_deg,
                    "amplitudo": amplitudo,
                    "duration": duration,
                    "alert_level": alert_level,
                    "year": year,
                    "month": month,
                    "day": day,
                    "hour": hour,
                }

                input_row, autofilled_columns = build_input_row(
                    expected_input_columns=expected_input_columns,
                    feature_defaults=feature_defaults,
                    volcano_coords=(latitude, longitude, elevation),
                    volcano_name=volcano_name,
                    form_values=values,
                )
                input_row = input_row.reindex(columns=expected_input_columns, fill_value=0)

                if autofilled_columns:
                    st.warning(
                        "Beberapa fitur tidak tersedia di form dan diisi default data historis (median/mode): "
                        + ", ".join(sorted(autofilled_columns))
                    )

                predictions = model.predict(input_row)

                result_df = pd.DataFrame(predictions, columns=target_columns)
                st.success("Prediksi berhasil dibuat.")
                st.dataframe(result_df, use_container_width=True)

                result = result_df.iloc[0]
                radius_km = float(result.get("radius_km", 0.0))
                area_km2 = float(result.get("luas_km2", 0.0))
                center_bearing_deg = float(result.get("sudut_deg", arah_angin_deg))

                polygons_df, summary_impact, points_df, centerline_df, metadata = build_impact_visual_data(
                    origin_lat=float(latitude),
                    origin_lon=float(longitude),
                    center_bearing_deg=center_bearing_deg,
                    radius_km=max(1.0, radius_km),
                    area_km2=max(1.0, area_km2),
                    stats=impact_stats,
                )

                st.subheader("Visualisasi Sebaran Abu (Simulasi Dampak)")
                st.caption(
                    "Visual ini meniru pola HYSPLIT secara konseptual dengan sector arah angin, "
                    "bukan output HYSPLIT numerik penuh."
                )

                max_distance = max(metadata["max_distance"], 1.0)
                zoom = max(6.5, 10.7 - (math.log10(max_distance + 1.0) * 1.7))

                layers = build_map_layers(
                    polygons_df=polygons_df,
                    centerline_df=centerline_df,
                    points_df=points_df,
                )

                tooltip = {
                    "html": "<b>Level:</b> {level} - {label}<br/><b>Radius:</b> {radius_km} km<br/><b>Skor:</b> {impact_score}",
                    "style": {"backgroundColor": "#111111", "color": "#ffffff"},
                }

                map_config = resolve_map_config()

                deck = pdk.Deck(
                    map_provider=map_config["map_provider"],
                    map_style=map_config["map_style"],
                    initial_view_state=pdk.ViewState(
                        latitude=float(latitude),
                        longitude=float(longitude),
                        zoom=zoom,
                        pitch=35,
                    ),
                    layers=layers,
                    tooltip=tooltip,
                )
                st.pydeck_chart(deck, use_container_width=True)

                st.markdown("Ringkasan titik/wilayah terdampak")
                st.dataframe(summary_impact, use_container_width=True)

                st.info(
                    "Skor dasar dampak dihitung dari kombinasi radius dan luas prediksi, "
                    "kemudian dibobotkan oleh konsentrasi arah sebaran."
                )
            except Exception as exc:
                st.error(f"Gagal melakukan prediksi: {exc}")

    with right:
        st.subheader("Ringkasan Metrik Model")
        holdout_metrics = artifact.get("holdout_metrics")
        comparison = artifact.get("comparison")

        if comparison is not None:
            st.markdown("Perbandingan model")
            st.dataframe(comparison, use_container_width=True)

        if holdout_metrics is not None:
            st.markdown("Metrik holdout per target")
            st.dataframe(holdout_metrics, use_container_width=True)


if __name__ == "__main__":
    main()
