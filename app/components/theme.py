"""Brand theme injected into Streamlit."""
import streamlit as st

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif !important;
    color: #1C1C1C;
}

.stApp {
    background-color: #F3EFE6;
}

.block-container {
    padding-top: 2.5rem;
    padding-bottom: 4rem;
    max-width: 1200px;
}

h1, h2, h3, h4 {
    color: #1C1C1C;
    font-weight: 600;
    letter-spacing: -0.01em;
}

.stButton > button {
    background-color: #5C1A2A;
    color: #F3EFE6;
    border: none;
    padding: 0.6rem 1.6rem;
    font-weight: 500;
    border-radius: 6px;
    transition: opacity 0.15s;
}

.stButton > button:hover {
    opacity: 0.85;
    background-color: #5C1A2A;
    color: #F3EFE6;
}

.verdict-card {
    background: white;
    border-radius: 10px;
    padding: 1.8rem 2rem;
    margin-top: 1.5rem;
    border-left: 8px solid #C4A35A;
    border-top: 1px solid rgba(196, 163, 90, 0.2);
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.verdict-sustentavel { border-left-color: #2D5F2E; }
.verdict-ressalvas { border-left-color: #C4A35A; }
.verdict-fragilizada { border-left-color: #5C1A2A; }

.metric-block {
    background: white;
    border-radius: 8px;
    padding: 1.2rem;
    text-align: center;
}

.verdict-metric {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 130px;
}

.verdict-metric-value {
    font-size: 1.3rem;
    font-weight: 600;
    line-height: 1.25;
    color: #1C1C1C;
    margin-bottom: 0.3rem;
}

.verdict-metric.verdict-sustentavel { border-top: 4px solid #2D5F2E; }
.verdict-metric.verdict-ressalvas { border-top: 4px solid #C4A35A; }
.verdict-metric.verdict-fragilizada { border-top: 4px solid #5C1A2A; }

.metric-value {
    font-size: 2.4rem;
    font-weight: 600;
    color: #5C1A2A;
    line-height: 1;
}

.metric-label {
    font-size: 0.85rem;
    color: #6B6B6B;
    margin-top: 0.4rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.metric-caption {
    font-size: 0.78rem;
    color: #6B6B6B;
    margin-top: 0.5rem;
    line-height: 1.3;
    font-style: italic;
}

.tension-item {
    background: white;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
    border-left: 4px solid #C4A35A;
}

.tension-high { border-left-color: #5C1A2A; }
.tension-medium { border-left-color: #C4A35A; }
.tension-low { border-left-color: #8AB386; }

.tension-driver {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6B6B6B;
    font-weight: 500;
}

.tension-finding {
    font-size: 0.95rem;
    color: #1C1C1C;
    margin-top: 0.3rem;
}

/* Multiselect chips */
[data-baseweb="tag"] {
    background-color: #5C1A2A !important;
    color: #F3EFE6 !important;
}
[data-baseweb="tag"] svg {
    color: #F3EFE6 !important;
}

/* Radio button */
[data-baseweb="radio"] [role="radio"][aria-checked="true"] > div:first-child {
    background-color: #5C1A2A !important;
    border-color: #5C1A2A !important;
}

/* Selectbox focus + dropdown selected state */
[data-baseweb="select"] [aria-selected="true"] {
    background-color: rgba(92, 26, 42, 0.08) !important;
}

.brand-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    font-size: 0.92rem;
    margin-top: 1rem;
}

.brand-table thead {
    background-color: rgba(92, 26, 42, 0.06);
}

.brand-table th {
    text-align: left;
    padding: 0.85rem 1rem;
    font-weight: 600;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6B6B6B;
    border-bottom: 1px solid rgba(92, 26, 42, 0.1);
}

.brand-table td {
    padding: 0.85rem 1rem;
    vertical-align: top;
    color: #1C1C1C;
    border-bottom: 1px solid rgba(0,0,0,0.04);
    line-height: 1.45;
}

.brand-table tbody tr:last-child td {
    border-bottom: none;
}

.brand-table td.col-emphasis {
    font-weight: 500;
}
</style>
"""


def inject_theme() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
