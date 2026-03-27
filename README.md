# AI Equity Research Lab — FGV EAESP

Pipeline completo de avaliacao de empresas brasileiras com IA.

**Universo:** 10 empresas | **Setores:** Bancos + Energia Eletrica | **Periodo:** 2020–2024

| Setor | Tickers |
|---|---|
| Bancos | ITUB4, BBDC4, BBAS3, SANB11, ABCB4 |
| Energia Eletrica | EGIE3, EQTL3, CPFE3, TAEE11, CMIG4 |

## Estrutura

```
equity_research/
├── data/
│   ├── processed/          # Parquets intermediarios e finais
│   │   ├── fundamentals_long.parquet
│   │   ├── income_long.parquet
│   │   ├── prices_daily.parquet
│   │   ├── macro_monthly.parquet
│   │   ├── kpis_wide.parquet
│   │   ├── scores_2024.parquet
│   │   ├── sentiment_scores.parquet
│   │   ├── textual_index.parquet
│   │   ├── master_scores_2024.parquet
│   │   ├── feature_matrix.parquet
│   │   ├── feature_importance.parquet
│   │   ├── supervised_predictions_2024.parquet
│   │   ├── clusters_2024.parquet
│   │   ├── master_scores_final.parquet
│   │   ├── multiples_2024.parquet
│   │   ├── scenarios_2024.parquet
│   │   ├── valuation_score_2024.parquet
│   │   └── ultimate_scores_2024.parquet
│   ├── output/             # Dossiers e relatorio PDF
│   └── raw/                # Textos coletados (JSON)
├── notebooks/
│   ├── 00_master.ipynb     # Pipeline completo end-to-end
│   ├── 01_ingestion.ipynb  # Aula 1-2: Ingestao de dados
│   ├── 02_kpis.ipynb       # Aula 3: Engenharia de KPIs
│   ├── 03_nlp.ipynb        # Aula 4: NLP e sentimento
│   ├── 04_models.ipynb     # Aula 5: Modelos de IA
│   ├── 05_valuation.ipynb  # Aula 6: Valuation
│   └── 06_agent.ipynb      # Aula 7: Agente de IA
├── src/
│   ├── ingest/             # CVM, Yahoo Finance, BCB/SGS
│   │   ├── cvm.py
│   │   ├── market.py
│   │   └── macro.py
│   ├── features/           # KPIs e score composto
│   │   ├── kpis.py
│   │   └── score.py
│   ├── nlp/                # Coleta de textos e sentimento
│   │   ├── collector.py
│   │   ├── sentiment.py
│   │   └── textual_index.py
│   ├── models/             # ML supervisionado e nao-supervisionado
│   │   ├── features.py
│   │   ├── supervised.py
│   │   └── unsupervised.py
│   ├── valuation/          # Multiplos, cenarios, score final
│   │   ├── multiples.py
│   │   ├── scenarios.py
│   │   └── valuation_score.py
│   ├── agent/              # Agente autonomo + CLI
│   │   ├── tools.py
│   │   ├── agent.py
│   │   ├── dossier_formatter.py
│   │   ├── company_names.py
│   │   └── cli.py
│   └── report/             # Geracao de relatorio PDF
│       └── report_generator.py
└── requirements.txt
```

## Como Rodar

### Instalacao

```bash
pip install -r requirements.txt
```

### Pipeline completo

```bash
jupyter notebook notebooks/00_master.ipynb
```

### Agente de IA

```bash
python -m src.agent.cli --tickers ITUB4 EGIE3 CMIG4 --profile base
python -m src.agent.cli --tickers all --profile conservative
python -m src.agent.cli --tickers all --profile aggressive --output pdf
```

### Relatorio PDF

```bash
python -m src.report.report_generator
```

## Fontes de Dados

- **CVM Dados Abertos:** https://dados.cvm.gov.br/ (DFP consolidado)
- **BCB/SGS API:** https://api.bcb.gov.br/ (Selic, IPCA, USD/BRL)
- **Google News RSS** (sem chave de API)
- **Yahoo Finance v8 API** via `yfinance` (sem chave de API)

## Resultados (2024)

| Rank | Ticker | Empresa | Score | Rec | Upside Base |
|------|--------|---------|-------|-----|-------------|
| 1 | ITUB4 | Itau Unibanco | 78.5 | Buy | N/A |
| 2 | EGIE3 | Engie Brasil | 69.8 | Buy | +2.1% |
| 3 | CMIG4 | Cemig | 66.4 | Buy | +2.1% |
| 4 | CPFE3 | CPFL Energia | 65.7 | Buy | +2.0% |
| 5 | BBAS3 | Banco do Brasil | 63.7 | Hold | +4.0% |
| 6 | ABCB4 | Banco ABC Brasil | 59.1 | Hold | +4.0% |
| 7 | TAEE11 | Taesa | 52.9 | Hold | +2.0% |
| 8 | BBDC4 | Bradesco | 46.7 | Hold | +3.9% |
| 9 | SANB11 | Santander Brasil | 40.7 | Sell | +4.0% |
| 10 | EQTL3 | Equatorial Energia | 36.2 | Sell | +2.0% |

**Score = 50% fundamental+NLP + 30% valuation + 20% ML probability**

## Limitacoes

1. **Universo restrito (n=10):** Baixo poder estatistico nos modelos ML. Mitigacao: ampliar para Ibovespa completo.
2. **Proxy EBITDA (+15% sobre EBIT):** Multiplos EV/EBITDA imprecisos. Mitigacao: usar DFC para D&A real.
3. **NLP via RSS:** Cobertura textual limitada. Mitigacao: integrar CVM Fatos Relevantes.
4. **Walk-forward com 4 anos:** Risco de overfitting com poucos folds. Mitigacao: expandir janela historica.
5. **ITUB4 net_income faltando:** Score parcial para o ticker lider. Mitigacao: verificar CNPJ alternativo no DFP.

## Boas Praticas

- Separacao treino/teste temporal (walk-forward, sem data leakage)
- Proxies documentados (EBITDA = EBIT x 1.15)
- Dados versionados em parquet
- Incerteza explicitada via 3 cenarios macro (Bull/Base/Bear)
- Agente com fallback gracioso (tool failure -> "DATA UNAVAILABLE")
- Relatorio com disclaimer automatico em todas as paginas
