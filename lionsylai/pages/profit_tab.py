"""
LionsylAI – Tab 2: Profit Analytics
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.data_engine import detect_columns, numeric_cols, categorical_cols, calc_growth
from design import section_header, kpi_card, insight_card


def render(df: pd.DataFrame):
    st.markdown(section_header(
        "💰 Advanced Profit Analytics",
        "Deep-dive profitability, margin analysis, and cost breakdown"
    ), unsafe_allow_html=True)

    det   = detect_columns(df)
    ncols = numeric_cols(df)
    ccols = categorical_cols(df)

    rev_col  = det["revenue"][0]  if det["revenue"]  else (ncols[0] if ncols else None)
    cost_col = det["cost"][0]     if det["cost"]      else (ncols[1] if len(ncols) > 1 else None)
    prof_col = det["profit"][0]   if det["profit"]    else None

    if not rev_col and not ncols:
        st.info("No numeric columns detected. Please upload financial data.")
        return

    # ── Compute key metrics ───────────────────────────────────
    def _to_num(col):
        return pd.to_numeric(df[col], errors="coerce").dropna() if col else pd.Series(dtype=float)

    rev_s  = _to_num(rev_col)
    cost_s = _to_num(cost_col)
    prof_s = _to_num(prof_col) if prof_col else (rev_s - cost_s if rev_col and cost_col else pd.Series(dtype=float))

    total_rev    = rev_s.sum()   if len(rev_s)  else 0
    total_cost   = cost_s.sum()  if len(cost_s) else 0
    total_profit = prof_s.sum()  if len(prof_s) else 0
    margin_pct   = (total_profit / total_rev * 100) if total_rev else 0
    cost_ratio   = (total_cost / total_rev * 100)   if total_rev else 0
    avg_rev      = rev_s.mean()  if len(rev_s)  else 0
    rev_growth   = calc_growth(rev_s)

    # ── Purple gradient KPI cards ─────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "Total Revenue",  f"${total_rev:,.0f}",    f"{rev_growth:+.1f}% growth", "💰"),
        (c2, "Total Cost",     f"${total_cost:,.0f}",   f"{cost_ratio:.1f}% of rev",  "📤"),
        (c3, "Net Profit",     f"${total_profit:,.0f}", f"{margin_pct:.1f}% margin",  "📈"),
        (c4, "Avg Transaction",f"${avg_rev:,.0f}",      f"{len(rev_s):,} records",    "🧮"),
    ]
    for col, label, val, delta, icon in cards:
        with col:
            st.markdown(kpi_card(label, val, delta, icon,
                        "linear-gradient(135deg,#6C63FF,#764ba2)"),
                        unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Charts row 1 ─────────────────────────────────────────
    if rev_col and cost_col:
        c1, c2 = st.columns(2)
        with c1:
            # Defensive: isolate only the two columns Plotly needs
            # Narwhals (used by trendline="ols") rejects duplicate column names
            plot_df = df[[rev_col, cost_col]].copy()
            fig = px.scatter(
                plot_df,
                x=rev_col,
                y=cost_col,
                title="Revenue vs Cost",
                trendline="ols",
                color_discrete_sequence=["#6C63FF"],
                opacity=0.65
            )
            fig.update_layout(**_cl(), height=360)
            st.plotly_chart(fig, use_container_width=True)

    # ── Category performance ──────────────────────────────────
    if ccols and rev_col:
        st.markdown("---")
        st.markdown("#### 📊 Revenue by Category")
        cat_c = st.selectbox("Group by category", ccols, key="profit_cat")
        try:
            rev_num = pd.to_numeric(df[rev_col], errors="coerce")
            cat_perf = (
                df[rev_num.notna()]
                .groupby(cat_c)[rev_col]
                .sum()
                .sort_values(ascending=False)
            )
            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(
                    x=cat_perf.index[:15], y=cat_perf.values[:15],
                    title=f"Top {min(15, len(cat_perf))} by Revenue",
                    color=cat_perf.values[:15],
                    color_continuous_scale="Viridis",
                )
                fig.update_layout(**_cl(), height=380, xaxis_tickangle=-35)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig = px.pie(
                    values=cat_perf.values[:10],
                    names=cat_perf.index[:10],
                    title="Revenue Share",
                    color_discrete_sequence=px.colors.qualitative.Vivid,
                    hole=0.45,
                )
                fig.update_traces(textposition="inside", textinfo="percent+label")
                fig.update_layout(**_cl(), height=380)
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Category analysis error: {e}")

    # ── Margin waterfall ──────────────────────────────────────
    if total_rev and total_cost:
        st.markdown("---")
        st.markdown("#### 🌊 Profit Waterfall")
        wf_x = ["Revenue", "Cost", "Net Profit"]
        wf_y = [total_rev, -total_cost, total_profit]
        wf_c = ["#6C63FF", "#FF6B6B", "#10B981" if total_profit >= 0 else "#EF4444"]
        fig = go.Figure(go.Waterfall(
            x=wf_x, y=wf_y,
            connector=dict(line=dict(color="#252836")),
            decreasing=dict(marker=dict(color="#FF6B6B")),
            increasing=dict(marker=dict(color="#10B981")),
            totals=dict(marker=dict(color="#6C63FF")),
            text=[f"${abs(v):,.0f}" for v in wf_y],
            textposition="outside",
        ))
        fig.update_layout(**_cl(), height=380, title="Profit Waterfall Analysis")
        st.plotly_chart(fig, use_container_width=True)

    # ── Insights ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 💡 Automated Insights")

    insights = _generate_profit_insights(margin_pct, cost_ratio, rev_growth, total_rev)
    for ins, color in insights:
        st.markdown(insight_card(ins, color), unsafe_allow_html=True)


def _generate_profit_insights(margin, cost_ratio, growth, total_rev):
    out = []
    if margin > 25:
        out.append(("🏆 **Exceptional margin** – you're in top-quartile profitability. Consider aggressive reinvestment.", "#10B981"))
    elif margin > 15:
        out.append(("✅ **Healthy margins** – maintain strategies while seeking efficiency gains.", "#6C63FF"))
    elif margin > 5:
        out.append(("⚡ **Moderate margin** – focus on cost optimisation and value-based pricing.", "#F59E0B"))
    else:
        out.append(("⚠️ **Low/negative margin** – urgent review of cost structure recommended.", "#EF4444"))

    if growth > 10:
        out.append((f"🚀 **Strong revenue growth** of {growth:.1f}% – scale marketing and operations.", "#0AEFFF"))
    elif growth > 0:
        out.append((f"📈 **Positive growth** of {growth:.1f}% – stable trajectory.", "#6C63FF"))
    else:
        out.append((f"📉 **Revenue decline** of {abs(growth):.1f}% – investigate root cause.", "#EF4444"))

    if cost_ratio > 85:
        out.append(("💸 **High cost ratio** – implement lean processes and renegotiate supplier terms.", "#FF6B6B"))
    elif cost_ratio < 60:
        out.append(("💪 **Efficient cost structure** – strong operational leverage.", "#10B981"))

    out.append(("🤖 **AI Recommendation** – use the AI Studio tab to forecast revenue and identify key drivers.", "#6C63FF"))
    return out


def _cl():
    return dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F0F2FF", family="Inter"),
        xaxis=dict(showgrid=True, gridcolor="#252836", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#252836", zeroline=False),
        margin=dict(t=40, b=30, l=10, r=10),
        coloraxis_colorbar=dict(tickfont=dict(color="#F0F2FF")),
    )
