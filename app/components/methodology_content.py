"""Static methodology content — tables, thresholds, narrative text."""
import pandas as pd

WALK_FORWARD = pd.DataFrame([
    {"Fold": 1, "Treino": "2020", "Teste": "2021",
     "ROC AUC": 0.844, "KS": 0.750, "Gini": 0.688},
    {"Fold": 2, "Treino": "2020-2021", "Teste": "2022",
     "ROC AUC": 0.500, "KS": 0.190, "Gini": 0.000},
    {"Fold": 3, "Treino": "2020-2022", "Teste": "2023",
     "ROC AUC": 0.417, "KS": 0.167, "Gini": -0.167},
])
WALK_FORWARD_MEAN = 0.587
WALK_FORWARD_STD = 0.226
WALK_FORWARD_KS_MEAN = 0.369
WALK_FORWARD_KS_STD = 0.330
WALK_FORWARD_GINI_MEAN = 0.174
WALK_FORWARD_GINI_STD = 0.453

PROFILE_WEIGHTS = pd.DataFrame([
    {"Componente": "Valuation", "Conservador": "35%", "Base": "25%", "Agressivo": "20%"},
    {"Componente": "Fundamentos", "Conservador": "30%", "Base": "35%", "Agressivo": "30%"},
    {"Componente": "Sentimento Textual", "Conservador": "25%", "Base": "25%", "Agressivo": "15%"},
    {"Componente": "Prob. Outperform", "Conservador": "10%", "Base": "15%", "Agressivo": "35%"},
])

TENSION_THRESHOLDS = pd.DataFrame([
    {
        "Driver": "Qualidade de fundamentos",
        "HIGH (bullish)": "ROE -2pp YoY E Margem -1pp YoY",
        "MEDIUM (bullish)": "Apenas um dos dois caiu",
        "Nota": "Para tese bearish, regras invertidas (HIGH = ROE +2pp E Margem +1pp).",
    },
    {
        "Driver": "Valuation atrativo",
        "HIGH (bullish)": "Trading >10% acima da mediana setorial",
        "MEDIUM (bullish)": "Premium de 0% a 10%",
        "Nota": "Para tese bearish, HIGH = trading >10% abaixo da mediana setorial.",
    },
    {
        "Driver": "Momentum positivo",
        "HIGH (bullish)": "Momentum 6m < -10% E 12m < 0%",
        "MEDIUM (bullish)": "Apenas um dos dois negativo",
        "Nota": "Para tese bearish, HIGH = 6m > +10% E 12m > 0%.",
    },
    {
        "Driver": "Sentimento de mercado",
        "HIGH (bullish)": "Índice textual < 30/100",
        "MEDIUM (bullish)": "Índice 30-50/100",
        "Nota": "Para tese bearish, HIGH = índice > 70/100.",
    },
    {
        "Driver": "Cenário macro",
        "HIGH (bullish)": "Bear scenario downside < -5%",
        "MEDIUM (bullish)": "Base scenario upside < 1%",
        "Nota": "Para tese bearish, HIGH = Bull scenario upside > +5%.",
    },
])

SENSITIVITY_TOTAL_PERTURBATIONS = 132
SENSITIVITY_FLIP_RATE = 0.000
SENSITIVITY_MEAN_SCORE_DELTA = 0.91
SENSITIVITY_MEAN_GAP_DELTA = 14.55

SENSITIVITY_BY_DRIVER = pd.DataFrame([
    {"Driver": "fundamentals_quality", "Δ Convicção": "±2", "Flip rate": 0.000,
     "|Δ Score| médio": 1.591, "|Δ Gap| médio": 19.394, "N": 66},
    {"Driver": "valuation_attractive", "Δ Convicção": "±2", "Flip rate": 0.000,
     "|Δ Score| médio": 0.000, "|Δ Gap| médio": 8.000, "N": 40},
    {"Driver": "sentiment_supportive", "Δ Convicção": "±2", "Flip rate": 0.000,
     "|Δ Score| médio": 0.938, "|Δ Gap| médio": 12.500, "N": 16},
    {"Driver": "macro_tailwind", "Δ Convicção": "±2", "Flip rate": 0.000,
     "|Δ Score| médio": 0.000, "|Δ Gap| médio": 12.000, "N": 10},
])

SENSITIVITY_NARRATIVE = (
    "Cada uma das 39 teses históricas curadas foi reauditada variando a "
    "convicção declarada em ±2 pontos para cada driver, mantendo os demais "
    "constantes em 7/10 (baseline neutro-positivo). A taxa de flip de "
    "veredito é zero — confirmando que o veredito é dominado pelas regras "
    "determinísticas sobre evidência, e a convicção declarada modula "
    "principalmente o Gap de Convicção, não o resultado final."
)


LIMITATIONS = pd.DataFrame([
    {
        "Limitação": "Universo n=10",
        "Impacto": "Baixo poder estatístico nos modelos supervisionados",
        "Mitigação atual": "Resultados reportados com desvio-padrão; thresholds de tensão usam regras determinísticas, não ML.",
    },
    {
        "Limitação": "Proxy EBITDA (EBIT × 1.15)",
        "Impacto": "Múltiplos EV/EBITDA são aproximados, não exatos",
        "Mitigação atual": "Reportado nos cards de evidência; não usado isoladamente para decisão.",
    },
    {
        "Limitação": "Fonte de notícias via Google News RSS",
        "Impacto": "Cobertura limitada; pode subestimar sinais de empresas menos cobertas",
        "Mitigação atual": "Sentimento é apenas 25-35% do score final, dependendo do perfil.",
    },
    {
        "Limitação": "Walk-forward com 4 anos (2020-2023)",
        "Impacto": "Janela curta; modelo pode não generalizar para regimes não vistos",
        "Mitigação atual": "ROC AUC reportado por fold com transparência; auditor não usa o supervisionado para o veredito principal.",
    },
    {
        "Limitação": "Sentimento via half-life de 90 dias",
        "Impacto": "Notícias antigas pesam menos; choques recentes podem dominar",
        "Mitigação atual": "REFERENCE_DATE atualizado a cada execução do pipeline (hoje: data atual).",
    },
    {
        "Limitação": "Convicção declarada é auto-reportada",
        "Impacto": "Usuário pode inflar convicção para forçar o veredito desejado",
        "Mitigação atual": "Gap de Convicção é exposto separadamente do score; amplificação de severidade torna a auto-inflação custosa quando dados contradizem o driver.",
    },
])
