# AI Equity Research Lab

University project (FGV EAESP) — Aulas 1–3 of 8.

## Universe

| Sector | Tickers |
|---|---|
| Bancos | ITUB4, BBDC4, BBAS3, SANB11, ABCB4 |
| Energia Elétrica | EGIE3, EQTL3, CPFE3, TAEE11, CMIG4 |

## How to run

```bash
pip install -r requirements.txt
jupyter notebook
# Open notebooks/01_ingestion.ipynb and run all cells
```

## Pipeline outputs

| File | Description |
|---|---|
| `data/processed/fundamentals_long.parquet` | Balance sheet + cash flow (long format) |
| `data/processed/income_long.parquet` | Revenue, EBIT, Net Income per ticker/year |
| `data/processed/prices_daily.parquet` | Daily OHLCV + returns for 10 tickers + Ibovespa |
| `data/processed/macro_monthly.parquet` | Selic, IPCA, USD/BRL (monthly) |

| `data/processed/kpis_wide.parquet` | All KPIs per ticker per year (2020–2024) |
| `data/processed/scores_2024.parquet` | Composite score 0–100 + rankings for 2024 |

## Data sources

- **CVM DFP**: https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp
- **Yahoo Finance**: daily prices via `yfinance`
- **BCB/SGS**: macro series via REST API

## Aula 3 — KPI Engineering

### CVM account codes used

| KPI input | Utilities (standard) | Banks (COSIF) |
|---|---|---|
| Total Assets | `1` (Ativo Total) | `1` (Ativo Total) |
| Current Assets | `1.01` (Ativo Circulante) | N/A |
| Cash | `1.01.01` (Caixa e Equivalentes) | `1.01` (Caixa e Equivalentes) |
| Current Liabilities | `2.01` (Passivo Circulante) | N/A |
| Total Equity (PL) | `2.03` (PL Consolidado) | `2.07` or `2.08` (varies by bank) |
| Short-term Debt | `2.01.04` (Empréstimos e Financiamentos) | N/A |
| Long-term Debt | `2.02.01` (Empréstimos e Financiamentos) | N/A |
| Revenue | DRE `3.01` | DRE `3.01` |
| EBIT | DRE `3.05` | DRE `3.05` |
| Net Income | DRE `3.11` | DRE `3.11` |

### Known limitations

- **Banks:** `current_ratio`, `debt_to_equity`, and `net_debt_to_ebit` are set to NaN — banks fund via deposits, not traditional debt, so these ratios are not meaningful.
- **ITUB4:** `net_income` is NaN across all years (DRE account `3.11` absent in DFP consolidated). ROE, ROA, net_margin, and net_income_cagr are unavailable.
- **ABCB4:** No 2024 DFP data available; 2023 is the most recent year for balance-sheet KPIs. Market KPIs use 2024 price data normally.
- **EBITDA proxy:** `net_debt_to_ebit` uses EBIT (account `3.05`) instead of EBITDA, since D&A is not directly available from DFP top-level accounts.
- **Duplicate rows in CVM:** Each account appears twice per year (beginning/end of period); the pipeline keeps the last occurrence (end-of-period balance).
- **CAGR:** Computed over 2020–2024 (or the available range). Negative base values yield NaN.
