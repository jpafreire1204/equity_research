"""
CVM DFP (Demonstrações Financeiras Padronizadas) ingestion module.

Downloads annual financial statements from CVM open data portal,
parses ZIP/CSV files, filters by the 10-company universe, and
produces standardized parquet tables.
"""

import io
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# ── Project paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# ── CNPJ ↔ Ticker mapping ─────────────────────────────────────────────────
CNPJ_TICKER = {
    "60.872.504/0001-23": ("ITUB4", "Bancos"),
    "60.746.948/0001-12": ("BBDC4", "Bancos"),
    "00.000.000/0001-91": ("BBAS3", "Bancos"),
    "90.400.888/0001-42": ("SANB11", "Bancos"),
    "28.195.667/0001-06": ("ABCB4", "Bancos"),
    "02.474.103/0001-19": ("EGIE3", "Energia Elétrica"),
    "03.220.438/0001-73": ("EQTL3", "Energia Elétrica"),
    "02.429.144/0001-93": ("CPFE3", "Energia Elétrica"),
    "07.859.971/0001-30": ("TAEE11", "Energia Elétrica"),
    "17.155.730/0001-64": ("CMIG4", "Energia Elétrica"),
}

# Reverse lookup: ticker -> cnpj
TICKER_CNPJ = {v[0]: k for k, v in CNPJ_TICKER.items()}

# Set of CNPJs for fast filtering (CVM uses plain digits format)
CNPJ_SET = set(CNPJ_TICKER.keys())
CNPJ_DIGITS_SET = {c.replace(".", "").replace("/", "").replace("-", "") for c in CNPJ_SET}

# ── CVM DFP URLs ───────────────────────────────────────────────────────────
BASE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/"

YEARS = list(range(2020, 2025))  # 2020..2024


def _dfp_zip_url(year: int) -> str:
    """Return the URL for the DFP ZIP file of a given year."""
    return f"{BASE_URL}dfp_cia_aberta_{year}.zip"


def _download_zip(url: str) -> zipfile.ZipFile | None:
    """Download a ZIP file from *url* and return a ZipFile object, or None on failure."""
    try:
        print(f"[{datetime.now()}] Downloading {url} ...")
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        print(f"[{datetime.now()}] OK — {len(resp.content) / 1e6:.1f} MB")
        return zipfile.ZipFile(io.BytesIO(resp.content))
    except requests.RequestException as e:
        print(f"[{datetime.now()}] WARNING: Failed to fetch {url} — {e}")
        return None


def _normalize_cnpj(raw: str) -> str:
    """Strip CNPJ to digits only."""
    return str(raw).replace(".", "").replace("/", "").replace("-", "").strip()


def _read_csv_from_zip(zf: zipfile.ZipFile, name_contains: str) -> pd.DataFrame | None:
    """Read the first CSV inside *zf* whose name contains *name_contains*."""
    for fname in zf.namelist():
        if name_contains.lower() in fname.lower() and fname.endswith(".csv"):
            with zf.open(fname) as f:
                try:
                    df = pd.read_csv(
                        f,
                        sep=";",
                        encoding="latin-1",
                        dtype=str,
                        on_bad_lines="skip",
                    )
                    return df
                except Exception as e:
                    print(f"[{datetime.now()}] WARNING: Could not parse {fname} — {e}")
                    return None
    return None


