"""
LionsylAI – FP&A Engine
Data consolidation, budget management, month-end close,
cash management, financial report generation.
"""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger("lionsylai.fpa")


# ─────────────────────────────────────────────────────────────
# Data Consolidation
# ─────────────────────────────────────────────────────────────

class DataConsolidator:
    """Merge multiple uploaded files into a single DataFrame."""

    def __init__(self):
        self.consolidated: Optional[pd.DataFrame] = None
        self.source_stats: Dict[str, Dict] = {}

    def add_file(self, label: str, uploaded_file) -> bool:
        if uploaded_file is None:
            return False
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        try:
            uploaded_file.seek(0)
            raw = uploaded_file.read()
            buf = io.BytesIO(raw)

            if ext == "csv":
                df = pd.read_csv(buf, low_memory=False, encoding_errors="ignore")
            elif ext in ("xlsx", "xls", "xlsm"):
                df = pd.read_excel(buf, engine="openpyxl")
            elif ext == "pdf":
                df = self._extract_pdf(buf)
            elif ext == "json":
                df = pd.read_json(buf)
            else:
                return False

            if df is None or df.empty:
                return False

            df["_source"] = label
            self.source_stats[label] = {
                "rows": len(df),
                "cols": len(df.columns),
                "missing_pct": round(df.isnull().sum().sum() / (df.size) * 100, 1),
            }

            if self.consolidated is None:
                self.consolidated = df
            else:
                self.consolidated = pd.concat(
                    [self.consolidated, df], ignore_index=True
                )
            return True
        except Exception as e:
            log.warning(f"File add error ({label}): {e}")
            return False

    def _extract_pdf(self, buf: io.BytesIO) -> Optional[pd.DataFrame]:
        try:
            import pdfplumber
            dfs = []
            with pdfplumber.open(buf) as pdf:
                for page in pdf.pages:
                    for table in (page.extract_tables() or []):
                        if len(table) > 1:
                            try:
                                df = pd.DataFrame(table[1:], columns=table[0])
                                dfs.append(df)
                            except Exception:
                                pass
            return pd.concat(dfs, ignore_index=True) if dfs else None
        except Exception as e:
            log.warning(f"PDF extract error: {e}")
            return None

    def quality_report(self) -> pd.DataFrame:
        rows = []
        for src, stats in self.source_stats.items():
            rows.append({
                "Source": src,
                "Records": stats["rows"],
                "Columns": stats["cols"],
                "Missing %": stats["missing_pct"],
                "Quality Score": f"{max(0, 100 - stats['missing_pct'] * 2):.0f}%",
            })
        return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────
# Budget Manager
# ─────────────────────────────────────────────────────────────

DEFAULT_BUDGET: Dict[str, Any] = {
    "total_budget": 1_000_000,
    "fiscal_year": 2026,
    "currency": "USD",
    "departments": {
        "Marketing":      {"budget": 250_000, "actual": 265_000, "allocation": 0.25},
        "Operations":     {"budget": 400_000, "actual": 395_000, "allocation": 0.40},
        "R&D":            {"budget": 300_000, "actual": 310_000, "allocation": 0.30},
        "Sales":          {"budget": 200_000, "actual": 185_000, "allocation": 0.20},
        "Administration": {"budget": 100_000, "actual": 123_500, "allocation": 0.10},
    },
}


