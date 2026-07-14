"""
LionsylAI – Tab 7: Month-End Close
Automated reconciliation · Financial statements · Close checklist
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from components.data_engine import numeric_cols
from components.fp_engine import month_end_close
from design import section_header, insight_card, kpi_card


def render(df: pd.DataFrame):
    st.markdown(section_header(
        "📑 Automated Month-End Close",
        "Reconciliation · Financial statements · Close checklist"
    ), unsafe_allow_html=True)

    # CRITICAL: session_state may hold None even if key exists
    active_df = st.session_state.get("consolidated_df")
    if active_df is None:
        active_df = df

    t1, t2, t3 = st.tabs(["🔍 Reconciliation", "📊 Financial Statements", "✅ Close Checklist"])

    with t1: _reconciliation(active_df)
    with t2: _financial_statements(active_df)
    with t3: _checklist()


# ─────────────────────────────────────────────────────────────
# Reconciliation
# ─────────────────────────────────────────────────────────────

def _reconciliation(df: pd.DataFrame):
    st.markdown("### 🔍 Account Reconciliation")

    if df is None or df.empty:
        st.info("No data available. Upload a dataset or consolidate sources first.")
        return

    ncols = numeric_cols(df)

    if len(ncols) < 2:
        st.info("Need at least 2 numeric columns for reconciliation. Upload financial data first.")
        return

    c1, c2 = st.columns(2)
    with c1: c1_sel = st.selectbox("Ledger A (Book)",  ncols, key="me_c1")
    with c2: c2_sel = st.selectbox("Ledger B (Bank)",  ncols, index=1, key="me_c2")

    tolerance = st.number_input("Tolerance (absolute)", value=0.01,
                                step=0.01, format="%.2f", key="me_tol")

    if st.button("🔄 Run Reconciliation", type="primary", use_container_width=True):
        with st.spinner("Running account reconciliation…"):
            result = month_end_close(df, (c1_sel, c2_sel))

        if result and not result["reconciliation"].empty:
            recon = result["reconciliation"]
            matched   = int((recon["Difference"].abs() <= tolerance).sum())
            unmatched = int((recon["Difference"].abs() > tolerance).sum())
            total     = len(recon)
            match_pct = matched / total * 100 if total else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Lines",     f"{total:,}")
            c2.metric("Matched",         f"{matched:,}")
            c3.metric("Unmatched",       f"{unmatched:,}")
            c4.metric("Match Rate",      f"{match_pct:.1f}%")

            # Gauge
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=match_pct,
                title={"text": "Reconciliation Match %", "font": {"color":"#F0F2FF"}},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor":"#6B7280"},
                    "bar": {"color": "#10B981" if match_pct > 95 else "#F59E0B"},
                    "steps": [
                        {"range":[0,80],  "color":"rgba(239,68,68,0.13)"},
                        {"range":[80,95], "color":"rgba(245,158,11,0.13)"},
                        {"range":[95,100],"color":"rgba(16,185,129,0.13)"},
                    ],
                    "threshold": {"line":{"color":"#0AEFFF","width":3},"value":95},
                },
                number={"suffix":"%","font":{"color":"#F0F2FF"}},
            ))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#F0F2FF", height=260)
            st.plotly_chart(fig, use_container_width=True)

            # Show unmatched rows
            unmatched_df = recon[recon["Difference"].abs() > tolerance]
            if not unmatched_df.empty:
                st.markdown("#### ⚠️ Unmatched Items")
                st.dataframe(unmatched_df.head(50), use_container_width=True)
                st.download_button(
                    "📥 Export Unmatched Items",
                    unmatched_df.to_csv(index=False).encode(),
                    "unmatched_items.csv", "text/csv", use_container_width=True,
                )
            else:
                st.success("✅ All items reconciled within tolerance!")

            if match_pct >= 99:
                st.markdown(insight_card("🏆 **Perfect reconciliation** – books are clean.", "#10B981"), unsafe_allow_html=True)
            elif match_pct >= 95:
                st.markdown(insight_card(f"✅ **{match_pct:.1f}% matched** – review {unmatched} exceptions before close.", "#6C63FF"), unsafe_allow_html=True)
            else:
                st.markdown(insight_card(f"⚠️ **Only {match_pct:.1f}% matched** – do NOT close until differences are resolved.", "#EF4444"), unsafe_allow_html=True)

        else:
            st.error("Reconciliation failed. Ensure selected columns contain numeric data.")


# ─────────────────────────────────────────────────────────────
# Financial Statements
# ─────────────────────────────────────────────────────────────

def _financial_statements(df: pd.DataFrame):
    st.markdown("### 📊 Financial Statements")

    if df is None or df.empty:
        st.info("No data available. Upload a dataset or consolidate sources first.")
        return

    ncols = numeric_cols(df)

    if not ncols:
        st.info("No numeric data available.")
        return

    if st.button("📄 Generate Statements", type="primary", use_container_width=True):
        with st.spinner("Generating statements…"):
            result = month_end_close(df)

        st.success(f"✅ Statements generated — {result['close_date']}")

        t1, t2, t3 = st.tabs(["P&L Statement", "Balance Sheet", "Cash Flow"])

        with t1:
            st.markdown("**Profit & Loss Statement**")
            pl = result.get("pl_statement", pd.DataFrame())
            if not pl.empty:
                st.dataframe(pl.style.background_gradient(cmap="Greens", axis=0),
                             use_container_width=True)
                total_pl = pl.iloc[:,0].sum() if not pl.empty else 0
                col1, col2 = st.columns(2)
                col1.metric("Total Revenue (P&L)", f"${max(0,total_pl):,.0f}")
                col2.metric("Net Profit (P&L)",    f"${total_pl:,.0f}")

        with t2:
            st.markdown("**Balance Sheet**")
            bs = result.get("balance_sheet", pd.DataFrame())
            if not bs.empty:
                st.dataframe(bs, use_container_width=True)

        with t3:
            st.markdown("**Cash Flow Statement**")
            cf = result.get("cash_flow", pd.DataFrame())
            if not cf.empty:
                st.dataframe(cf, use_container_width=True)

    # Export all
    if st.button("📥 Export All Statements", use_container_width=True):
        result = month_end_close(df)
        content = (
            "LIONSYLAI – FINANCIAL STATEMENTS\n"
            "=" * 50 + "\n"
            f"Close Date: {result['close_date']}\n\n"
            "P&L STATEMENT\n" + result["pl_statement"].to_string() + "\n\n"
            "BALANCE SHEET\n" + result["balance_sheet"].to_string() + "\n\n"
            "CASH FLOW\n" + result["cash_flow"].to_string()
        )
        st.download_button("📥 Download", content,
                           "financial_statements.txt", "text/plain",
                           use_container_width=True)


# ─────────────────────────────────────────────────────────────
# Checklist
# ─────────────────────────────────────────────────────────────

def _checklist():
    st.markdown("### ✅ Month-End Close Checklist")

    DEFAULT_ITEMS = [
        "Review and validate all journal entries",
        "Reconcile all bank accounts",
        "Reconcile credit card statements",
        "Post all accruals and prepayments",
        "Calculate and post depreciation",
        "Review inventory valuations",
        "Verify accounts receivable ageing",
        "Verify accounts payable ageing",
        "Prepare Profit & Loss statement",
        "Prepare Balance Sheet",
        "Prepare Cash Flow statement",
        "Intercompany reconciliation",
        "Management review and sign-off",
        "Submit regulatory filings",
        "Archive all closing documents",
    ]

    # Initialize or repair corrupted session state
    if "me_checklist" not in st.session_state:
        st.session_state["me_checklist"] = {item: False for item in DEFAULT_ITEMS}
    chk = st.session_state["me_checklist"]
    if not isinstance(chk, dict) or not chk:
        st.session_state["me_checklist"] = {item: False for item in DEFAULT_ITEMS}
        chk = st.session_state["me_checklist"]

    completed = sum(chk.values())
    total     = len(chk)
    pct       = (completed / total * 100) if total else 0

    # Progress bar
    st.markdown(f"""
    <div style="margin-bottom:16px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
        <span style="color:#9CA3AF;font-size:13px;">Close Progress</span>
        <span style="color:#F0F2FF;font-weight:700;">{completed}/{total} ({pct:.0f}%)</span>
      </div>
      <div style="height:8px;background:#252836;border-radius:4px;">
        <div style="height:8px;width:{pct}%;background:{'#10B981' if pct==100 else '#6C63FF'};
                    border-radius:4px;transition:width 0.4s;"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Group items
    categories = {
        "📓 Journal & Entries":  list(chk.keys())[:3],
        "🏦 Banking & Recon":    list(chk.keys())[3:6],
        "📦 Assets & Inventory": list(chk.keys())[6:9],
        "📊 Statements":         list(chk.keys())[9:12],
        "✍️ Review & Archive":   list(chk.keys())[12:],
    }

    for cat, items in categories.items():
        st.markdown(f"**{cat}**")
        for item in items:
            col1, col2 = st.columns([4, 1])
            with col1:
                checked = st.checkbox(item, value=chk.get(item, False), key=f"chk_{item[:20]}")
                chk[item] = checked
            with col2:
                status = "✅ Done" if checked else "⏳ Pending"
                color  = "#10B981" if checked else "#6B7280"
                st.markdown(f"<small style='color:{color};'>{status}</small>",
                            unsafe_allow_html=True)
        st.markdown("")

    # Complete button
    if pct < 100:
        remain = total - completed
        st.warning(f"⚠️ {remain} item(s) remaining before close can be completed.")
    else:
        if st.button("🎉 Mark Month-End Close COMPLETE", type="primary",
                     use_container_width=True):
            st.success("✅ Month-end close completed successfully!")
            st.balloons()
            # Reset for next month
            st.session_state["me_checklist"] = {item: False for item in DEFAULT_ITEMS}
            st.rerun()

    # Quick reset
    if st.button("🔄 Reset Checklist", use_container_width=True):
        st.session_state["me_checklist"] = {item: False for item in DEFAULT_ITEMS}
        st.rerun()
