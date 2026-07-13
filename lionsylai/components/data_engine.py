"""
LionsylAI – Data Engine
Universal loader, cleaner, and financial column detector.
"""

from __future__ import annotations

import io
import logging
from typing import Optional, Dict, List, Any, Tuple

import numpy as np
import pandas as pd
import streamlit as st

log = logging.getLogger("lionsylai.data")

SUPPORTED_FORMATS = ["csv", "xlsx", "xls", "xlsm", "json", "parquet", "tsv", "feather"]

FINANCIAL_KEYWORDS: Dict[str, List[str]] = {
    "revenue":  ["revenue", "sales", "income", "turnover", "rev", "sale", "amount", "price", "gross"],
    "cost":     ["cost", "expense", "cogs", "spending", "expenditure", "outflow", "opex", "capex"],
    "profit":   ["profit", "margin", "net", "earnings", "ebitda", "ebit", "noi", "operating_income"],
    "quantity": ["quantity", "qty", "volume", "units", "count", "orders", "transactions"],
    "category": ["category", "type", "department", "segment", "product", "division", "region", "group"],
    "date":     ["date", "time", "month", "year", "quarter", "period", "timestamp", "created", "updated"],
    "customer": ["customer", "client", "user", "account", "buyer", "subscriber"],
    "region":   ["region", "area", "territory", "location", "city", "state", "country", "zone"],
}


# ─────────────────────────────────────────────────────────────
# Loader
# ─────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_file(uploaded_file) -> Optional[pd.DataFrame]:
    """Read any supported file format into a DataFrame."""
    if uploaded_file is None:
        return None
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    try:
        uploaded_file.seek(0)
        raw = uploaded_file.read()
        buf = io.BytesIO(raw)

        if ext == "csv":
            for enc in ["utf-8", "latin-1", "cp1252"]:
                try:
                    buf.seek(0)
                    df = pd.read_csv(buf, encoding=enc, low_memory=False)
                    break
                except (UnicodeDecodeError, Exception):
                    continue
            else:
                buf.seek(0)
                df = pd.read_csv(buf, encoding_errors="ignore", low_memory=False)

        elif ext in ("xlsx", "xls", "xlsm"):
            df = pd.read_excel(buf, engine="openpyxl")

        elif ext == "json":
            buf.seek(0)
            df = pd.read_json(buf)

        elif ext == "parquet":
            df = pd.read_parquet(buf)

        elif ext in ("tsv", "txt"):
            buf.seek(0)
            df = pd.read_csv(buf, sep="\t", low_memory=False)

        elif ext == "feather":
            df = pd.read_feather(buf)

        else:
            st.error(f"Unsupported format: .{ext}")
            return None

        return clean_dataframe(df)

    except Exception as e:
        st.error(f"Error loading **{uploaded_file.name}**: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# Cleaner
# ─────────────────────────────────────────────────────────────

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Robust cleaning: dedup columns, fill nulls, parse dates, trim strings."""
    if df is None or df.empty:
        return df

    df = df.copy()

    # 1. Remove fully-empty rows/cols
    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)

    # 2. Drop unnamed index columns
    unnamed = [c for c in df.columns if str(c).startswith("Unnamed")]
    df.drop(columns=unnamed, inplace=True, errors="ignore")

    # 3. Deduplicate column names
    df.columns = _dedup_cols(df.columns)

    # 4. Drop duplicate rows
    df.drop_duplicates(inplace=True)

    # 5. Parse dates
    for col in df.columns:
        if any(kw in col.lower() for kw in ["date", "time", "month", "year", "period", "timestamp"]):
            try:
                df[col] = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
            except Exception:
                pass

    # 6. Fill missing values
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            median = df[col].median()
            fill_val = float(median) if not pd.isna(median) else 0.0
            df[col] = df[col].fillna(fill_val)
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            pass  # keep NaT
        else:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": "Unknown", "None": "Unknown",
                                       "<NA>": "Unknown", "": "Unknown"})

    df.reset_index(drop=True, inplace=True)
    return df


def _dedup_cols(cols) -> List[str]:
    seen: Dict[str, int] = {}
    out = []
    for c in cols:
        c = str(c)
        if c in seen:
            seen[c] += 1
            out.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            out.append(c)
    return out


# ─────────────────────────────────────────────────────────────
# Financial column detector
# ─────────────────────────────────────────────────────────────

def detect_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    """Map semantic categories to column names found in df."""
    result: Dict[str, List[str]] = {k: [] for k in FINANCIAL_KEYWORDS}
    for col in df.columns:
        col_l = col.lower()
        for category, keywords in FINANCIAL_KEYWORDS.items():
            if any(kw in col_l for kw in keywords):
                result[category].append(col)
    return result


def numeric_cols(df: pd.DataFrame) -> List[str]:
    return df.select_dtypes(include=[np.number]).columns.tolist()


def categorical_cols(df: pd.DataFrame) -> List[str]:
    return df.select_dtypes(include=["object", "category"]).columns.tolist()


def date_cols(df: pd.DataFrame) -> List[str]:
    return df.select_dtypes(include=["datetime64"]).columns.tolist()


def all_cols(df: pd.DataFrame) -> List[str]:
    return df.columns.tolist()


# ─────────────────────────────────────────────────────────────
# Quick-stats for sidebar
# ─────────────────────────────────────────────────────────────

def quick_stats(df: pd.DataFrame) -> Dict[str, Any]:
    n_num = len(numeric_cols(df))
    n_cat = len(categorical_cols(df))
    n_dt  = len(date_cols(df))
    missing_pct = (df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100) if not df.empty else 0
    return {
        "rows":       len(df),
        "cols":       len(df.columns),
        "numeric":    n_num,
        "categorical":n_cat,
        "datetime":   n_dt,
        "missing_pct":round(missing_pct, 1),
    }


# ─────────────────────────────────────────────────────────────
# Growth calculation helper
# ─────────────────────────────────────────────────────────────

def calc_growth(series: pd.Series) -> float:
    """Overall percentage growth from first to last valid value."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 2 or s.iloc[0] == 0:
        return 0.0
    return float((s.iloc[-1] - s.iloc[0]) / abs(s.iloc[0]) * 100)
