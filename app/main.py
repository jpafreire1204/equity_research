"""Thesis Auditor — Streamlit entry point.

Run: streamlit run app/main.py
"""
import streamlit as st

from app.components.theme import inject_theme
from app.tabs import auditor, universo, metodologia

st.set_page_config(
    page_title="Auditor de Tese",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_theme()

st.markdown('<h1 style="margin-bottom:0.2rem;">Auditor de Tese</h1>', unsafe_allow_html=True)
st.caption("FGV EAESP — Inteligência Artificial Aplicada ao Mercado Financeiro")

tab_auditor, tab_universo, tab_metodologia = st.tabs([
    "Auditar Tese",
    "Explorar Universo",
    "Metodologia",
])

with tab_auditor:
    auditor.render()

with tab_universo:
    universo.render()

with tab_metodologia:
    metodologia.render()
