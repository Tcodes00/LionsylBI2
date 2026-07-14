"""
LionsylAI – Tab 4: Strategic Insights
Auto-generated profitability, growth, risk, and roadmap recommendations.
"""
from __future__ import annotations
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.data_engine import detect_columns, numeric_cols, categorical_cols, calc_growth
from design import section_header, insight_card, kpi_card, badge


def render(df: pd.DataFrame):
    st.markdown(section_header(
        "🎯 Strategic Business Insights",
        "AI-generated recommendations across profitability, growth, risk and operations"
    ), unsafe_allow_html=True)

    det   = detect_columns(df)
    ncols = numeric_cols(df)
    ccols = categorical_cols(df)

    rev_col  = det["revenue"][0]  if det["revenue"]  else (ncols[0] if ncols else None)
    cost_col = det["cost"][0]     if det["cost"]      else (ncols[1] if len(ncols) > 1 else None)

    # ── Compute base metrics ──────────────────────────────────
    def s(col): return pd.to_numeric(df[col], errors="coerce").dropna() if col else pd.Series(dtype=float)

    rev_s  = s(rev_col)
    cost_s = s(cost_col)

    total_rev    = float(rev_s.sum())  if len(rev_s)  else 0
    total_cost   = float(cost_s.sum()) if len(cost_s) else 0
    total_profit = total_rev - total_cost
    margin_pct   = (total_profit / total_rev * 100) if total_rev else 0
    rev_growth   = calc_growth(rev_s)
    cost_ratio   = (total_cost / total_rev * 100) if total_rev else 0
    n_customers  = df[det["customer"][0]].nunique() if det["customer"] else 0
    n_products   = df[det["category"][0]].nunique() if det["category"] else 0

    # ── Executive Score Card ──────────────────────────────────
    st.markdown("### 📋 Executive Scorecard")
    score = _compute_score(margin_pct, rev_growth, cost_ratio)
    _render_scorecard(score, margin_pct, rev_growth, cost_ratio, n_customers, n_products)

    st.markdown("---")

    # ── Insight tabs ──────────────────────────────────────────
    t1, t2, t3, t4, t5 = st.tabs([
        "💰 Profitability", "🚀 Growth", "⚡ Operations",
        "⚠️ Risk", "🗺️ Roadmap"
    ])

    with t1:
        _profitability_insights(margin_pct, total_rev, total_profit, cost_ratio)

    with t2:
        _growth_insights(df, det, rev_col, rev_growth, ccols, ncols)

    with t3:
        _operational_insights(df, det, ncols, ccols)

    with t4:
        _risk_insights(margin_pct, cost_ratio, rev_growth, df)

    with t5:
        _strategic_roadmap(margin_pct, rev_growth)


# ─────────────────────────────────────────────────────────────
# Scorecard
# ─────────────────────────────────────────────────────────────

def _compute_score(margin, growth, cost_ratio):
    score = 50
    if margin > 25: score += 20
    elif margin > 15: score += 12
    elif margin > 5: score += 5
    else: score -= 10
    if growth > 15: score += 15
    elif growth > 5: score += 8
    elif growth > 0: score += 3
    else: score -= 8
    if cost_ratio < 60: score += 10
    elif cost_ratio < 75: score += 5
    elif cost_ratio > 90: score -= 10
    return min(max(score, 0), 100)


