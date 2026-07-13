"""
LionsylAI – Tab 5: Advanced Analytics
Anomaly Detection · Correlation · Time Series · Custom Visualisations · NLP
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.data_engine import numeric_cols, categorical_cols, date_cols
from design import section_header, insight_card, kpi_card


def render(df: pd.DataFrame):
    st.markdown(section_header(
        "🔬 Advanced Analytics",
        "Anomaly detection · Correlation · Time series · Custom visualisations"
    ), unsafe_allow_html=True)

    sub = st.radio(
        "Module",
        ["🔍 Anomaly Detection", "🔗 Correlation Deep-Dive",
         "📅 Time Series", "📊 Custom Charts", "🌐 Geo & Network"],
        horizontal=True, label_visibility="collapsed",
    )

    if sub == "🔍 Anomaly Detection":
        _anomaly_detection(df)
    elif sub == "🔗 Correlation Deep-Dive":
        _correlation_deep(df)
    elif sub == "📅 Time Series":
        _time_series(df)
    elif sub == "📊 Custom Charts":
        _custom_charts(df)
    elif sub == "🌐 Geo & Network":
        _geo_network(df)


# ─────────────────────────────────────────────────────────────
# Anomaly Detection
# ─────────────────────────────────────────────────────────────

def _anomaly_detection(df: pd.DataFrame):
    st.markdown("### 🔍 Anomaly Detection")
    ncols = numeric_cols(df)
    if not ncols:
        st.warning("No numeric columns found.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        sel_col   = st.selectbox("Column", ncols, key="ad_col")
    with c2:
        method    = st.selectbox("Method", ["Z-Score", "IQR", "Modified Z-Score"], key="ad_method")
    with c3:
        threshold = st.slider("Sensitivity", 1.0, 5.0, 3.0, 0.1, key="ad_thresh")

    if st.button("🔍 Detect Anomalies", type="primary", use_container_width=True):
        data = pd.to_numeric(df[sel_col], errors="coerce").dropna()

        if method == "Z-Score":
            z = np.abs((data - data.mean()) / data.std())
            mask = z > threshold
        elif method == "IQR":
            q1, q3 = data.quantile(0.25), data.quantile(0.75)
            iqr = q3 - q1
            mask = (data < q1 - threshold * iqr) | (data > q3 + threshold * iqr)
        else:  # Modified Z-Score
            median = data.median()
            mad = (data - median).abs().median()
            mz = 0.6745 * (data - median) / (mad + 1e-9)
            mask = mz.abs() > threshold

        normal    = data[~mask]
        anomalies = data[mask]

        # ── Metrics ──────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Points",   f"{len(data):,}")
        c2.metric("Anomalies",      f"{len(anomalies):,}")
        c3.metric("Anomaly Rate",   f"{len(anomalies)/len(data)*100:.2f}%")
        c4.metric("Largest Outlier",f"{anomalies.max():,.2f}" if len(anomalies) else "N/A")

        # ── Scatter plot ──────────────────────────────────────
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=normal.index, y=normal.values,
            mode="markers", name="Normal",
            marker=dict(color="#6C63FF", size=5, opacity=0.6)
        ))
        fig.add_trace(go.Scatter(
            x=anomalies.index, y=anomalies.values,
            mode="markers", name="Anomaly",
            marker=dict(color="#EF4444", size=10, symbol="x",
                        line=dict(width=2, color="#EF4444"))
        ))
        fig.update_layout(**_cl(), height=400,
                          title=f"Anomaly Detection – {sel_col} ({method})",
                          xaxis_title="Index", yaxis_title=sel_col)
        st.plotly_chart(fig, use_container_width=True)

        # ── Distribution overlay ──────────────────────────────
        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(x=normal.values, name="Normal",
                                    marker_color="#6C63FF", opacity=0.7))
        fig2.add_trace(go.Histogram(x=anomalies.values, name="Anomaly",
                                    marker_color="#EF4444", opacity=0.9))
        fig2.update_layout(**_cl(), height=300, barmode="overlay",
                           title="Distribution: Normal vs Anomaly")
        st.plotly_chart(fig2, use_container_width=True)

        # ── Anomaly table ─────────────────────────────────────
        if len(anomalies) > 0:
            st.markdown("#### 📋 Anomaly Details")
            anom_df = pd.DataFrame({
                "Index": anomalies.index,
                "Value": anomalies.values,
                "Deviation from Mean": (anomalies.values - data.mean()).round(2),
                "Std Deviations Away": ((anomalies.values - data.mean()) / data.std()).round(2),
            })
            st.dataframe(anom_df.head(50), use_container_width=True, hide_index=True)

        # ── Insights ──────────────────────────────────────────
        rate = len(anomalies) / len(data) * 100
        if rate > 5:
            st.markdown(insight_card(
                f"⚠️ **High anomaly rate ({rate:.1f}%)** – investigate data quality and potential fraud.",
                "#EF4444"), unsafe_allow_html=True)
        elif rate > 1:
            st.markdown(insight_card(
                f"🟡 **Moderate anomalies ({rate:.1f}%)** – review flagged records for accuracy.",
                "#F59E0B"), unsafe_allow_html=True)
        else:
            st.markdown(insight_card(
                f"✅ **Low anomaly rate ({rate:.1f}%)** – data quality looks healthy.",
                "#10B981"), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Correlation Deep-Dive
# ─────────────────────────────────────────────────────────────

def _correlation_deep(df: pd.DataFrame):
    st.markdown("### 🔗 Correlation Deep-Dive")
    ncols = numeric_cols(df)
    if len(ncols) < 2:
        st.warning("Need at least 2 numeric columns.")
        return

    c1, c2 = st.columns(2)
    with c1:
        method = st.selectbox("Correlation Method",
                              ["Pearson", "Spearman", "Kendall"], key="corr_method")
    with c2:
        max_cols = st.slider("Max columns", 5, min(30, len(ncols)), min(15, len(ncols)), key="corr_maxc")

    cols_sel = ncols[:max_cols]
    corr = df[cols_sel].corr(method=method.lower())

    # Heatmap
    fig = px.imshow(
        corr, text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1, zmax=1,
        title=f"{method} Correlation Matrix",
    )
    fig.update_layout(**_cl(), height=520)
    st.plotly_chart(fig, use_container_width=True)

    # Top pairs
    st.markdown("#### 🏆 Strongest Pairs")
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    pairs = (
        upper.stack().reset_index()
        .rename(columns={0: "Correlation", "level_0": "Variable A", "level_1": "Variable B"})
        .assign(AbsCorr=lambda x: x["Correlation"].abs())
        .sort_values("AbsCorr", ascending=False)
        .drop(columns="AbsCorr")
        .head(10)
        .round(4)
    )

    # Colour-code correlation strength
    def _color_corr(val):
        if abs(val) > 0.8:
            return "color: #EF4444; font-weight: bold"
        elif abs(val) > 0.6:
            return "color: #F59E0B; font-weight: bold"
        elif abs(val) > 0.4:
            return "color: #6C63FF"
        return ""

    st.dataframe(
        pairs.style.map(_color_corr, subset=["Correlation"]),
        use_container_width=True, hide_index=True
    )

    # Pair scatter
    st.markdown("#### 🔎 Pair Deep-Dive")
    c1, c2 = st.columns(2)
    with c1: xc = st.selectbox("X variable", cols_sel, key="corr_x")
    with c2: yc = st.selectbox("Y variable", cols_sel, index=1, key="corr_y")

    fig2 = px.scatter(df, x=xc, y=yc, trendline="ols",
                      opacity=0.65, color_discrete_sequence=["#6C63FF"],
                      title=f"{yc} vs {xc} (r = {corr.loc[xc, yc]:.3f})")
    fig2.update_layout(**_cl(), height=380)
    st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# Time Series
# ─────────────────────────────────────────────────────────────

def _time_series(df: pd.DataFrame):
    st.markdown("### 📅 Time Series Analysis")
    ncols = numeric_cols(df)
    dcols = date_cols(df)

    if not dcols:
        st.warning("No datetime columns detected. Ensure date columns are in a recognisable format.")
        return
    if not ncols:
        st.warning("No numeric columns for time series analysis.")
        return

    c1, c2, c3 = st.columns(3)
    with c1: dt_c  = st.selectbox("Date column", dcols, key="ts_dc")
    with c2: val_c = st.selectbox("Value column", ncols, key="ts_vc")
    with c3: freq  = st.selectbox("Resample frequency",
                                  ["Daily (D)", "Weekly (W)", "Monthly (M)", "Quarterly (Q)"],
                                  key="ts_freq")

    freq_map = {"Daily (D)": "D", "Weekly (W)": "W", "Monthly (M)": "ME", "Quarterly (Q)": "QE"}
    f = freq_map[freq]

    try:
        tmp = df[[dt_c, val_c]].copy()
        tmp[dt_c] = pd.to_datetime(tmp[dt_c], errors="coerce")
        tmp = tmp.dropna().sort_values(dt_c)
        ts  = tmp.set_index(dt_c)[val_c].resample(f).agg(["sum", "mean", "count"]).dropna()

        if ts.empty:
            st.warning("No data after resampling.")
            return

        # ── Metrics ──────────────────────────────────────────
        pct_c = ts["sum"].pct_change().dropna()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Peak Value",    f"{ts['sum'].max():,.0f}")
        c2.metric("Avg per Period",f"{ts['sum'].mean():,.0f}")
        c3.metric("Avg Growth",    f"{pct_c.mean()*100:.1f}%")
        c4.metric("Volatility",    f"{pct_c.std()*100:.1f}%")

        # ── Main trend chart ──────────────────────────────────
        ma_w = min(7, len(ts))
        ma   = ts["sum"].rolling(window=ma_w).mean()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ts.index, y=ts["sum"].values,
                                 mode="lines", name="Actual",
                                 line=dict(color="#6C63FF", width=1.5),
                                 fill="tozeroy", fillcolor="rgba(108,99,255,0.08)"))
        fig.add_trace(go.Scatter(x=ma.index, y=ma.values,
                                 mode="lines", name=f"{ma_w}-period MA",
                                 line=dict(color="#0AEFFF", width=2.5)))
        fig.update_layout(**_cl(), height=400,
                          title=f"{val_c} – {freq} Trend",
                          xaxis_title="Period", yaxis_title=val_c)
        st.plotly_chart(fig, use_container_width=True)

        # ── Seasonality (monthly heatmap) ─────────────────────
        if f in ("D", "W"):
            st.markdown("#### 🗓️ Seasonal Pattern (Month × Year)")
            tmp2 = ts["sum"].reset_index()
            tmp2.columns = ["date", "value"]
            tmp2["Year"]  = tmp2["date"].dt.year
            tmp2["Month"] = tmp2["date"].dt.strftime("%b")
            pivot = tmp2.pivot_table(index="Year", columns="Month",
                                     values="value", aggfunc="sum")
            months_order = ["Jan","Feb","Mar","Apr","May","Jun",
                            "Jul","Aug","Sep","Oct","Nov","Dec"]
            pivot = pivot.reindex(columns=[m for m in months_order if m in pivot.columns])
            fig2 = px.imshow(pivot, color_continuous_scale="Viridis",
                             title="Monthly Seasonal Heatmap")
            fig2.update_layout(**_cl(), height=300)
            st.plotly_chart(fig2, use_container_width=True)

        # ── YoY comparison ────────────────────────────────────
        st.markdown("#### 📊 Period-over-Period Comparison")
        pct_df = pct_c.reset_index()
        pct_df.columns = ["Period", "Growth %"]
        pct_df["Growth %"] *= 100
        pct_df["Color"] = pct_df["Growth %"].apply(lambda x: "#10B981" if x >= 0 else "#EF4444")
        fig3 = go.Figure(go.Bar(
            x=pct_df["Period"], y=pct_df["Growth %"],
            marker_color=pct_df["Color"].tolist(),
        ))
        fig3.update_layout(**_cl(), height=300,
                           title="Period-over-Period Growth %",
                           yaxis_title="Growth %")
        st.plotly_chart(fig3, use_container_width=True)

    except Exception as e:
        st.error(f"Time series analysis error: {e}")


# ─────────────────────────────────────────────────────────────
# Custom Charts
# ─────────────────────────────────────────────────────────────

def _custom_charts(df: pd.DataFrame):
    st.markdown("### 📊 Custom Visualisation Builder")
    ncols = numeric_cols(df)
    ccols = categorical_cols(df)
    all_c = df.columns.tolist()

    chart_type = st.selectbox("Chart Type", [
        "Heatmap (Pivot)", "Treemap", "Sunburst",
        "Parallel Coordinates", "Funnel", "Bullet Chart", "Radar Chart"
    ], key="cv_type")

    if chart_type == "Heatmap (Pivot)":
        c1, c2, c3 = st.columns(3)
        with c1: xc = st.selectbox("X (columns)", ccols or all_c, key="hm_x")
        with c2: yc = st.selectbox("Y (rows)", ccols or all_c, key="hm_y")
        with c3: vc = st.selectbox("Value", ncols, key="hm_v") if ncols else None
        if st.button("📊 Build Heatmap", type="primary", use_container_width=True) and vc:
            try:
                pivot = df.pivot_table(values=vc, index=yc, columns=xc, aggfunc="mean")
                fig = px.imshow(pivot, color_continuous_scale="Viridis",
                                title=f"Heatmap: {vc} by {xc} × {yc}", aspect="auto")
                fig.update_layout(**_cl(), height=480)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Heatmap error: {e}")

    elif chart_type == "Treemap":
        c1, c2 = st.columns(2)
        with c1: pc = st.selectbox("Path (hierarchy)", ccols or all_c, key="tm_p")
        with c2: vc = st.selectbox("Value", ncols, key="tm_v") if ncols else None
        if st.button("📊 Build Treemap", type="primary", use_container_width=True) and vc:
            try:
                fig = px.treemap(df, path=[pc], values=vc,
                                 color=vc, color_continuous_scale="Viridis",
                                 title=f"Treemap: {vc} by {pc}")
                fig.update_layout(**_cl(), height=480)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Treemap error: {e}")

    elif chart_type == "Sunburst":
        c1, c2 = st.columns(2)
        with c1: pc = st.selectbox("Path", ccols or all_c, key="sb_p")
        with c2: vc = st.selectbox("Value", ncols, key="sb_v") if ncols else None
        if st.button("📊 Build Sunburst", type="primary", use_container_width=True) and vc:
            try:
                fig = px.sunburst(df, path=[pc], values=vc,
                                  color=vc, color_continuous_scale="Viridis",
                                  title=f"Sunburst: {vc} by {pc}")
                fig.update_layout(**_cl(), height=500)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Sunburst error: {e}")

    elif chart_type == "Parallel Coordinates":
        if len(ncols) < 2:
            st.warning("Need at least 2 numeric columns.")
        else:
            cols_pc = st.multiselect("Select columns (2–8)", ncols,
                                     default=ncols[:min(5, len(ncols))], key="pc_cols")
            if st.button("📊 Build Parallel Coordinates", type="primary", use_container_width=True):
                if len(cols_pc) >= 2:
                    fig = px.parallel_coordinates(df, dimensions=cols_pc,
                                                  color=cols_pc[0],
                                                  color_continuous_scale="Viridis",
                                                  title="Parallel Coordinates")
                    fig.update_layout(**_cl(), height=500)
                    st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "Funnel":
        c1, c2 = st.columns(2)
        with c1: lc = st.selectbox("Stages (text)", ccols or all_c, key="fn_l")
        with c2: vc = st.selectbox("Values", ncols, key="fn_v") if ncols else None
        if st.button("📊 Build Funnel", type="primary", use_container_width=True) and vc:
            try:
                agg = df.groupby(lc)[vc].sum().sort_values(ascending=False)
                fig = go.Figure(go.Funnel(
                    y=agg.index.tolist(), x=agg.values.tolist(),
                    textinfo="value+percent total",
                    marker={"color": ["#6C63FF","#8B84FF","#0AEFFF",
                                      "#10B981","#F59E0B"][:len(agg)]},
                ))
                fig.update_layout(**_cl(), height=400, title=f"Funnel: {vc} by {lc}")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Funnel error: {e}")

    elif chart_type == "Radar Chart":
        if len(ncols) < 3:
            st.warning("Need at least 3 numeric columns for a radar chart.")
        else:
            cols_r = st.multiselect("Dimensions (3–8)", ncols,
                                    default=ncols[:min(6, len(ncols))], key="rd_cols")
            if st.button("📊 Build Radar Chart", type="primary", use_container_width=True):
                if len(cols_r) >= 3:
                    mean_vals = df[cols_r].mean()
                    norm_vals = (mean_vals - mean_vals.min()) / (mean_vals.max() - mean_vals.min() + 1e-9)
                    fig = go.Figure(go.Scatterpolar(
                        r=norm_vals.values.tolist() + [norm_vals.values[0]],
                        theta=cols_r + [cols_r[0]],
                        fill="toself", fillcolor="rgba(108,99,255,0.2)",
                        line=dict(color="#6C63FF"),
                    ))
                    fig.update_layout(
                        polar=dict(
                            bgcolor="rgba(0,0,0,0)",
                            radialaxis=dict(color="#6B7280", gridcolor="#252836"),
                            angularaxis=dict(color="#9CA3AF"),
                        ),
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#F0F2FF", height=460,
                        title="Normalised Radar Chart",
                    )
                    st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "Bullet Chart":
        c1, c2 = st.columns(2)
        with c1: ac = st.selectbox("Actual column", ncols, key="bc_a")
        with c2: tc = st.selectbox("Target column", ncols, index=min(1, len(ncols)-1), key="bc_t")
        if st.button("📊 Build Bullet Chart", type="primary", use_container_width=True):
            try:
                actual = df[ac].mean()
                target = df[tc].mean()
                fig = go.Figure(go.Indicator(
                    mode="number+gauge+delta",
                    value=actual,
                    delta={"reference": target, "valueformat": ",.0f"},
                    title={"text": f"{ac} vs Target ({tc})", "font": {"color": "#F0F2FF"}},
                    gauge={
                        "shape": "bullet",
                        "axis": {"range": [0, max(actual, target) * 1.3]},
                        "threshold": {"line": {"color": "#EF4444", "width": 3}, "value": target},
                        "bar": {"color": "#6C63FF"},
                        "steps": [
                            {"range": [0, target * 0.7], "color": "#EF444422"},
                            {"range": [target * 0.7, target], "color": "#F59E0B22"},
                            {"range": [target, max(actual, target) * 1.3], "color": "#10B98122"},
                        ],
                    },
                    number={"valueformat": ",.0f", "font": {"color": "#F0F2FF"}},
                ))
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                  font_color="#F0F2FF", height=250)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Bullet chart error: {e}")


# ─────────────────────────────────────────────────────────────
# Geo & Network
# ─────────────────────────────────────────────────────────────

def _geo_network(df: pd.DataFrame):
    st.markdown("### 🌐 Geo & Network Analysis")
    ncols = numeric_cols(df)
    ccols = categorical_cols(df)

    sub = st.radio("View", ["Location Bar", "Network Graph"], horizontal=True, key="geo_sub")

    if sub == "Location Bar":
        loc_cols = [c for c in ccols if any(k in c.lower() for k in
                    ["city", "country", "region", "state", "location", "area"])] or ccols
        if not loc_cols or not ncols:
            st.info("No location or numeric columns detected.")
            return
        c1, c2 = st.columns(2)
        with c1: lc = st.selectbox("Location column", loc_cols, key="geo_lc")
        with c2: vc = st.selectbox("Value column", ncols, key="geo_vc")
        agg = df.groupby(lc)[vc].sum().sort_values(ascending=False).head(20)
        fig = px.bar(x=agg.index, y=agg.values, color=agg.values,
                     color_continuous_scale="Viridis",
                     title=f"Top Locations by {vc}")
        fig.update_layout(**_cl(), height=420, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    elif sub == "Network Graph":
        all_c = df.columns.tolist()
        if len(all_c) < 2:
            st.info("Need at least 2 columns for network analysis.")
            return
        c1, c2, c3 = st.columns(3)
        with c1: fc = st.selectbox("From", all_c, key="net_from")
        with c2: tc = st.selectbox("To", all_c, index=1, key="net_to")
        with c3: vc = st.selectbox("Weight", ["Count"] + ncols, key="net_weight")

        if vc == "Count":
            edges = df.groupby([fc, tc]).size().reset_index(name="weight")
        else:
            edges = df.groupby([fc, tc])[vc].sum().reset_index()
            edges.rename(columns={vc: "weight"}, inplace=True)

        edges = edges.nlargest(30, "weight")
        fig = px.scatter(edges, x=fc, y=tc, size="weight",
                         color="weight", color_continuous_scale="Viridis",
                         title=f"Network: {fc} → {tc}",
                         hover_data=["weight"])
        fig.update_layout(**_cl(), height=460, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)


def _cl():
    return dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F0F2FF", family="Inter"),
        xaxis=dict(showgrid=True, gridcolor="#252836", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#252836", zeroline=False),
        margin=dict(t=40, b=30, l=10, r=10),
        coloraxis_colorbar=dict(tickfont=dict(color="#F0F2FF")),
    )
