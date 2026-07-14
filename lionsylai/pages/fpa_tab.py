"""
LionsylAI – Tab 6: FP&A Automation
Data consolidation · Financial reporting · Budget analysis · Report library
"""
from __future__ import annotations
import json
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.fp_engine import (
    DataConsolidator, budget_from_dataframe, budget_variance_df,
    DEFAULT_BUDGET, generate_report, report_to_text,
)
from design import section_header, kpi_card, insight_card, badge


def render(df: pd.DataFrame):
    st.markdown(section_header(
        "🏦 FP&A Automation",
        "Consolidate · Report · Budget · Archive"
    ), unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs([
        "🔗 Data Consolidation",
        "📈 Financial Reporting",
        "💰 Budget Analysis",
        "📋 Report Library",
    ])

    with t1: _consolidation()
    with t2: _financial_reporting(df)
    with t3: _budget_analysis(df)
    with t4: _report_library()


# ─────────────────────────────────────────────────────────────
# Data Consolidation
# ─────────────────────────────────────────────────────────────

def _consolidation():
    st.markdown("### 🔗 Multi-Source Data Consolidation")
    st.markdown("""
    <div style="background:#141720;border:1px solid #6C63FF44;border-radius:14px;
                padding:16px 20px;margin-bottom:20px;font-size:14px;color:#9CA3AF;">
      Upload data from multiple systems – ERP, CRM, HR, Finance – and consolidate
      into a single source of truth with one click.
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        erp  = st.file_uploader("🏢 ERP Data",    type=["csv","xlsx","pdf"], key="fpa_erp")
        crm  = st.file_uploader("👥 CRM Data",    type=["csv","xlsx"],      key="fpa_crm")
    with c2:
        hr   = st.file_uploader("👤 HR Data",     type=["csv","xlsx"],      key="fpa_hr")
        fin  = st.file_uploader("💰 Finance Data", type=["csv","xlsx","pdf"],key="fpa_fin")

    files = {"ERP": erp, "CRM": crm, "HR": hr, "Finance": fin}
    any_f = any(v is not None for v in files.values())

    if st.button("🔄 Consolidate Data", type="primary",
                 use_container_width=True, disabled=not any_f):
        consolidator = DataConsolidator()
        added = 0
        with st.spinner("Consolidating sources…"):
            for label, f in files.items():
                if f and consolidator.add_file(label, f):
                    added += 1

        if added and consolidator.consolidated is not None:
            st.session_state["consolidated_df"] = consolidator.consolidated
            st.success(f"✅ Consolidated {added} source(s) → {len(consolidator.consolidated):,} records")

            # Quality report
            qr = consolidator.quality_report()
            st.markdown("#### 🎯 Data Quality Report")
            st.dataframe(qr, use_container_width=True, hide_index=True)

            # Source chart
            if "_source" in consolidator.consolidated.columns:
                src_cnt = consolidator.consolidated["_source"].value_counts()
                c1, c2 = st.columns(2)
                with c1:
                    fig = px.pie(values=src_cnt.values, names=src_cnt.index,
                                 title="Records by Source",
                                 color_discrete_sequence=["#6C63FF","#0AEFFF",
                                                           "#10B981","#F59E0B"])
                    fig.update_layout(**_cl(), height=300)
                    st.plotly_chart(fig, use_container_width=True)
                with c2:
                    fig = px.bar(x=src_cnt.index, y=src_cnt.values,
                                 title="Source Record Count",
                                 color=src_cnt.values, color_continuous_scale="Viridis")
                    fig.update_layout(**_cl(), height=300)
                    st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### 🔍 Data Preview")
            st.dataframe(consolidator.consolidated.head(20), use_container_width=True)
        else:
            st.error("No data could be loaded. Check file formats.")
    elif not any_f:
        st.info("📁 Upload at least one file to begin consolidation.")


# ─────────────────────────────────────────────────────────────
# Financial Reporting
# ─────────────────────────────────────────────────────────────

def _financial_reporting(df: pd.DataFrame):
    st.markdown("### 📈 Automated Financial Reporting")

    active_df = st.session_state.get("consolidated_df", df)
    if active_df is None:
        st.warning("No data available. Upload a dataset or consolidate first.")
        return

    ncols = active_df.select_dtypes(include=[np.number]).columns.tolist()

    c1, c2 = st.columns(2)
    with c1:
        report_type = st.selectbox("Report Type", [
            "Financial Summary", "Profit & Loss",
            "Balance Sheet", "Cash Flow", "KPI Dashboard", "Executive Summary"
        ], key="fpa_rtype")
        timeframe = st.selectbox("Timeframe", ["Monthly","Quarterly","Annual"], key="fpa_tf")
    with c2:
        analysis_col = st.selectbox("Primary analysis column",
                                    ncols if ncols else ["N/A"], key="fpa_acol")
        include_charts = st.checkbox("Include visualisations", value=True)
        export_pdf    = st.checkbox("Generate downloadable report", value=True)

    if st.button("📊 Generate Report", type="primary", use_container_width=True):
        with st.spinner("Generating comprehensive financial report…"):
            reports = generate_report(active_df, report_type,
                                      analysis_col if ncols else None, timeframe)

        if reports:
            st.success("✅ Report generated!")
            st.session_state["last_report"] = reports
            _display_report(reports, active_df, analysis_col, include_charts)

            if export_pdf:
                txt = report_to_text(reports)
                fname = (f"lionsylai_{report_type.replace(' ','_').lower()}_"
                         f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                st.download_button("📥 Download Report", txt, fname, "text/plain",
                                   use_container_width=True)
        else:
            st.error("Report generation failed.")


def _display_report(reports, df, acol, charts):
    meta = reports.get("meta", {})
    fs   = reports.get("financial_summary", {})
    tr   = reports.get("trend", {})

    # Meta row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records",     f"{meta.get('rows',0):,}")
    c2.metric("Columns",     meta.get("cols", 0))
    c3.metric("Timeframe",   meta.get("timeframe","N/A"))
    c4.metric("Generated",   meta.get("generated_at","N/A")[:10] if meta.get("generated_at") else "N/A")

    if fs:
        st.markdown("#### 💰 Financial Summary")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total",   f"${fs.get('total',0):,.0f}")
        c2.metric("Average", f"${fs.get('mean',0):,.0f}")
        c3.metric("Max",     f"${fs.get('max',0):,.0f}")
        c4.metric("Std Dev", f"${fs.get('std',0):,.0f}")

        # Distribution stats
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Median",   f"${fs.get('median',0):,.0f}")
        c2.metric("Q1",       f"${fs.get('q1',0):,.0f}")
        c3.metric("Q3",       f"${fs.get('q3',0):,.0f}")
        c4.metric("Kurtosis", f"{fs.get('kurtosis',0):.2f}")

    if tr and "error" not in tr:
        st.markdown("#### 📈 Trend Analysis")
        c1,c2,c3,c4 = st.columns(4)
        dir_icon = "🔼" if tr.get("direction")=="Upward" else "🔽"
        c1.metric("Direction",      f"{dir_icon} {tr.get('direction','N/A')}")
        c2.metric("Period Growth",  f"{tr.get('growth_rate',0):.1f}%")
        c3.metric("Avg Growth",     f"{tr.get('avg_growth',0):.1f}%")
        c4.metric("Volatility",     f"{tr.get('volatility',0):.1f}%")

        if charts and tr.get("series"):
            s = pd.Series(tr["series"])
            fig = px.line(s, title="Financial Trend Over Time",
                          color_discrete_sequence=["#6C63FF"])
            fig.update_layout(**_cl(), height=360, xaxis_title="Period", yaxis_title=acol)
            st.plotly_chart(fig, use_container_width=True)

    # Source breakdown
    src = reports.get("source_breakdown", {})
    if src:
        st.markdown("#### 🔗 Source Performance")
        src_df = pd.DataFrame(src).T.reset_index().rename(columns={"index":"Source"})
        st.dataframe(src_df, use_container_width=True, hide_index=True)

    if charts and acol and acol in df.columns:
        st.markdown("#### 📊 Distribution Analysis")
        c1, c2 = st.columns(2)
        with c1:
            fig = px.histogram(df, x=acol, nbins=40,
                               color_discrete_sequence=["#6C63FF"], opacity=0.85)
            fig.update_layout(**_cl(), height=320, title=f"Distribution of {acol}")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.box(df, y=acol, color_discrete_sequence=["#0AEFFF"])
            fig.update_layout(**_cl(), height=320, title=f"Box Plot – {acol}")
            st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# Budget Analysis
# ─────────────────────────────────────────────────────────────

def _budget_analysis(df: pd.DataFrame):
    st.markdown("### 💰 Budget vs Actual Analysis")

    # Init budget
    if "budget_data" not in st.session_state:
        st.session_state["budget_data"] = (
            budget_from_dataframe(df) if df is not None else DEFAULT_BUDGET.copy()
        )
    bd = st.session_state["budget_data"]

    # ── DEFENSIVE NORMALIZATION ─────────────────────────────
    # budget_from_dataframe or JSON-loaded budgets may return strings,
    # None, or nested objects. Coerce every numeric field to Python float.
    def _safe_float(val, default=0.0):
        try:
            return float(val) if val is not None else default
        except (TypeError, ValueError):
            return default

    bd["total_budget"] = _safe_float(bd.get("total_budget"), 1_000_000.0)
    bd["fiscal_year"]  = int(_safe_float(bd.get("fiscal_year"), 2026))
    bd["currency"]     = str(bd.get("currency", "USD"))

    for dept, data in bd.get("departments", {}).items():
        data["allocation"] = _safe_float(data.get("allocation"), 0.0)
        data["budget"]     = _safe_float(data.get("budget"), 0.0)
        data["actual"]     = _safe_float(data.get("actual"), 0.0)

    # ── Config panel ─────────────────────────────────────────
    c1, c2 = st.columns([2, 1])
    with c2:
        st.markdown("#### ⚙️ Global Settings")
        new_total = st.number_input("Total Budget ($)", value=bd["total_budget"],
                                    step=50_000.0, format="%.0f", key="bd_total")
        fy = st.selectbox("Fiscal Year", [2024,2025,2026,2027],
                          index=[2024,2025,2026,2027].index(bd.get("fiscal_year",2026)),
                          key="bd_fy")
        curr = st.selectbox("Currency", ["USD","EUR","GBP","JPY","BDT"],
                            index=["USD","EUR","GBP","JPY","BDT"].index(bd.get("currency","USD")),
                            key="bd_curr")

        if new_total != bd["total_budget"]:
            for dept in bd["departments"]:
                alloc = bd["departments"][dept]["allocation"]
                bd["departments"][dept]["budget"] = new_total * alloc
            bd["total_budget"] = new_total
            bd["fiscal_year"]  = fy
            bd["currency"]     = curr

        bcol1, bcol2 = st.columns(2)
        with bcol1:
            if st.button("⚖️ Equalise", use_container_width=True):
                n = len(bd["departments"])
                for d in bd["departments"]:
                    bd["departments"][d]["allocation"] = 1/n
                    bd["departments"][d]["budget"]     = new_total/n
                st.rerun()
        with bcol2:
            if st.button("🔄 Reset", use_container_width=True):
                st.session_state["budget_data"] = DEFAULT_BUDGET.copy()
                st.rerun()

        if st.button("💾 Save Budget", type="primary", use_container_width=True):
            # Persist to DB if user logged in
            if st.session_state.get("authenticated") and st.session_state.get("user_id"):
                try:
                    from database import BudgetRepo
                    BudgetRepo.save(
                        st.session_state["user_id"], "Budget Plan",
                        bd["fiscal_year"], bd["currency"], json.dumps(bd)
                    )
                except Exception:
                    pass
            st.success("Budget saved!")

    with c1:
        st.markdown("#### 🏢 Department Allocations")
        total_alloc = 0.0
        for dept, data in bd["departments"].items():
            with st.expander(f"📊 {dept}", expanded=False):
                ca, cb = st.columns(2)
                with ca:
                    new_alloc = st.slider(
                        "Allocation %", 0.0, 100.0,
                        float(data["allocation"] * 100), 0.5,
                        key=f"alloc_{dept}"
                    )
                    data["allocation"] = new_alloc / 100
                    data["budget"]     = new_total * new_alloc / 100
                    st.metric("Budget", f"${data['budget']:,.0f}")
                with cb:
                    new_actual = st.number_input(
                        "Actual Spend", value=float(data["actual"]),
                        step=1000.0, format="%.0f", key=f"actual_{dept}"
                    )
                    data["actual"] = new_actual
                    var_pct = ((new_actual - data["budget"]) / data["budget"] * 100
                               if data["budget"] else 0)
                    if var_pct > 5:
                        st.error(f"Over: {var_pct:.1f}%")
                    elif var_pct < -5:
                        st.success(f"Under: {abs(var_pct):.1f}%")
                    else:
                        st.info(f"On target: {var_pct:.1f}%")
            total_alloc += data["allocation"]

        # Allocation check
        if abs(total_alloc - 1.0) > 0.05:
            st.warning(f"⚠️ Total allocation = {total_alloc*100:.1f}% (should be ~100%)")
        else:
            st.success(f"✅ Total allocation: {total_alloc*100:.1f}%")

    # ── Variance charts ───────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📊 Budget Performance Dashboard")
    var_df = budget_variance_df(bd)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Budget", f"${var_df['Budgeted ($)'].sum():,.0f}")
    c2.metric("Total Actual", f"${var_df['Actual ($)'].sum():,.0f}")
    total_var = var_df['Variance ($)'].sum()
    c3.metric("Total Variance", f"${total_var:,.0f}",
              delta_color="inverse" if total_var > 0 else "normal")
    avg_var_pct = var_df["Variance %"].mean()
    c4.metric("Avg Variance %", f"{avg_var_pct:.1f}%")

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Budgeted", x=var_df["Department"],
                             y=var_df["Budgeted ($)"], marker_color="#6C63FF"))
        fig.add_trace(go.Bar(name="Actual",   x=var_df["Department"],
                             y=var_df["Actual ($)"], marker_color="#0AEFFF"))
        fig.update_layout(**_cl(), barmode="group", height=360,
                          title="Budget vs Actual by Department",
                          xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        colors = ["#EF4444" if v > 0 else "#10B981" for v in var_df["Variance %"]]
        fig = go.Figure(go.Bar(x=var_df["Department"], y=var_df["Variance %"],
                               marker_color=colors))
        fig.add_hline(y=0, line_dash="dash", line_color="#6B7280")
        fig.update_layout(**_cl(), height=360,
                          title="Variance % by Department",
                          yaxis_title="Variance %", xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(var_df, use_container_width=True, hide_index=True)

    # Insights
    st.markdown("#### 💡 Budget Insights")
    over  = var_df[var_df["Variance %"] > 5]["Department"].tolist()
    under = var_df[var_df["Variance %"] < -5]["Department"].tolist()
    if over:
        st.markdown(insight_card(
            f"⚠️ **Over budget departments:** {', '.join(over)} – review spend controls.",
            "#EF4444"), unsafe_allow_html=True)
    if under:
        st.markdown(insight_card(
            f"✅ **Under budget:** {', '.join(under)} – consider reallocating surplus.",
            "#10B981"), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Report Library
# ─────────────────────────────────────────────────────────────

def _report_library():
    st.markdown("### 📋 Report Library")

    # Seed sample reports
    if "report_library" not in st.session_state:
        st.session_state["report_library"] = [
            {"id":1,"name":"Monthly Financial Summary","type":"Financial",
             "date":"2026-05-01","status":"Approved","size":"1.2 MB",
             "description":"Comprehensive monthly financial performance."},
            {"id":2,"name":"Q1 Strategic Analysis","type":"Strategic",
             "date":"2026-04-01","status":"Pending Review","size":"2.8 MB",
             "description":"Quarterly strategic business review."},
            {"id":3,"name":"Annual Budget Plan","type":"Budget",
             "date":"2026-01-10","status":"Approved","size":"1.8 MB",
             "description":"Annual budget across all departments."},
        ]

    # Also add any dynamically generated
    last = st.session_state.get("last_report")
    if last:
        exists = any(r["name"] == "Latest Generated Report"
                     for r in st.session_state["report_library"])
        if not exists:
            st.session_state["report_library"].append({
                "id": 99, "name": "Latest Generated Report", "type": "Dynamic",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "status": "Generated", "size": "N/A",
                "description": "Most recently generated report.",
                "_data": last,
            })

    # Filters
    c1, c2 = st.columns([3, 1])
    with c2:
        filt_type = st.selectbox("Filter by type",
                                 ["All","Financial","Strategic","Budget","Dynamic"],
                                 key="rl_filt")

    lib = [r for r in st.session_state["report_library"]
           if filt_type == "All" or r["type"] == filt_type]

    for rpt in lib:
        status_color = {"Approved":"#10B981","Pending Review":"#F59E0B",
                        "Generated":"#6C63FF","Rejected":"#EF4444"}.get(rpt["status"],"#6B7280")
        with st.expander(f"📄 {rpt['name']} — {rpt['date']}", expanded=False):
            ca, cb, cc = st.columns([3,1,1])
            with ca:
                st.markdown(f"**Type:** {rpt['type']}  \n**Description:** {rpt['description']}")
            with cb:
                st.markdown(f"<span style='color:{status_color};font-weight:700;'>"
                            f"● {rpt['status']}</span>",
                            unsafe_allow_html=True)
                st.caption(f"Size: {rpt['size']}")
            with cc:
                if st.button("👁 View", key=f"rl_view_{rpt['id']}", use_container_width=True):
                    st.session_state["viewing_report"] = rpt
                if "_data" in rpt:
                    txt = report_to_text(rpt["_data"])
                    st.download_button("📥 Export", txt,
                                       f"report_{rpt['id']}.txt", "text/plain",
                                       key=f"rl_dl_{rpt['id']}", use_container_width=True)

    # View modal
    viewing = st.session_state.get("viewing_report")
    if viewing:
        st.markdown("---")
        st.markdown(f"#### 👁 Viewing: {viewing['name']}")
        if "_data" in viewing:
            _display_report(viewing["_data"], pd.DataFrame(), "", False)
        else:
            st.info("Full report data not available for this sample entry.")
        if st.button("✕ Close Preview"):
            st.session_state.pop("viewing_report", None)
            st.rerun()


def _cl():
    return dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F0F2FF", family="Inter"),
        xaxis=dict(showgrid=True, gridcolor="#252836", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#252836", zeroline=False),
        margin=dict(t=40, b=30, l=10, r=10),
        coloraxis_colorbar=dict(tickfont=dict(color="#F0F2FF")),
    )