def _render_scorecard(score, margin, growth, cost_ratio, customers, products):
    grade = "A+" if score >= 90 else "A" if score >= 80 else "B+" if score >= 70 else \
            "B" if score >= 60 else "C+" if score >= 50 else "C" if score >= 40 else "D"
    color = "#10B981" if score >= 70 else "#F59E0B" if score >= 50 else "#EF4444"

    st.markdown(f"""
    <div style="background:#141720;border:1px solid #252836;border-radius:20px;
                padding:32px;display:flex;align-items:center;gap:40px;margin-bottom:24px;">
      <div style="text-align:center;min-width:100px;">
        <div style="font-size:64px;font-weight:900;color:{color};font-family:'Space Grotesk',sans-serif;
                    line-height:1;">{grade}</div>
        <div style="font-size:13px;color:#9CA3AF;margin-top:4px;">Business Score</div>
        <div style="height:6px;background:#252836;border-radius:3px;margin-top:8px;">
          <div style="height:6px;width:{score}%;background:{color};border-radius:3px;"></div>
        </div>
        <div style="font-size:11px;color:{color};margin-top:4px;">{score}/100</div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:16px;flex:1;">
        <div><div style="font-size:11px;color:#6B7280;text-transform:uppercase;
                         letter-spacing:0.1em;">Profit Margin</div>
             <div style="font-size:22px;font-weight:700;color:#F0F2FF;">{margin:.1f}%</div></div>
        <div><div style="font-size:11px;color:#6B7280;text-transform:uppercase;
                         letter-spacing:0.1em;">Revenue Growth</div>
             <div style="font-size:22px;font-weight:700;color:#F0F2FF;">{growth:+.1f}%</div></div>
        <div><div style="font-size:11px;color:#6B7280;text-transform:uppercase;
                         letter-spacing:0.1em;">Cost Ratio</div>
             <div style="font-size:22px;font-weight:700;color:#F0F2FF;">{cost_ratio:.1f}%</div></div>
        <div><div style="font-size:11px;color:#6B7280;text-transform:uppercase;
                         letter-spacing:0.1em;">Customers</div>
             <div style="font-size:22px;font-weight:700;color:#F0F2FF;">{customers:,}</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Profitability
# ─────────────────────────────────────────────────────────────

def _profitability_insights(margin, total_rev, total_profit, cost_ratio):
    st.markdown("#### 💰 Profitability Analysis")
    insights = []
    if margin > 25:
        insights += [
            ("🏆 **Top-quartile margins** – reinvest 20–30% of profits into R&D and market expansion.", "#10B981"),
            ("💡 **Premium positioning** – your margins support aggressive brand investment.", "#6C63FF"),
            ("🌍 **International expansion** – strong unit economics make new markets viable now.", "#0AEFFF"),
        ]
    elif margin > 15:
        insights += [
            ("✅ **Healthy profitability** – focus on volume growth while protecting margins.", "#10B981"),
            ("🔄 **Process automation** – capture additional 2–3% margin through operational efficiency.", "#6C63FF"),
            ("📊 **Price optimisation** – test selective price increases on high-value segments.", "#0AEFFF"),
        ]
    elif margin > 5:
        insights += [
            ("⚡ **Moderate margins** – urgently review top 3 cost centres for reduction opportunities.", "#F59E0B"),
            ("💸 **Pricing strategy** – move toward value-based pricing to improve realisation.", "#F59E0B"),
            ("🔍 **Product mix** – shift focus toward highest-margin SKUs or services.", "#6C63FF"),
        ]
    else:
        insights += [
            ("🚨 **Critical margin issue** – immediate cost restructuring required.", "#EF4444"),
            ("🏦 **Cash preservation** – prioritise liquidity and reduce discretionary spend.", "#EF4444"),
            ("🤝 **Supplier renegotiation** – target 5–10% reduction in input costs within 90 days.", "#F59E0B"),
        ]

    if cost_ratio < 60:
        insights.append(("💪 **Lean cost structure** – operational leverage is a competitive advantage.", "#10B981"))
    elif cost_ratio > 85:
        insights.append(("⚠️ **High cost burden** – implement zero-based budgeting across all departments.", "#EF4444"))

    for ins, col in insights:
        st.markdown(insight_card(ins, col), unsafe_allow_html=True)

    # Gauge chart – bulletproof against NaN and invalid color formats
    # Plotly's ColorValidator rejects 8-digit hex (#RRGGBBAA) in some versions;
    # use 6-digit hex or rgba() instead.
    safe_margin = 0.0 if (margin is None or math.isnan(margin)) else float(margin)

    try:
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=safe_margin,
            delta={"reference": 15, "valueformat": ".1f"},
            title={"text": "Profit Margin %", "font": {"color": "#F0F2FF"}},
            gauge={
                "axis": {"range": [-10, 50], "tickcolor": "#6B7280"},
                "bar": {"color": "#6C63FF"},
                "steps": [
                    {"range": [-10, 5], "color": "rgba(239,68,68,0.13)"},
                    {"range": [5, 15], "color": "rgba(245,158,11,0.13)"},
                    {"range": [15, 50], "color": "rgba(16,185,129,0.13)"},
                ],
                "threshold": {"line": {"color": "#0AEFFF", "width": 3}, "value": 15},
            },
            number={"suffix": "%", "font": {"color": "#F0F2FF"}},
        ))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#F0F2FF", height=280)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Gauge chart could not render: {e}")
        st.metric("Profit Margin", f"{safe_margin:.1f}%", delta=f"{safe_margin - 15:.1f}%")


# ─────────────────────────────────────────────────────────────
# Growth
# ─────────────────────────────────────────────────────────────

def _growth_insights(df, det, rev_col, rev_growth, ccols, ncols):
    st.markdown("#### 🚀 Growth Opportunities")

    insights = []
    if rev_growth > 20:
        insights += [
            (f"🚀 **Hyper-growth detected** ({rev_growth:.1f}%) – scale infrastructure now.", "#10B981"),
            ("📈 **Momentum capture** – double down on top-performing channels.", "#6C63FF"),
        ]
    elif rev_growth > 10:
        insights += [
            (f"📈 **Strong growth** ({rev_growth:.1f}%) – expand into adjacent markets.", "#10B981"),
            ("🎯 **Customer acquisition** – increase CAC budget by 20–30%.", "#6C63FF"),
        ]
    elif rev_growth > 0:
        insights += [
            (f"✅ **Positive trajectory** ({rev_growth:.1f}%) – optimise conversion funnels.", "#6C63FF"),
            ("🔄 **Upsell / cross-sell** – target existing customers for expansion revenue.", "#0AEFFF"),
        ]
    else:
        insights += [
            (f"📉 **Revenue decline** ({rev_growth:.1f}%) – analyse churn and win-back campaigns.", "#EF4444"),
            ("🔍 **Root cause** – segment revenue by product/region to identify decline drivers.", "#F59E0B"),
        ]

    insights += [
        ("🤖 **AI-driven personalisation** – deploy ML models to increase conversion by 15–25%.", "#6C63FF"),
        ("🌐 **Digital channels** – expand e-commerce and digital presence for lower CAC.", "#0AEFFF"),
        ("🤝 **Strategic partnerships** – pursue co-marketing with complementary brands.", "#6C63FF"),
    ]

    for ins, col in insights:
        st.markdown(insight_card(ins, col), unsafe_allow_html=True)

    # Category growth if available
    if det["category"] and rev_col:
        cat_c = det["category"][0]
        try:
            rev_num = pd.to_numeric(df[rev_col], errors="coerce")
            cat_rev = df[rev_num.notna()].groupby(cat_c)[rev_col].sum().sort_values(ascending=False)
            fig = px.treemap(
                names=cat_rev.index.tolist(),
                parents=["" for _ in cat_rev],
                values=cat_rev.values.tolist(),
                title="Revenue Treemap by Category",
                color=cat_rev.values.tolist(),
                color_continuous_scale="Viridis",
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                              font_color="#F0F2FF", height=360)
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
# Operational
# ─────────────────────────────────────────────────────────────

def _operational_insights(df, det, ncols, ccols):
    st.markdown("#### ⚡ Operational Efficiency")
    insights = [
        ("⚡ **Process automation** – identify repetitive workflows for RPA implementation.", "#6C63FF"),
        ("📦 **Supply chain** – implement demand-driven replenishment to reduce working capital.", "#0AEFFF"),
        ("🔄 **Lean methodology** – run value-stream mapping to eliminate waste.", "#10B981"),
        ("📊 **Real-time KPIs** – deploy live dashboards across all operational teams.", "#6C63FF"),
        ("🧑‍💻 **Digital tools** – invest in ERP/CRM integration for single source of truth.", "#0AEFFF"),
    ]

    if det["quantity"] and det["revenue"]:
        qty_c = det["quantity"][0]
        rev_c = det["revenue"][0]
        try:
            qty_n = pd.to_numeric(df[qty_c], errors="coerce")
            rev_n = pd.to_numeric(df[rev_c], errors="coerce")
            mask  = qty_n.notna() & rev_n.notna() & (qty_n > 0)
            if mask.any():
                rpu = float(rev_n[mask].sum() / qty_n[mask].sum())
                insights.insert(0, (
                    f"📦 **Revenue per unit: ${rpu:,.2f}** – benchmark against industry standards.",
                    "#10B981"
                ))
        except Exception:
            pass

    for ins, col in insights:
        st.markdown(insight_card(ins, col), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Risk
# ─────────────────────────────────────────────────────────────

def _risk_insights(margin, cost_ratio, growth, df):
    st.markdown("#### ⚠️ Risk Assessment")

    risks = []
    if margin < 5:
        risks.append(("🚨 **Solvency risk** – margins below safe threshold. Immediate action required.", "Critical", "#EF4444"))
    if cost_ratio > 90:
        risks.append(("🔴 **Cost concentration** – cost ratio >90% leaves no buffer for downturns.", "High", "#EF4444"))
    if growth < -10:
        risks.append(("🔴 **Revenue erosion** – sustained decline signals structural market issues.", "High", "#EF4444"))
    if cost_ratio > 75:
        risks.append(("🟡 **Margin compression** – rising costs may accelerate without intervention.", "Medium", "#F59E0B"))
    if growth < 0:
        risks.append(("🟡 **Growth stagnation** – flat/negative growth creates competitive vulnerability.", "Medium", "#F59E0B"))

    # Always-on risks
    risks += [
        ("🟡 **Concentration risk** – evaluate customer/supplier concentration for single points of failure.", "Medium", "#F59E0B"),
        ("🟢 **Regulatory compliance** – ensure data protection and financial reporting standards are met.", "Low", "#10B981"),
        ("🟢 **Cybersecurity** – strengthen endpoint protection and employee training.", "Low", "#10B981"),
        ("🟢 **Talent retention** – monitor engagement and implement competitive compensation reviews.", "Low", "#10B981"),
    ]

    if risks:
        risk_df = pd.DataFrame([{"Risk": r[0].split("**")[1].split("**")[0],
                                  "Severity": r[1], "Color": r[2]} for r in risks])
        col_map = {"Critical": "#EF4444", "High": "#F97316", "Medium": "#F59E0B", "Low": "#10B981"}
        c1, c2, c3, c4 = st.columns(4)
        for sev, col in [("Critical", c1), ("High", c2), ("Medium", c3), ("Low", c4)]:
            n = len(risk_df[risk_df["Severity"] == sev])
            with col:
                st.markdown(kpi_card(f"{sev} Risks", str(n), icon="⚠️",
                            gradient=f"linear-gradient(135deg,{col_map[sev]},{col_map[sev]}88)"),
                            unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        for r, sev, col in risks:
            st.markdown(insight_card(r, col), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Roadmap
# ─────────────────────────────────────────────────────────────

def _strategic_roadmap(margin, growth):
    st.markdown("#### 🗺️ Strategic Implementation Roadmap")

    phases = [
        ("🚀 Quick Wins", "0–90 days", "#10B981", [
            "🎯 Price optimisation on top 20% of SKUs",
            "📧 Automated customer retention sequences",
            "🔄 3 highest-impact process automations",
            "📊 Live KPI dashboard for leadership team",
            "👥 Cross-sell/upsell training for sales team",
        ]),
        ("📈 Growth Initiatives", "3–12 months", "#6C63FF", [
            "🤖 AI analytics implementation across divisions",
            "🌐 Digital channel expansion (e-commerce, social)",
            "🤝 2–3 strategic partnership agreements",
            "📱 Customer experience platform upgrade",
            "🔒 Cybersecurity framework implementation",
        ]),
        ("🌟 Long-Term Vision", "1–3 years", "#0AEFFF", [
            "🚀 International market entry (2 new markets)",
            "🎓 Leadership & talent development pipeline",
            "🌱 ESG strategy and sustainability programme",
            "🏢 M&A screening for consolidation opportunities",
            "🔬 R&D innovation pipeline (3 new offerings)",
        ]),
    ]

    for title, timeline, color, items in phases:
        st.markdown(f"""
        <div style="background:#141720;border:1px solid #252836;border-left:4px solid {color};
                    border-radius:0 16px 16px 0;padding:20px 24px;margin:12px 0;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <h4 style="margin:0;color:#fff;font-family:'Space Grotesk',sans-serif;">{title}</h4>
            <span style="background:{color}22;color:{color};border:1px solid {color}55;
                         border-radius:20px;padding:3px 12px;font-size:12px;font-weight:700;">
              {timeline}
            </span>
          </div>
          {"".join(f'<div style="color:#E0E4F0;font-size:14px;padding:4px 0;border-bottom:1px solid #252836;">{item}</div>' for item in items)}
        </div>
        """, unsafe_allow_html=True)