def budget_from_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Auto-generate budget structure from a dataset."""
    num_cols = df.select_dtypes(include=[np.number]).columns
    cat_cols = df.select_dtypes(include=["object", "category"]).columns

    if len(num_cols) == 0:
        return DEFAULT_BUDGET.copy()

    total = float(df[num_cols[0]].sum())
    depts = {}

    if len(cat_cols) > 0:
        cat_col = cat_cols[0]
        top_cats = df[cat_col].value_counts().head(6).index.tolist()
        for cat in top_cats:
            subset = df[df[cat_col] == cat]
            actual = float(subset[num_cols[0]].sum())
            alloc = actual / total if total > 0 else 1 / len(top_cats)
            depts[str(cat)] = {
                "budget": total * alloc,
                "actual": actual,
                "allocation": alloc,
            }
    else:
        depts = DEFAULT_BUDGET["departments"]

    return {
        "total_budget": total,
        "fiscal_year": datetime.now().year,
        "currency": "USD",
        "departments": depts,
    }


def budget_variance_df(budget_data: Dict[str, Any]) -> pd.DataFrame:
    """Return department variance table."""
    rows = []
    for dept, d in budget_data["departments"].items():
        b, a = d["budget"], d["actual"]
        var = a - b
        var_pct = (var / b * 100) if b else 0
        rows.append({
            "Department": dept,
            "Budgeted ($)": b,
            "Actual ($)": a,
            "Variance ($)": var,
            "Variance %": round(var_pct, 1),
            "Status": "🔴 Over" if var_pct > 5 else ("🟢 Under" if var_pct < -5 else "🟡 On Target"),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────
# Month-End Close
# ─────────────────────────────────────────────────────────────

def month_end_close(
    df: pd.DataFrame,
    recon_cols: Optional[Tuple[str, str]] = None,
) -> Dict[str, Any]:
    """Run month-end reconciliation and build summary statements."""
    result: Dict[str, Any] = {
        "close_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "Completed",
    }

    # ── Reconciliation ───────────────────────────────────────
    if recon_cols and len(recon_cols) == 2:
        c1, c2 = recon_cols
        s1 = pd.to_numeric(df[c1], errors="coerce").fillna(0)
        s2 = pd.to_numeric(df[c2], errors="coerce").fillna(0)
        diff = s1 - s2
        recon_df = pd.DataFrame({"Col_A": s1, "Col_B": s2, "Difference": diff})
        result["reconciliation"] = recon_df
        result["recon_matched"] = int((diff.abs() < 0.01).sum())
        result["recon_unmatched"] = int((diff.abs() >= 0.01).sum())
    else:
        result["reconciliation"] = pd.DataFrame()

    # ── Financial statements (simplified) ───────────────────
    num = df.select_dtypes(include=[np.number])
    if not num.empty:
        result["pl_statement"]  = num.sum().rename("Amount").to_frame()
        result["balance_sheet"] = num.mean().rename("Average").to_frame()
        result["cash_flow"]     = num.diff().sum().rename("Net_Change").to_frame()
    else:
        empty = pd.DataFrame(columns=["Note"])
        result["pl_statement"] = result["balance_sheet"] = result["cash_flow"] = empty

    return result


# ─────────────────────────────────────────────────────────────
# Cash Management
# ─────────────────────────────────────────────────────────────

def cash_position(df: pd.DataFrame, cash_col: str,
                  group_col: Optional[str] = None) -> Dict[str, Any]:
    """Compute cash positions and auto-categorize via KMeans."""
    result: Dict[str, Any] = {}
    cash = pd.to_numeric(df[cash_col], errors="coerce").fillna(0)

    if group_col and group_col in df.columns:
        result["positions"] = df.groupby(group_col)[cash_col].sum().to_dict()
    else:
        result["total_cash"] = float(cash.sum())

    # KMeans categorization
    num_df = df.select_dtypes(include=[np.number]).fillna(0)
    if len(num_df.columns) >= 1 and len(num_df) >= 3:
        from sklearn.cluster import KMeans
        k = min(3, len(num_df))
        labels = KMeans(n_clusters=k, random_state=42, n_init=5).fit_predict(num_df)
        df2 = df.copy()
        df2["_category"] = labels.astype(str)
        result["categorized"] = df2.groupby("_category")[cash_col].sum().to_dict()
    else:
        result["categorized"] = {}

    return result


def cash_forecast(
    current: float, inflow: float, outflow: float, months: int
) -> pd.DataFrame:
    """Simple linear cash flow forecast."""
    net = inflow - outflow
    balances = [current + net * m for m in range(1, months + 1)]
    return pd.DataFrame({
        "Month": list(range(1, months + 1)),
        "Projected_Balance": balances,
        "Net_Cash_Flow": [net] * months,
    })


# ─────────────────────────────────────────────────────────────
# Financial Report Generator
# ─────────────────────────────────────────────────────────────

def generate_report(
    df: pd.DataFrame,
    report_type: str,
    analysis_col: Optional[str],
    timeframe: str = "Monthly",
) -> Dict[str, Any]:
    """Compute all metrics for a financial report."""
    reports: Dict[str, Any] = {
        "meta": {
            "report_type": report_type,
            "timeframe": timeframe,
            "rows": len(df),
            "cols": len(df.columns),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    }

    num_cols = df.select_dtypes(include=[np.number]).columns
    if not analysis_col or analysis_col not in df.columns:
        analysis_col = num_cols[0] if len(num_cols) > 0 else None

    if analysis_col:
        s = pd.to_numeric(df[analysis_col], errors="coerce").dropna()
        reports["financial_summary"] = {
            "total":    float(s.sum()),
            "mean":     float(s.mean()),
            "median":   float(s.median()),
            "max":      float(s.max()),
            "min":      float(s.min()),
            "std":      float(s.std()),
            "q1":       float(s.quantile(0.25)),
            "q3":       float(s.quantile(0.75)),
            "skewness": float(s.skew()),
            "kurtosis": float(s.kurtosis()),
            "count":    int(len(s)),
        }

        # Time series
        dt_cols = df.select_dtypes(include=["datetime64"]).columns
        if len(dt_cols) > 0:
            dc = dt_cols[0]
            freq_map = {"Monthly": "ME", "Quarterly": "QE", "Annual": "YE"}
            freq = freq_map.get(timeframe, "ME")
            try:
                ts = df.set_index(dc)[analysis_col].resample(freq).sum().dropna()
                if len(ts) > 1:
                    pct = ts.pct_change().dropna()
                    reports["trend"] = {
                        "series":       ts.to_dict(),
                        "growth_rate":  float(pct.iloc[-1] * 100) if len(pct) else 0,
                        "avg_growth":   float(pct.mean() * 100),
                        "volatility":   float(pct.std() * 100),
                        "direction":    "Upward" if pct.mean() > 0 else "Downward",
                        "periods":      len(ts),
                        "last_value":   float(ts.iloc[-1]),
                    }
            except Exception as e:
                log.warning(f"Trend calc error: {e}")

        # Source breakdown
        if "_source" in df.columns:
            src = df.groupby("_source")[analysis_col].agg(
                Total="sum", Average="mean", Count="count"
            ).round(2)
            src["Share_%"] = (src["Total"] / src["Total"].sum() * 100).round(1)
            reports["source_breakdown"] = src.to_dict("index")

    return reports


def report_to_text(reports: Dict[str, Any]) -> str:
    """Serialise a report dict into a downloadable text format."""
    meta = reports.get("meta", {})
    fs = reports.get("financial_summary", {})
    trend = reports.get("trend", {})

    lines = [
        "=" * 60,
        f"  LIONSYLAI FINANCIAL REPORT",
        "=" * 60,
        f"Type       : {meta.get('report_type', 'N/A')}",
        f"Timeframe  : {meta.get('timeframe', 'N/A')}",
        f"Generated  : {meta.get('generated_at', 'N/A')}",
        f"Records    : {meta.get('rows', 0):,}",
        "",
        "── FINANCIAL SUMMARY ──────────────────────────────",
        f"Total      : ${fs.get('total', 0):,.2f}",
        f"Mean       : ${fs.get('mean', 0):,.2f}",
        f"Median     : ${fs.get('median', 0):,.2f}",
        f"Max        : ${fs.get('max', 0):,.2f}",
        f"Min        : ${fs.get('min', 0):,.2f}",
        f"Std Dev    : ${fs.get('std', 0):,.2f}",
        f"Skewness   : {fs.get('skewness', 0):.3f}",
        f"Kurtosis   : {fs.get('kurtosis', 0):.3f}",
    ]

    if trend:
        lines += [
            "",
            "── TREND ANALYSIS ─────────────────────────────────",
            f"Direction  : {trend.get('direction', 'N/A')}",
            f"Period Gr. : {trend.get('growth_rate', 0):.1f}%",
            f"Avg Growth : {trend.get('avg_growth', 0):.1f}%",
            f"Volatility : {trend.get('volatility', 0):.1f}%",
            f"Periods    : {trend.get('periods', 0)}",
            f"Last Value : ${trend.get('last_value', 0):,.2f}",
        ]

    src = reports.get("source_breakdown", {})
    if src:
        lines += ["", "── SOURCE BREAKDOWN ───────────────────────────────"]
        for s, m in src.items():
            lines.append(
                f"  {s:20} Total=${m.get('Total', 0):>12,.2f}  "
                f"Share={m.get('Share_%', 0):>5.1f}%"
            )

    lines += ["", "=" * 60, "Report generated by LionsylAI FP&A Automation", "=" * 60]
    return "\n".join(lines)
