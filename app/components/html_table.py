"""Render a pandas DataFrame as a brand-themed HTML table with proper word wrap."""
import html

import pandas as pd
import streamlit as st


def render_brand_table(df: pd.DataFrame, emphasis_col: str | None = None) -> None:
    """Render df as <table class='brand-table'>. emphasis_col gets bolder weight."""
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    rows_html = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            cls = ' class="col-emphasis"' if col == emphasis_col else ""
            cells.append(f"<td{cls}>{html.escape(str(row[col]))}</td>")
        rows_html.append("<tr>" + "".join(cells) + "</tr>")
    body = "".join(rows_html)
    st.markdown(
        f'<table class="brand-table"><thead><tr>{head}</tr></thead>'
        f'<tbody>{body}</tbody></table>',
        unsafe_allow_html=True,
    )
