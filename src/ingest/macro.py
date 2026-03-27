"""
Macro data ingestion module.

Fetches Brazilian macroeconomic series from BCB/SGS API:
- Selic (daily target rate) — código 11
- IPCA (monthly inflation) — código 433
- USD/BRL PTAX — código 1

Resamples to monthly frequency and saves to parquet.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# ── Project paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# ── BCB/SGS series ─────────────────────────────────────────────────────────
SERIES = {
    "selic_daily": 11,
    "ipca_monthly": 433,
    "usdbrl": 1,
}

START_DATE = "01/01/2020"  # dd/mm/yyyy format for BCB API
END_DATE = "31/12/2025"


def _fetch_bcb_series(codigo: int, name: str) -> pd.DataFrame | None:
    """
    Fetch a single time series from BCB/SGS API.
    Returns a DataFrame with columns [date, value] or None on failure.
    """
    url = (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}"
        f"/dados?formato=json&dataInicial={START_DATE}&dataFinal={END_DATE}"
    )

    try:
        print(f"[{datetime.now()}] Fetching BCB series {codigo} ({name}) ...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"[{datetime.now()}] WARNING: Failed to fetch {url} — {e}")
        return None
    except ValueError as e:
        print(f"[{datetime.now()}] WARNING: Invalid JSON from BCB series {codigo} — {e}")
        return None

    if not data:
        print(f"[{datetime.now()}] WARNING: Empty response for BCB series {codigo}")
        return None

    df = pd.DataFrame(data)
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])

    print(f"[{datetime.now()}] Fetched {len(df)} observations for {name}")
    return df


def ingest_macro() -> pd.DataFrame:
    """
    Fetch all macro series, resample to monthly, and merge.
    Saves to data/processed/macro_monthly.parquet.
    """
    series_data = {}

    for name, codigo in SERIES.items():
        df = _fetch_bcb_series(codigo, name)
        if df is not None:
            # Set date as index for resampling
            df = df.set_index("date")
            # Resample to month-end; use last observation for rates/prices
            monthly = df["value"].resample("ME").last()
            series_data[name] = monthly

    if not series_data:
        print(f"[{datetime.now()}] ERROR: No macro data collected!")
        return pd.DataFrame()

    # Merge all series on date
    result = pd.DataFrame(series_data)
    result.index.name = "date"
    result = result.reset_index()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    result.to_parquet(PROCESSED_DIR / "macro_monthly.parquet", index=False)
    print(f"[{datetime.now()}] Saved macro_monthly.parquet — {len(result)} rows")
    return result


def run():
    """Run full macro data ingestion."""
    print(f"[{datetime.now()}] === Macro Data Ingestion Start ===")
    macro = ingest_macro()
    print(f"[{datetime.now()}] === Macro Data Ingestion Complete ===")
    return macro


if __name__ == "__main__":
    run()
