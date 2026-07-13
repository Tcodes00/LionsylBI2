"""
Shared readers for the user's Settings -> Preferences choices (chart
palette, currency, date format). Centralised here so every tab applies
the same preference the same way instead of each one hardcoding its own
colors/symbols - this is what makes changing a preference in Settings
actually show up elsewhere in the app, not just in a local preview.
"""
from __future__ import annotations
import streamlit as st

PALETTE_SWATCHES = {
    "LionsylAI (default)": ["#6C63FF", "#0AEFFF", "#10B981", "#F59E0B"],
    "Viridis": ["#440154", "#31688e", "#35b779", "#fde725"],
    "Plasma":  ["#0d0887", "#9c179e", "#ed7953", "#f0f921"],
    "Inferno": ["#000004", "#781c6d", "#ed6925", "#fcffa4"],
    "Blues":   ["#f7fbff", "#6baed6", "#2171b5", "#08306b"],
}

# Continuous (magnitude-based) equivalent of each palette, for charts that
# color by value rather than by category. Not used for diverging/
# correlation visuals - those need a fixed red-blue scale to stay
# readable no matter what palette is selected.
PALETTE_CONTINUOUS = {
    "LionsylAI (default)": "Purp",
    "Viridis": "Viridis", "Plasma": "Plasma", "Inferno": "Inferno", "Blues": "Blues",
}

CURRENCY_SYMBOLS = {"USD ($)": "$", "BDT (৳)": "৳", "EUR (€)": "€", "GBP (£)": "£", "JPY (¥)": "¥"}
DATEFMT_STRFTIME = {"YYYY-MM-DD": "%Y-%m-%d", "DD/MM/YYYY": "%d/%m/%Y", "MM/DD/YYYY": "%m/%d/%Y"}


def chart_colors() -> list[str]:
    """Discrete 4-color sequence for category-based charts (pie, single-
    series histogram/box/violin), reflecting the saved palette preference."""
    key = st.session_state.get("pref_palette", "LionsylAI (default)")
    return PALETTE_SWATCHES.get(key, PALETTE_SWATCHES["LionsylAI (default)"])


def chart_scale() -> str:
    """Continuous Plotly colorscale name for magnitude-based charts
    (bar-by-value, density), reflecting the same preference."""
    key = st.session_state.get("pref_palette", "LionsylAI (default)")
    return PALETTE_CONTINUOUS.get(key, PALETTE_CONTINUOUS["LionsylAI (default)"])


def currency_symbol() -> str:
    key = st.session_state.get("pref_currency", "USD ($)")
    return CURRENCY_SYMBOLS.get(key, "$")


def date_format() -> str:
    key = st.session_state.get("pref_datefmt", "YYYY-MM-DD")
    return DATEFMT_STRFTIME.get(key, "%Y-%m-%d")
