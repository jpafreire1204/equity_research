"""Brand-consistent Plotly theme."""
import plotly.graph_objects as go

BRAND_BORDO = "#5C1A2A"
BRAND_CREME = "#F3EFE6"
BRAND_DOURADO = "#C4A35A"
BRAND_TEXT = "#1C1C1C"
BRAND_MUTED = "#6B6B6B"

COLORSCALE_SEQUENTIAL = [
    [0.0, "#F3EFE6"],
    [0.5, "#C4A35A"],
    [1.0, "#5C1A2A"],
]

COLORSCALE_DIVERGING = [
    [0.0, "#5C1A2A"],
    [0.5, "#F3EFE6"],
    [1.0, "#2D5F2E"],
]


def apply_brand_layout(
    fig: go.Figure, title: str | None = None, height: int = 420
) -> go.Figure:
    fig.update_layout(
        font=dict(family="Poppins, sans-serif", size=12, color=BRAND_TEXT),
        title=dict(text=title, font=dict(size=16, color=BRAND_TEXT)) if title else None,
        paper_bgcolor=BRAND_CREME,
        plot_bgcolor=BRAND_CREME,
        margin=dict(l=60, r=30, t=60 if title else 30, b=50),
        height=height,
        xaxis=dict(showgrid=False, color=BRAND_MUTED),
        yaxis=dict(showgrid=False, color=BRAND_MUTED),
        coloraxis_colorbar=dict(
            outlinewidth=0,
            tickfont=dict(color=BRAND_MUTED, size=10),
        ),
    )
    return fig
