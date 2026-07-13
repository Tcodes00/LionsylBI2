"""
LionsylAI – Tab 8: Cash Management
Real-time positions · Forecasting · Working capital · Liquidity
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.data_engine import numeric_cols, categorical_cols
from components.fp_engine import cash_position, cash_forecast
from design import section_header, insight_card, kpi_card


def render(df: pd.DataFrame):
    st.markdown(section_header(
        "💵 Advanced Cash Management",
        "Real-time positions · Forecasting · Working capital optimisation"
    ), unsafe_allow_html=True)

    t1, t2, t3 = st.tabs([
        "💰 Cash Position", "🔮 Cash Forecast", "⚡ Working Capital"
    ])

    with t1: _cash_position(df)
    with t2: _cash_forecast_ui()
    with t3: _working_capital()


# ─────────────────────────────────────────────────────────────
# Cash Position
# ─────────────────────────────────────────────────────────────

def _cash_position(df: pd.DataFrame):
    st.markdown("### 💰 Current Cash Position")
    active_df = st.session_state.get("consolidated_df", df)
    ncols = numeric_cols(active_df)
    ccols = categorical_cols(active_df)

    if not ncols:
        st.info("No numeric columns available.")
        return

    c1, c2 = st.columns(2)
    with c1: cash_c  = st.selectbox("Cash / Balance column", ncols, key="cp_cash")
    with c2: group_c = st.selectbox("Group by (optional)", ["None"] + ccols, key="cp_grp")

    if st.button("📊 Analyse Cash Position", type="primary", use_container_width=True):
        grp = group_c if group_c != "None" else None
        result = cash_position(active_df, cash_c, grp)

        if result:
            if "positions" in result:
                pos = result["positions"]
                c1, c2 = st.columns(2)
                pos_df = pd.DataFrame({"Account": list(pos.keys()),
                                       "Balance": list(pos.values())})
                with c1:
                    fig = px.bar(pos_df, x="Account", y="Balance",
                                 color="Balance", color_continuous_scale="Viridis",
                                 title="Cash by Account")
                    fig.update_layout(**_cl(), height=320, xaxis_tickangle=-30)
                    st.plotly_chart(fig, use_container_width=True)
                with c2:
                    fig = px.pie(pos_df, names="Account", values="Balance",
                                 title="Cash Distribution", hole=0.4,
                                 color_discrete_sequence=["#6C63FF","#0AEFFF",
                                                           "#10B981","#F59E0B"])
                    fig.update_layout(**_cl(), height=320)
                    st.plotly_chart(fig, use_container_width=True)

                total = sum(pos.values())
                st.metric("Total Cash Position", f"${total:,.2f}")
            else:
                total = result.get("total_cash", 0)
                st.markdown(kpi_card("Total Cash", f"${total:,.2f}", icon="💰",
                            gradient="linear-gradient(135deg,#6C63FF,#0AEFFF)"),
                            unsafe_allow_html=True)

            # Categorised
            cat = result.get("categorized", {})
            if cat:
                st.markdown("#### 📊 Auto-Categorised Transactions")
                cat_df = pd.DataFrame({
                    "Category": [f"Cluster {k}" for k in cat.keys()],
                    "Total":     list(cat.values()),
                })
                fig = px.bar(cat_df, x="Category", y="Total",
                             color="Total", color_continuous_scale="Viridis",
                             title="Transactions by Auto-Category")
                fig.update_layout(**_cl(), height=300)
                st.plotly_chart(fig, use_container_width=True)

            # Cash insights
            cash_s = pd.to_numeric(active_df[cash_c], errors="coerce").dropna()
            avg_c  = float(cash_s.mean())
            std_c  = float(cash_s.std())
            cv     = std_c / avg_c * 100 if avg_c else 0

            st.markdown("#### 💡 Cash Insights")
            if cv > 50:
                st.markdown(insight_card(
                    f"⚠️ **High cash volatility** (CV={cv:.1f}%) – implement cash pooling strategies.",
                    "#F59E0B"), unsafe_allow_html=True)
            else:
                st.markdown(insight_card(
                    f"✅ **Stable cash flows** (CV={cv:.1f}%) – predictable liquidity position.",
                    "#10B981"), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Cash Forecast
# ─────────────────────────────────────────────────────────────

def _cash_forecast_ui():
    st.markdown("### 🔮 Cash Flow Forecasting")

    c1, c2 = st.columns(2)
    with c1:
        current  = st.number_input("Current Cash Balance ($)", value=500_000.0,
                                   step=10_000.0, format="%.0f", key="cf_curr")
        inflow   = st.number_input("Expected Monthly Inflow ($)", value=200_000.0,
                                   step=5_000.0, format="%.0f", key="cf_in")
    with c2:
        outflow  = st.number_input("Expected Monthly Outflow ($)", value=175_000.0,
                                   step=5_000.0, format="%.0f", key="cf_out")
        months   = st.slider("Forecast Period (months)", 1, 36, 12, key="cf_months")

    # Sensitivity
    with st.expander("⚙️ Sensitivity Analysis"):
        inflow_var  = st.slider("Inflow variability (%)", 0, 30, 10, key="cf_iv")
        outflow_var = st.slider("Outflow variability (%)", 0, 30, 10, key="cf_ov")

    if st.button("🔮 Generate Forecast", type="primary", use_container_width=True):
        fc_df = cash_forecast(current, inflow, outflow, months)

        # Base scenario
        base_final = fc_df["Projected_Balance"].iloc[-1]
        bear_fc    = cash_forecast(current, inflow*(1-inflow_var/100),
                                   outflow*(1+outflow_var/100), months)
        bull_fc    = cash_forecast(current, inflow*(1+inflow_var/100),
                                   outflow*(1-outflow_var/100), months)

        # ── Metrics ──────────────────────────────────────────
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Final Balance (Base)", f"${base_final:,.0f}")
        c2.metric("Min Balance",          f"${fc_df['Projected_Balance'].min():,.0f}")
        c3.metric("Net Monthly Flow",     f"${inflow-outflow:,.0f}")
        burn = int(current / (outflow - inflow)) if outflow > inflow else 99
        c4.metric("Runway (months)",      f"{min(burn,99)}+" if burn >= 99 else str(burn))

        # ── Chart ────────────────────────────────────────────
        m_idx = list(range(1, months+1))
        fig = go.Figure()

        # Confidence band (bear/bull)
        fig.add_trace(go.Scatter(
            x=m_idx + m_idx[::-1],
            y=list(bull_fc["Projected_Balance"]) + list(bear_fc["Projected_Balance"])[::-1],
            fill="toself", fillcolor="rgba(108,99,255,0.1)",
            line=dict(width=0), name="Sensitivity Range",
        ))
        fig.add_trace(go.Scatter(x=m_idx, y=bear_fc["Projected_Balance"],
                                 mode="lines", name="Bear Case",
                                 line=dict(color="#EF4444", dash="dash", width=1.5)))
        fig.add_trace(go.Scatter(x=m_idx, y=bull_fc["Projected_Balance"],
                                 mode="lines", name="Bull Case",
                                 line=dict(color="#10B981", dash="dash", width=1.5)))
        fig.add_trace(go.Scatter(x=m_idx, y=fc_df["Projected_Balance"],
                                 mode="lines+markers", name="Base Case",
                                 line=dict(color="#6C63FF", width=2.5),
                                 marker=dict(size=5)))
        fig.add_hline(y=0, line_dash="dash", line_color="#EF4444",
                      annotation_text="Zero Cash", annotation_font_color="#EF4444")

        min_cash_reserve = outflow * 3
        fig.add_hline(y=min_cash_reserve, line_dash="dot", line_color="#F59E0B",
                      annotation_text="3-Month Reserve",
                      annotation_font_color="#F59E0B")

        fig.update_layout(**_cl(), height=440, title="Cash Flow Forecast (with Sensitivity)",
                          xaxis_title="Month", yaxis_title="Balance ($)")
        st.plotly_chart(fig, use_container_width=True)

        # ── Insights ──────────────────────────────────────────
        if fc_df["Projected_Balance"].min() < 0:
            st.markdown(insight_card(
                "🚨 **Cash shortfall projected** – arrange credit facilities or reduce outflows immediately.",
                "#EF4444"), unsafe_allow_html=True)
        elif fc_df["Projected_Balance"].min() < outflow * 3:
            st.markdown(insight_card(
                "⚠️ **Low reserve** – balance may drop below 3-month safety buffer. Monitor closely.",
                "#F59E0B"), unsafe_allow_html=True)
        else:
            st.markdown(insight_card(
                "✅ **Healthy cash position** – adequate reserves maintained throughout forecast period.",
                "#10B981"), unsafe_allow_html=True)

        # Download
        st.download_button(
            "📥 Download Forecast",
            fc_df.to_csv(index=False).encode(),
            "cash_forecast.csv", "text/csv",
            use_container_width=True,
        )


# ─────────────────────────────────────────────────────────────
# Working Capital
# ─────────────────────────────────────────────────────────────

def _working_capital():
    st.markdown("### ⚡ Working Capital Optimisation")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 📥 Accounts Receivable")
        ar_days = st.number_input("Current AR Days", value=45.0, step=1.0, key="wc_ar")
        target_ar = st.number_input("Target AR Days", value=30.0, step=1.0, key="wc_ar_t")
        annual_rev = st.number_input("Annual Revenue ($)", value=5_000_000.0,
                                     step=100_000.0, format="%.0f", key="wc_rev")

        daily_rev   = annual_rev / 365
        current_ar  = ar_days * daily_rev
        target_ar_b = target_ar * daily_rev
        ar_release  = current_ar - target_ar_b

        st.metric("Current AR Balance",  f"${current_ar:,.0f}")
        st.metric("Target AR Balance",   f"${target_ar_b:,.0f}")
        st.metric("Potential Cash Release", f"${ar_release:,.0f}",
                  delta_color="normal" if ar_release > 0 else "inverse")

    with c2:
        st.markdown("#### 📤 Accounts Payable")
        ap_days    = st.number_input("Current AP Days", value=30.0, step=1.0, key="wc_ap")
        target_ap  = st.number_input("Target AP Days", value=45.0, step=1.0, key="wc_ap_t")
        annual_cogs = st.number_input("Annual COGS ($)", value=3_000_000.0,
                                      step=100_000.0, format="%.0f", key="wc_cogs")

        daily_cogs  = annual_cogs / 365
        current_ap  = ap_days * daily_cogs
        target_ap_b = target_ap * daily_cogs
        ap_benefit  = target_ap_b - current_ap

        st.metric("Current AP Balance",  f"${current_ap:,.0f}")
        st.metric("Target AP Balance",   f"${target_ap_b:,.0f}")
        st.metric("Potential Benefit",   f"${ap_benefit:,.0f}",
                  delta_color="normal" if ap_benefit > 0 else "inverse")

    # Cash Conversion Cycle
    st.markdown("---")
    st.markdown("#### 🔄 Cash Conversion Cycle (CCC)")
    dso  = ar_days    # Days Sales Outstanding
    dpo  = ap_days    # Days Payable Outstanding
    dio  = st.number_input("Days Inventory Outstanding (DIO)", value=20.0,
                           step=1.0, key="wc_dio")
    ccc  = dso + dio - dpo
    t_ccc= target_ar + dio - target_ap

    c1, c2, c3 = st.columns(3)
    c1.metric("Current CCC",    f"{ccc:.1f} days")
    c2.metric("Target CCC",     f"{t_ccc:.1f} days")
    c3.metric("CCC Improvement",f"{ccc-t_ccc:.1f} days",
              delta_color="normal" if ccc > t_ccc else "inverse")

    # CCC waterfall
    fig = go.Figure(go.Waterfall(
        x=["DSO", "DIO", "DPO", "CCC"],
        y=[dso, dio, -dpo, ccc],
        measure=["relative","relative","relative","total"],
        connector=dict(line=dict(color="#252836")),
        decreasing=dict(marker_color="#10B981"),
        increasing=dict(marker_color="#EF4444"),
        totals=dict(marker_color="#6C63FF"),
        text=[f"{dso:.0f}d", f"{dio:.0f}d", f"-{dpo:.0f}d", f"{ccc:.0f}d"],
        textposition="outside",
    ))
    fig.update_layout(**_cl(), height=340, title="Cash Conversion Cycle Waterfall")
    st.plotly_chart(fig, use_container_width=True)

    # Recommendations
    st.markdown("#### 💡 Working Capital Recommendations")
    recs = [
        ("💰 **Accelerate collections** – implement early payment discounts (2/10 net 30).", "#6C63FF"),
        ("📦 **Inventory optimisation** – adopt JIT replenishment to reduce DIO.", "#0AEFFF"),
        ("🤝 **Supplier terms** – negotiate extended payment terms with key vendors.", "#10B981"),
        ("📊 **AR automation** – deploy e-invoicing and automated payment reminders.", "#6C63FF"),
        ("🏦 **Supply chain finance** – offer dynamic discounting programmes.", "#0AEFFF"),
    ]
    if ccc > 60:
        recs.insert(0, ("🚨 **High CCC** – prioritise DSO reduction and AP extension urgently.", "#EF4444"))
    for r, col in recs:
        st.markdown(insight_card(r, col), unsafe_allow_html=True)


def _cl():
    return dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F0F2FF", family="Inter"),
        xaxis=dict(showgrid=True, gridcolor="#252836", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#252836", zeroline=False),
        margin=dict(t=40, b=30, l=10, r=10),
        coloraxis_colorbar=dict(tickfont=dict(color="#F0F2FF")),
    )
