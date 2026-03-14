from pathlib import Path
import json
import pickle

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = BASE_DIR / "artifacts_multi_regressor"
MODEL_PATH = ARTIFACT_DIR / "model" / "multi_output_xgboost.pkl"
X_SCALER_PATH = ARTIFACT_DIR / "scalers" / "x_scaler.pkl"
Y_SCALER_PATH = ARTIFACT_DIR / "scalers" / "y_scaler.pkl"
X_META_PATH = ARTIFACT_DIR / "scalers" / "x_scaler_metadata.json"
Y_META_PATH = ARTIFACT_DIR / "scalers" / "y_scaler_metadata.json"
DATA_PATH = BASE_DIR / "java-ash-hysplit-encoded.csv"


@st.cache_resource
def load_artifacts():
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    with open(X_SCALER_PATH, "rb") as f:
        x_scaler = pickle.load(f)

    with open(Y_SCALER_PATH, "rb") as f:
        y_scaler = pickle.load(f)

    with open(X_META_PATH, "r", encoding="utf-8") as f:
        x_meta = json.load(f)

    with open(Y_META_PATH, "r", encoding="utf-8") as f:
        y_meta = json.load(f)

    return model, x_scaler, y_scaler, x_meta, y_meta


@st.cache_data
def load_reference_data():
    if DATA_PATH.exists():
        return pd.read_csv(DATA_PATH)
    return pd.DataFrame()


def get_default_feature_names(x_meta, df, target_names):
    feature_names = x_meta.get("feature_names", [])
    if feature_names:
        return feature_names

    if not df.empty:
        return [c for c in df.columns if c not in target_names]

    return []


def safe_median(df, col, default=0.0):
    if df.empty or col not in df.columns:
        return float(default)
    series = pd.to_numeric(df[col], errors="coerce").dropna()
    if series.empty:
        return float(default)
    return float(series.median())


def main():
    st.set_page_config(page_title="Simulasi XGBoost Multi-Regressor", layout="wide")
    st.title("Simulasi Prediksi Abu Vulkanik - XGBoost")

    missing = [
        p
        for p in [MODEL_PATH, X_SCALER_PATH, Y_SCALER_PATH, X_META_PATH, Y_META_PATH]
        if not p.exists()
    ]
    if missing:
        st.error(
            "Artefak model belum lengkap. Jalankan notebook training terlebih dulu."
        )
        st.write("File yang belum ada:")
        for p in missing:
            st.write(f"- {p}")
        st.stop()

    model, x_scaler, y_scaler, x_meta, y_meta = load_artifacts()
    ref_df = load_reference_data()

    target_names = y_meta.get(
        "target_names", ["target_1", "target_2", "target_3", "target_4"]
    )
    feature_names = get_default_feature_names(x_meta, ref_df, target_names)

    if not feature_names:
        st.error("Feature names tidak ditemukan dari metadata atau dataset referensi.")
        st.stop()

    one_hot_cols = [c for c in feature_names if c.startswith("volcano_filter_")]
    manual_input_cols = [
        "timestamp",
        "kec_angin_km_jam",
        "amplitudo",
        "duration",
        "alert_level",
        "tinggi_letusan_m",
        "arah_angin_deg",
    ]
    auto_geo_cols = ["latitude", "longitude", "elevation"]

    input_values = {}

    st.subheader("Input Fitur")

    selected_volcano = None
    volcano_ref_df = ref_df
    if one_hot_cols:
        volcano_options = [c.replace("volcano_filter_", "") for c in one_hot_cols]
        selected_volcano = st.selectbox(
            "Volcano Filter", options=volcano_options, index=0
        )
        volcano_col = f"volcano_filter_{selected_volcano}"

        if not ref_df.empty and volcano_col in ref_df.columns:
            filtered = ref_df[ref_df[volcano_col] == 1]
            if not filtered.empty:
                volcano_ref_df = filtered

        for col in one_hot_cols:
            input_values[col] = (
                1.0 if col == f"volcano_filter_{selected_volcano}" else 0.0
            )

    with st.expander("Input numerik manual", expanded=True):
        left, right = st.columns(2)
        available_manual_cols = [c for c in manual_input_cols if c in feature_names]
        for i, col in enumerate(available_manual_cols):
            default_val = safe_median(
                volcano_ref_df, col, default=safe_median(ref_df, col, default=0.0)
            )

            container = left if i % 2 == 0 else right
            input_values[col] = container.number_input(
                label=col,
                value=float(default_val),
                step=0.1,
                format="%.6f",
            )

    st.subheader("Fitur Otomatis Dari Gunung")
    geo_cols = st.columns(3)
    for i, col in enumerate(auto_geo_cols):
        if col in feature_names:
            auto_val = safe_median(
                volcano_ref_df, col, default=safe_median(ref_df, col, default=0.0)
            )
            input_values[col] = auto_val
            geo_cols[i].number_input(
                label=f"{col} (otomatis)",
                value=float(auto_val),
                step=0.1,
                format="%.6f",
                disabled=True,
            )

    fallback_cols = [
        c
        for c in feature_names
        if c not in one_hot_cols + manual_input_cols + auto_geo_cols
    ]
    if fallback_cols:
        st.info(
            "Beberapa fitur tambahan model tidak ditampilkan di form dan diisi otomatis dari median data referensi: "
            + ", ".join(fallback_cols)
        )
        for col in fallback_cols:
            input_values[col] = safe_median(
                volcano_ref_df, col, default=safe_median(ref_df, col, default=0.0)
            )

    st.caption(
        "Input manual dibatasi sesuai kebutuhan. Latitude, longitude, dan elevation mengikuti gunung yang dipilih."
    )

    if st.button("Prediksi", type="primary"):
        input_df = pd.DataFrame(
            [[input_values.get(col, 0.0) for col in feature_names]],
            columns=feature_names,
        )

        x_scaled = x_scaler.transform(input_df)
        y_pred_scaled = model.predict(x_scaled)
        y_pred = y_scaler.inverse_transform(y_pred_scaled)

        pred_df = pd.DataFrame(y_pred, columns=target_names)

        st.subheader("Hasil Prediksi")
        metric_cols = st.columns(len(target_names))
        for i, target in enumerate(target_names):
            metric_cols[i].metric(target, f"{pred_df.loc[0, target]:.6f}")

        st.subheader("Detail Input")
        st.dataframe(input_df)

        if not volcano_ref_df.empty and all(
            t in volcano_ref_df.columns for t in target_names
        ):
            actual_df = (
                volcano_ref_df[[*target_names]]
                .median(numeric_only=True)
                .to_frame()
                .T.reset_index(drop=True)
            )
            compare_df = pd.concat(
                [
                    pred_df.T.rename(columns={0: "prediksi"}),
                    actual_df.T.rename(columns={0: "median_referensi"}),
                ],
                axis=1,
            )
            st.subheader("Perbandingan Dengan Median Referensi Gunung")
            st.dataframe(compare_df)


if __name__ == "__main__":
    main()
