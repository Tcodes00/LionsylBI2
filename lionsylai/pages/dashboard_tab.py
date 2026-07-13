"""
LionsylAI – Tab 1: Business Intelligence Dashboard
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.data_engine import (
    detect_columns, numeric_cols, categorical_cols, date_cols, calc_growth,
)
from design import section_header, kpi_card, insight_card
from utils.prefs import chart_colors, chart_scale, currency_symbol


def render(df: pd.DataFrame):
    st.markdown(section_header(
        "📊 Business Intelligence Dashboard",
        "Real-time overview of your data across all dimensions"
    ), unsafe_allow_html=True)

    # ── KPI Row ───────────────────────────────────────────────
    det  = detect_columns(df)
    ncols = numeric_cols(df)
    ccols = categorical_cols(df)
    dcols = date_cols(df)

    rev_col  = det["revenue"][0]  if det["revenue"]  else (ncols[0] if ncols else None)
    cost_col = det["cost"][0]     if det["cost"]      else (ncols[1] if len(ncols) > 1 else None)
    prof_col = det["profit"][0]   if det["profit"]    else None

    # Compute headline numbers
    total_rev   = float(df[rev_col].sum())  if rev_col  else 0
    total_cost  = float(df[cost_col].sum()) if cost_col else 0
    total_profit = (
        float(df[prof_col].sum()) if prof_col
        else (total_rev - total_cost if rev_col and cost_col else 0)
    )
    margin_pct = (total_profit / total_rev * 100) if total_rev else 0
    rev_growth = calc_growth(df[rev_col]) if rev_col else 0.0

    c1, c2, c3, c4 = st.columns(4)
    cur = currency_symbol()
    with c1:
        st.markdown(kpi_card(
            "Total Revenue", f"{cur}{total_rev:,.0f}",
            delta=f"{rev_growth:+.1f}%", icon="💰",
            gradient="linear-gradient(135deg,#6C63FF,#0AEFFF)"
        ), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card(
            "Total Cost", f"{cur}{total_cost:,.0f}",
            icon="📤", gradient="linear-gradient(135deg,#FF6B6B,#F59E0B)"
        ), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card(
            "Net Profit", f"{cur}{total_profit:,.0f}",
            delta=f"{margin_pct:.1f}% margin", icon="📈",
            gradient="linear-gradient(135deg,#10B981,#0AEFFF)"
        ), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card(
            "Data Records", f"{len(df):,}",
            delta=f"{len(df.columns)} columns", icon="🗄️",
            gradient="linear-gradient(135deg,#8B84FF,#6C63FF)"
        ), unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Data preview + column type pie ───────────────────────
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("#### 📋 Data Preview")
        st.dataframe(
            df.head(12).style.set_properties(**{
                "background-color": "#141720",
                "color": "#F0F2FF",
                "border": "1px solid #252836",
            }),
            use_container_width=True,
        )

    with col_right:
        st.markdown("#### 🔢 Column Composition")
        col_types = {
            "Numeric":   len(ncols),
            "Text":      len(ccols),
            "Date/Time": len(dcols),
            "Other":     len(df.columns) - len(ncols) - len(ccols) - len(dcols),
        }
        col_types = {k: v for k, v in col_types.items() if v > 0}
        fig = px.pie(
            values=list(col_types.values()),
            names=list(col_types.keys()),
            color_discrete_sequence=chart_colors(),
            hole=0.5,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label",
                          textfont_size=12)
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#F0F2FF", showlegend=True, height=280,
            margin=dict(t=10, b=10, l=10, r=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Advanced distribution section ─────────────────────────
    st.markdown("---")
    st.markdown("#### 🔍 Distribution & Correlation Analysis")

    tab_dist, tab_scatter, tab_cat, tab_corr, tab_time = st.tabs([
        "Distribution", "Scatter", "Category", "Correlation", "Time Series"
    ])

    with tab_dist:
        if ncols:
            c1, c2 = st.columns(2)
            with c1:
                sel_col   = st.selectbox("Column", ncols, key="bi_dist_col")
                chart_typ = st.selectbox("Chart Type", ["Histogram", "Box Plot",
                                         "Violin", "ECDF"], key="bi_dist_type")
            with c2:
                if sel_col:
                    pal = chart_colors()
                    if chart_typ == "Histogram":
                        fig = px.histogram(df, x=sel_col, nbins=40,
                                           color_discrete_sequence=[pal[0]], opacity=0.85)
                    elif chart_typ == "Box Plot":
                        fig = px.box(df, y=sel_col, color_discrete_sequence=[pal[1]])
                    elif chart_typ == "Violin":
                        fig = px.violin(df, y=sel_col, box=True,
                                        color_discrete_sequence=[pal[2]])
                    else:
                        fig = px.ecdf(df, x=sel_col, color_discrete_sequence=[pal[3]])
                    fig.update_layout(**_chart_layout(), height=350)
                    st.plotly_chart(fig, use_container_width=True)

    with tab_scatter:
        if len(ncols) >= 2:
            c1, c2, c3 = st.columns(3)
            with c1: x_col = st.selectbox("X axis", ncols, key="bi_sc_x")
            with c2: y_col = st.selectbox("Y axis", ncols, index=1, key="bi_sc_y")
            with c3: clr   = st.selectbox("Color by", ["None"] + ccols, key="bi_sc_clr")
            color_arg = None if clr == "None" else clr
            fig = px.scatter(df, x=x_col, y=y_col, color=color_arg,
                             trendline="ols", opacity=0.7,
                             color_discrete_sequence=px.colors.qualitative.Vivid)
            fig.update_layout(**_chart_layout(), height=400)
            st.plotly_chart(fig, use_container_width=True)

    with tab_cat:
        if ccols and ncols:
            c1, c2 = st.columns(2)
            with c1: cat_c = st.selectbox("Category", ccols, key="bi_cat_c")
            with c2: val_c = st.selectbox("Value", ncols, key="bi_cat_v")
            grouped = (
                df.groupby(cat_c)[val_c].mean()
                .sort_values(ascending=False).head(12)
            )
            fig = px.bar(
                x=grouped.index, y=grouped.values,
                color=grouped.values,
                color_continuous_scale=chart_scale(),
                title=f"Avg {val_c} by {cat_c}",
            )
            fig.update_layout(**_chart_layout(), height=380,
                              xaxis_tickangle=-35)
            st.plotly_chart(fig, use_container_width=True)

    with tab_corr:
        if len(ncols) > 1:
            corr = df[ncols[:15]].corr()
            fig = px.imshow(
                corr, text_auto=".2f",
                color_continuous_scale="RdBu_r",
                title="Pearson Correlation Matrix",
            )
            fig.update_layout(**_chart_layout(), height=500)
            st.plotly_chart(fig, use_container_width=True)

            # Top correlations table
            upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
            pairs = (
                upper.stack().reset_index()
                .rename(columns={0: "Correlation", "level_0": "Var 1", "level_1": "Var 2"})
                .assign(Abs=lambda x: x["Correlation"].abs())
                .sort_values("Abs", ascending=False)
                .drop(columns="Abs")
                .head(8)
                .round(4)
            )
            st.dataframe(pairs, use_container_width=True, hide_index=True)

    with tab_time:
        if dcols and ncols:
            c1, c2 = st.columns(2)
            with c1: dt_c = st.selectbox("Date column", dcols, key="bi_ts_dc")
            with c2: vl_c = st.selectbox("Value column", ncols, key="bi_ts_vc")
            try:
                tmp = df[[dt_c, vl_c]].copy()
                tmp[dt_c] = pd.to_datetime(tmp[dt_c], errors="coerce")
                tmp = tmp.dropna().sort_values(dt_c)
                ts  = tmp.set_index(dt_c)[vl_c].resample("D").mean().dropna()
                ma7 = ts.rolling(7).mean()
                pal = chart_colors()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=ts.index, y=ts.values, mode="lines",
                                         name="Daily", line=dict(color=pal[0], width=1)))
                fig.add_trace(go.Scatter(x=ma7.index, y=ma7.values, mode="lines",
                                         name="7-Day MA", line=dict(color=pal[1], width=2.5)))
                fig.update_layout(**_chart_layout(), height=400,
                                  xaxis_title="Date", yaxis_title=vl_c)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Time series error: {e}")
        else:
            st.info("Upload data with date and numeric columns for time series analysis.")


# ─────────────────────────────────────────────────────────────
# Shared chart layout helper
# ─────────────────────────────────────────────────────────────

def _chart_layout():
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F0F2FF", family="Inter"),
        xaxis=dict(showgrid=True, gridcolor="#252836", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#252836", zeroline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#252836"),
        margin=dict(t=40, b=30, l=10, r=10),
    )
