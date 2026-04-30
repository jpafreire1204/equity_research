"""Cached data loaders for the Streamlit app."""
import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


@st.cache_data(ttl=3600)
def load_kpis_wide() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "kpis_wide.parquet")


@st.cache_data(ttl=3600)
def load_ultimate_scores() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "ultimate_scores_2024.parquet")


@st.cache_data(ttl=3600)
def load_scenarios() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "scenarios_2024.parquet")


@st.cache_data(ttl=3600)
def load_feature_matrix() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "feature_matrix.parquet")


@st.cache_data(ttl=3600)
def load_feature_importance() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / "feature_importance.parquet")


@st.cache_data(ttl=3600)
def get_data_freshness() -> str:
    """Return mtime of ultimate_scores_2024.parquet as a friendly string."""
    p = PROCESSED_DIR / "ultimate_scores_2024.parquet"
    ts = dt.datetime.fromtimestamp(p.stat().st_mtime)
    return ts.strftime("%d/%m/%Y %H:%M")