def _filter_universe(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows matching our 10-company universe by CNPJ."""
    if df is None or df.empty:
        return pd.DataFrame()

    # CVM files use column CNPJ_CIA
    cnpj_col = None
    for col in df.columns:
        if "cnpj" in col.lower():
            cnpj_col = col
            break
    if cnpj_col is None:
        return pd.DataFrame()

    df["_cnpj_clean"] = df[cnpj_col].apply(_normalize_cnpj)
    filtered = df[df["_cnpj_clean"].isin(CNPJ_DIGITS_SET)].copy()
    filtered.drop(columns=["_cnpj_clean"], inplace=True)
    return filtered


def _add_ticker_sector(df: pd.DataFrame) -> pd.DataFrame:
    """Add ticker and sector columns based on CNPJ."""
    cnpj_col = None
    for col in df.columns:
        if "cnpj" in col.lower():
            cnpj_col = col
            break
    if cnpj_col is None:
        return df

    def _lookup(raw_cnpj):
        digits = _normalize_cnpj(raw_cnpj)
        # Rebuild formatted CNPJ for lookup
        formatted = f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
        return CNPJ_TICKER.get(formatted, (None, None))

    df[["ticker", "sector"]] = df[cnpj_col].apply(lambda x: pd.Series(_lookup(x)))
    df["cnpj"] = df[cnpj_col]
    return df


# ── Main ingestion functions ───────────────────────────────────────────────

def ingest_fundamentals() -> pd.DataFrame:
    """
    Download and parse DFP ZIPs for 2020-2024.
    Returns a long-format DataFrame with balance sheet + cash flow accounts.
    Saves to data/processed/fundamentals_long.parquet.
    """
    all_frames = []

    # Sheet suffixes we want: BPA (Ativo), BPP (Passivo), DFC_MI (DFC método indireto)
    sheets = ["BPA_con", "BPP_con", "DFC_MI_con"]

    for year in YEARS:
        url = _dfp_zip_url(year)
        zf = _download_zip(url)
        if zf is None:
            continue

        for sheet in sheets:
            df = _read_csv_from_zip(zf, sheet)
            if df is None or df.empty:
                print(f"[{datetime.now()}] WARNING: Sheet {sheet} not found in {year} ZIP")
                continue

            df = _filter_universe(df)
            if df.empty:
                continue

            df = _add_ticker_sector(df)

            # Standardize columns
            # CVM columns typically: DT_REFER, CD_CONTA, DS_CONTA, VL_CONTA
            dt_col = [c for c in df.columns if "DT_REFER" in c.upper() or "DT_FIM_EXERC" in c.upper()]
            cd_col = [c for c in df.columns if "CD_CONTA" in c.upper()]
            ds_col = [c for c in df.columns if "DS_CONTA" in c.upper()]
            vl_col = [c for c in df.columns if "VL_CONTA" in c.upper()]

            if not (dt_col and cd_col and ds_col and vl_col):
                continue

            subset = df[["ticker", "sector", "cnpj", dt_col[0], cd_col[0], ds_col[0], vl_col[0]]].copy()
            subset.columns = ["ticker", "sector", "cnpj", "date", "account_code", "account_name", "value"]

            # Extract year from date
            subset["year"] = pd.to_datetime(subset["date"], errors="coerce").dt.year
            subset["value"] = pd.to_numeric(subset["value"], errors="coerce")
            subset = subset[["ticker", "sector", "cnpj", "year", "account_code", "account_name", "value"]]

            all_frames.append(subset)

    if not all_frames:
        print(f"[{datetime.now()}] ERROR: No fundamentals data collected!")
        return pd.DataFrame()

    result = pd.concat(all_frames, ignore_index=True)
    result = result.dropna(subset=["ticker", "year", "value"])
    result = result.drop_duplicates()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    result.to_parquet(PROCESSED_DIR / "fundamentals_long.parquet", index=False)
    print(f"[{datetime.now()}] Saved fundamentals_long.parquet — {len(result)} rows")
    return result


def ingest_income() -> pd.DataFrame:
    """
    Download and parse DFP DRE (income statement) for 2020-2024.
    Returns a DataFrame with revenue, net_income, ebit per ticker/year.
    Saves to data/processed/income_long.parquet.
    """
    all_frames = []

    for year in YEARS:
        url = _dfp_zip_url(year)
        zf = _download_zip(url)
        if zf is None:
            continue

        df = _read_csv_from_zip(zf, "DRE_con")
        if df is None or df.empty:
            print(f"[{datetime.now()}] WARNING: DRE sheet not found in {year} ZIP")
            continue

        df = _filter_universe(df)
        if df.empty:
            continue

        df = _add_ticker_sector(df)

        # Standardize
        dt_col = [c for c in df.columns if "DT_FIM_EXERC" in c.upper() or "DT_REFER" in c.upper()]
        cd_col = [c for c in df.columns if "CD_CONTA" in c.upper()]
        vl_col = [c for c in df.columns if "VL_CONTA" in c.upper()]

        if not (dt_col and cd_col and vl_col):
            continue

        subset = df[["ticker", "sector", dt_col[0], cd_col[0], vl_col[0]]].copy()
        subset.columns = ["ticker", "sector", "date", "account_code", "value"]
        subset["year"] = pd.to_datetime(subset["date"], errors="coerce").dt.year
        subset["value"] = pd.to_numeric(subset["value"], errors="coerce")

        all_frames.append(subset)

    if not all_frames:
        print(f"[{datetime.now()}] ERROR: No income data collected!")
        return pd.DataFrame()

    raw = pd.concat(all_frames, ignore_index=True)
    raw = raw.dropna(subset=["ticker", "year", "value"])

    # Map account codes to standard names.
    # CVM DRE account codes vary by company type:
    #   Revenue:    3.01 (standard + banks)
    #   EBIT:       3.05 (standard), 3.08/3.07 (banks)
    #   Net Income: 3.11 (standard), 3.10/3.09 (banks using different DRE layout)
    # Fallback priority: try each code in order, keep first non-empty match per ticker/year.
    INCOME_ACCOUNTS = {
        "revenue": ["3.01", "3.03"],
        "net_income": ["3.11", "3.10", "3.09"],
        "ebit": ["3.05", "3.08", "3.07"],
    }

    records = []
    for (ticker, sector, year), grp in raw.groupby(["ticker", "sector", "year"]):
        row = {"ticker": ticker, "sector": sector, "year": year}
        for field, codes in INCOME_ACCOUNTS.items():
            row[field] = None
            for code in codes:
                match = grp[grp["account_code"] == code]
                if not match.empty:
                    row[field] = match["value"].iloc[-1]  # last occurrence (end-of-period)
                    break
        records.append(row)

    pivoted = pd.DataFrame(records)

    # Fallback: fill missing net_income from DFC (6.01.01.01 = "Lucro Líquido")
    # in fundamentals_long.parquet (cash flow statement starts with net income).
    fund_path = PROCESSED_DIR / "fundamentals_long.parquet"
    if fund_path.exists():
        fund = pd.read_parquet(fund_path)
        dfc_ni = fund[fund["account_code"] == "6.01.01.01"].copy()
        # Take last entry per ticker/year (end-of-period)
        dfc_ni = (
            dfc_ni.sort_values("value")
            .groupby(["ticker", "year"])["value"]
            .last()
            .reset_index()
            .rename(columns={"value": "net_income_dfc"})
        )
        pivoted = pivoted.merge(dfc_ni, on=["ticker", "year"], how="left")
        mask = pivoted["net_income"].isna() & pivoted["net_income_dfc"].notna()
        if mask.any():
            filled = pivoted.loc[mask, "ticker"].unique()
            print(f"[DFC fallback] Filled net_income for: {list(filled)}")
            pivoted.loc[mask, "net_income"] = pivoted.loc[mask, "net_income_dfc"]
        pivoted.drop(columns=["net_income_dfc"], inplace=True)

    # Ensure all expected columns exist
    for col in ["revenue", "net_income", "ebit"]:
        if col not in pivoted.columns:
            pivoted[col] = None

    pivoted = pivoted[["ticker", "sector", "year", "revenue", "net_income", "ebit"]]

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    pivoted.to_parquet(PROCESSED_DIR / "income_long.parquet", index=False)
    print(f"[{datetime.now()}] Saved income_long.parquet — {len(pivoted)} rows")
    return pivoted


def run():
    """Run full CVM ingestion pipeline."""
    print(f"[{datetime.now()}] === CVM Ingestion Start ===")
    fundamentals = ingest_fundamentals()
    income = ingest_income()
    print(f"[{datetime.now()}] === CVM Ingestion Complete ===")
    return fundamentals, income


if __name__ == "__main__":
    run()
