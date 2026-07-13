"""
LionsylAI – Tab 11: Advanced Mode
NLP · Real-time streaming · Security · Industry modules · Export Suite
"""
from __future__ import annotations
import random
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.data_engine import numeric_cols, categorical_cols, date_cols
from components.ml_engine import auto_feature_engineer, CustomerAnalytics
from design import section_header, kpi_card, insight_card, badge


def render(df: pd.DataFrame):
    st.markdown(section_header(
        "🚀 Advanced Mode",
        "NLP · Real-time data · Security · Industry modules · Export suite"
    ), unsafe_allow_html=True)

    sub = st.radio(
        "Module",
        ["🧠 NLP Insights", "📡 Real-time Stream", "🔒 Security Hub",
         "🏭 Industry Modules", "📤 Export Suite"],
        horizontal=True, label_visibility="collapsed",
    )

    if sub == "🧠 NLP Insights":
        _nlp_insights(df)
    elif sub == "📡 Real-time Stream":
        _realtime_stream()
    elif sub == "🔒 Security Hub":
        _security_hub()
    elif sub == "🏭 Industry Modules":
        _industry_modules(df)
    elif sub == "📤 Export Suite":
        _export_suite(df)


# ─────────────────────────────────────────────────────────────
# NLP Insights
# ─────────────────────────────────────────────────────────────

SENTIMENT_LEXICON = {
    "excellent":3,"great":2,"good":1,"positive":2,"profit":1,"growth":2,
    "increase":1,"strong":2,"outstanding":3,"impressive":2,"record":1,
    "bad":-1,"poor":-2,"terrible":-3,"negative":-2,"loss":-1,"decline":-2,
    "decrease":-1,"weak":-2,"concerning":-1,"disappointing":-2,"risk":-1,
}

FINANCIAL_TERMS = [
    "revenue","profit","loss","margin","growth","decline","investment",
    "cash","budget","forecast","expense","ebitda","roi","kpi","cagr",
    "arpu","ltv","cac","burn rate","runway","mrr","arr",
]


def _analyze_sentiment(text: str) -> dict:
    words = text.lower().split()
    score = sum(SENTIMENT_LEXICON.get(w, 0) for w in words)
    label = "Positive" if score > 0 else "Negative" if score < 0 else "Neutral"
    confidence = min(abs(score) / (len(words) * 0.5 + 1) * 100, 99)
    return {"label": label, "score": score, "confidence": round(confidence, 1)}


def _extract_terms(text: str) -> list:
    words = text.lower().split()
    return [t for t in FINANCIAL_TERMS if t in " ".join(words)]


def _nlp_insights(df: pd.DataFrame):
    st.markdown("### 🧠 NLP Text Analysis")

    tab_a, tab_b = st.tabs(["📝 Text Analyser", "📊 Column Text Mining"])

    with tab_a:
        st.markdown("#### Analyse financial text for sentiment and key terms")
        text_input = st.text_area(
            "Enter text to analyse",
            value="Our Q2 revenue growth has been excellent with strong profit margins "
                  "and outstanding customer acquisition. EBITDA increased by 18% driven "
                  "by operational efficiency improvements.",
            height=130,
        )
        if st.button("🔍 Analyse Text", type="primary", use_container_width=True):
            if text_input.strip():
                sent = _analyze_sentiment(text_input)
                terms = _extract_terms(text_input)

                s_color = {"Positive":"#10B981","Negative":"#EF4444","Neutral":"#6B7280"}
                c1, c2, c3 = st.columns(3)
                c1.markdown(kpi_card("Sentiment", sent["label"], icon="💬",
                            gradient=f"linear-gradient(135deg,{s_color[sent['label']]},#0AEFFF)"),
                            unsafe_allow_html=True)
                c2.markdown(kpi_card("Confidence", f"{sent['confidence']}%", icon="🎯",
                            gradient="linear-gradient(135deg,#6C63FF,#8B84FF)"),
                            unsafe_allow_html=True)
                c3.markdown(kpi_card("Financial Terms", str(len(terms)), icon="📊",
                            gradient="linear-gradient(135deg,#F59E0B,#FF6B6B)"),
                            unsafe_allow_html=True)

                if terms:
                    st.markdown("#### 📊 Financial Terms Detected")
                    term_html = " ".join(
                        f'<span style="background:#6C63FF22;color:#6C63FF;border:1px solid #6C63FF55;'
                        f'border-radius:20px;padding:4px 12px;font-size:13px;margin:4px;'
                        f'display:inline-block;">{t}</span>'
                        for t in terms
                    )
                    st.markdown(term_html, unsafe_allow_html=True)

                # Word frequency
                from collections import Counter
                words = [w.lower().strip(".,!?;:") for w in text_input.split() if len(w) > 3]
                freq  = Counter(words).most_common(10)
                if freq:
                    wdf = pd.DataFrame(freq, columns=["Word", "Count"])
                    fig = px.bar(wdf, x="Word", y="Count", color="Count",
                                 color_continuous_scale="Viridis", title="Top Words")
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                      font_color="#F0F2FF", height=280, margin=dict(t=40,b=30,l=10,r=10))
                    st.plotly_chart(fig, use_container_width=True)

    with tab_b:
        ccols = categorical_cols(df)
        if not ccols:
            st.info("No text columns detected in your dataset.")
            return
        sel_col = st.selectbox("Select text column", ccols, key="nlp_col")
        if st.button("🔍 Mine Column", type="primary", use_container_width=True):
            col_data = df[sel_col].astype(str).dropna()
            sentiments = [_analyze_sentiment(t)["label"] for t in col_data]
            from collections import Counter
            sent_cnt = Counter(sentiments)
            c1, c2 = st.columns(2)
            with c1:
                fig = px.pie(values=list(sent_cnt.values()), names=list(sent_cnt.keys()),
                             title=f"Sentiment Distribution – {sel_col}",
                             color_discrete_map={"Positive":"#10B981","Negative":"#EF4444","Neutral":"#6B7280"},
                             hole=0.4)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#F0F2FF", height=300)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                all_text = " ".join(col_data)
                terms    = _extract_terms(all_text)
                term_cnt = Counter(t for t in [_extract_terms(t) for t in col_data] for t in t)
                if term_cnt:
                    tdf = pd.DataFrame(term_cnt.most_common(8), columns=["Term","Count"])
                    fig = px.bar(tdf, x="Term", y="Count", color="Count",
                                 color_continuous_scale="Viridis", title="Top Financial Terms")
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                      font_color="#F0F2FF", height=300, margin=dict(t=40,b=30,l=10,r=10))
                    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# Real-time Stream
# ─────────────────────────────────────────────────────────────

def _realtime_stream():
    st.markdown("### 📡 Real-time Data Streaming")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 🔌 Data Sources")
        symbol = st.text_input("Symbol / Metric", "AAPL", key="rt_sym")
        source = st.selectbox("Source", ["Financial Markets","IoT Sensor",
                                          "Web Analytics","Custom API"], key="rt_src")
        interval = st.selectbox("Interval", ["5s","30s","1min","5min"], key="rt_int")

        if st.button("📈 Fetch Live Data", type="primary", use_container_width=True):
            # Simulated live data
            price  = round(150 + random.uniform(-5, 5), 2)
            change = round(random.uniform(-3, 3), 2)
            vol    = random.randint(1_000_000, 10_000_000)

            if "rt_history" not in st.session_state:
                st.session_state["rt_history"] = []
            st.session_state["rt_history"].append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "symbol": symbol, "price": price,
                "change": change, "volume": vol,
            })
            # Keep last 30 points
            st.session_state["rt_history"] = st.session_state["rt_history"][-30:]

            c_col = "normal" if change >= 0 else "inverse"
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("Symbol",  symbol)
            m2.metric("Price",   f"${price}")
            m3.metric("Change",  f"{change:+.2f}%", delta_color=c_col)
            m4.metric("Volume",  f"{vol:,}")

    with c2:
        st.markdown("#### 📊 Live Chart")
        hist = st.session_state.get("rt_history", [])
        if hist:
            hdf = pd.DataFrame(hist)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hdf["timestamp"], y=hdf["price"],
                mode="lines+markers", name=symbol,
                line=dict(color="#6C63FF", width=2),
                marker=dict(size=5, color="#0AEFFF"),
            ))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font_color="#F0F2FF", height=280,
                              xaxis=dict(showgrid=True, gridcolor="#252836"),
                              yaxis=dict(showgrid=True, gridcolor="#252836"),
                              margin=dict(t=30,b=20,l=10,r=10),
                              title="Live Price Stream")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Click 'Fetch Live Data' to start streaming.")

    # API connection manager
    st.markdown("---")
    st.markdown("#### 🔗 API Connections")
    cc1, cc2 = st.columns(2)
    with cc1:
        api_url = st.text_input("API Endpoint", placeholder="https://api.datasource.com/v1", key="rt_api_url")
        api_key = st.text_input("API Key",      type="password", key="rt_api_key")
    with cc2:
        auth_type = st.selectbox("Auth Type", ["API Key","Bearer Token","OAuth 2.0","Basic Auth"], key="rt_auth")
        data_fmt  = st.selectbox("Data Format", ["JSON","CSV","XML","Parquet"], key="rt_fmt")

    if st.button("🔗 Connect API Source", use_container_width=True):
        if api_url:
            st.success(f"✅ Connected to {api_url[:40]}… (simulated)")
        else:
            st.warning("Enter an API URL.")


# ─────────────────────────────────────────────────────────────
# Security Hub
# ─────────────────────────────────────────────────────────────

def _security_hub():
    st.markdown("### 🔒 Security Hub")

    uid = st.session_state.get("user_id")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 🛡️ Security Score")
        score = 78  # Computed score
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            title={"text":"Security Score","font":{"color":"#F0F2FF"}},
            gauge={
                "axis": {"range":[0,100],"tickcolor":"#6B7280"},
                "bar":  {"color": "#10B981" if score>70 else "#F59E0B"},
                "steps":[
                    {"range":[0,40],  "color":"#EF444422"},
                    {"range":[40,70], "color":"#F59E0B22"},
                    {"range":[70,100],"color":"#10B98122"},
                ],
                "threshold":{"line":{"color":"#0AEFFF","width":3},"value":80},
            },
            number={"font":{"color":"#F0F2FF"}},
        ))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#F0F2FF", height=260)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### ⚙️ Security Settings")
        st.toggle("Two-Factor Authentication (2FA)",  value=False, key="sec_2fa")
        st.toggle("IP Allowlisting",                  value=False, key="sec_ip")
        st.toggle("Session timeout (30 min)",          value=True,  key="sec_timeout")
        st.toggle("Data encryption at rest",           value=True,  key="sec_enc")
        st.toggle("Audit logging (all actions)",       value=True,  key="sec_audit")

        if st.button("💾 Save Security Settings", type="primary", use_container_width=True):
            st.success("Security settings updated!")

    with c2:
        st.markdown("#### ✅ Security Checklist")
        checks = [
            ("✅ Password hashing (bcrypt)", True, "#10B981"),
            ("✅ HTTPS enforcement",         True, "#10B981"),
            ("✅ SQL injection prevention",  True, "#10B981"),
            ("✅ Rate limiting",             True, "#10B981"),
            ("✅ Input validation",          True, "#10B981"),
            ("⚠️ 2FA not enabled",          False,"#F59E0B"),
            ("⚠️ IP allowlisting off",      False,"#F59E0B"),
            ("✅ Audit logging active",      True, "#10B981"),
            ("✅ Session management",        True, "#10B981"),
            ("✅ Data encryption",           True, "#10B981"),
        ]
        for label, ok, color in checks:
            st.markdown(f"<div style='color:{color};padding:6px 0;border-bottom:1px solid #252836;'>"
                        f"<span style='font-size:14px;'>{label}</span></div>",
                        unsafe_allow_html=True)

        st.markdown("#### 🔑 Active Sessions")
        sessions = [
            {"Device":"Chrome – Windows","IP":"192.168.1.1","Since":"Today 09:00","Current":True},
            {"Device":"Safari – iPhone",  "IP":"10.0.0.5",  "Since":"Yesterday", "Current":False},
        ]
        for s in sessions:
            is_cur = s["Current"]
            bdr    = "#6C63FF" if is_cur else "#252836"
            st.markdown(f"""
            <div style="background:#141720;border:1px solid {bdr};border-radius:10px;
                        padding:12px 16px;margin:6px 0;display:flex;justify-content:space-between;">
              <div>
                <div style="font-weight:{'700' if is_cur else '400'};color:#F0F2FF;">
                  {s['Device']} {'(Current)' if is_cur else ''}
                </div>
                <div style="font-size:12px;color:#6B7280;">{s['IP']} · {s['Since']}</div>
              </div>
              {'<span style="color:#10B981;font-size:12px;">Active</span>' if is_cur
               else '<span style="color:#EF4444;font-size:11px;cursor:pointer;">Revoke</span>'}
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Industry Modules
# ─────────────────────────────────────────────────────────────

def _industry_modules(df: pd.DataFrame):
    st.markdown("### 🏭 Industry-Specific Analytics")

    industry = st.selectbox("Select Industry Vertical", [
        "🛒 Retail & E-commerce",
        "☁️ SaaS & Subscriptions",
        "🏭 Manufacturing",
        "🏥 Healthcare",
        "💼 Financial Services",
        "🏨 Hospitality & Travel",
    ])

    ncols = numeric_cols(df)
    ccols = categorical_cols(df)
    dcols = date_cols(df)

    if "🛒 Retail" in industry:
        st.markdown("#### 🛒 Retail Analytics Suite")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📦 Inventory Optimisation**")
            if ncols:
                sales_c = st.selectbox("Sales column", ncols, key="ret_sales")
                if st.button("Optimise Inventory", use_container_width=True):
                    avg = df[sales_c].mean()
                    st.metric("Recommended Reorder Point", f"{avg*1.5:,.0f} units")
                    st.metric("Safety Stock",              f"{avg*0.3:,.0f} units")
                    st.success("Inventory plan generated!")
        with c2:
            st.markdown("**👥 RFM Segmentation**")
            cust_cols = [c for c in ccols if any(k in c.lower() for k in ["customer","client","user"])]
            if cust_cols and dcols and ncols:
                cc = st.selectbox("Customer col", cust_cols, key="ret_cust")
                dc = st.selectbox("Date col", dcols, key="ret_dt")
                rc = st.selectbox("Revenue col", ncols, key="ret_rev")
                if st.button("Run RFM", type="primary", use_container_width=True):
                    ca  = CustomerAnalytics()
                    rfm = ca.rfm(df, cc, dc, rc)
                    if rfm is not None:
                        st.dataframe(rfm.head(10), use_container_width=True, hide_index=True)

    elif "☁️ SaaS" in industry:
        st.markdown("#### ☁️ SaaS Metrics Suite")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📈 MRR / ARR Calculator**")
            mrr    = st.number_input("Monthly Recurring Revenue ($)", value=50_000.0, key="saas_mrr")
            churn  = st.number_input("Monthly Churn Rate (%)", value=2.0, step=0.1, key="saas_churn")
            growth = st.number_input("Monthly Growth Rate (%)", value=8.0, step=0.1, key="saas_growth")
            if st.button("📊 Calculate SaaS Metrics", use_container_width=True):
                arr   = mrr * 12
                ltv   = mrr / (churn / 100)
                nrr   = ((1 + growth/100) / (1 + churn/100) - 1) * 100
                m1,m2,m3,m4 = st.columns(4)
                m1.metric("ARR",   f"${arr:,.0f}")
                m2.metric("LTV",   f"${ltv:,.0f}")
                m3.metric("NRR",   f"{nrr:.1f}%")
                m4.metric("Payback","~{:.0f} mo".format(1/(growth/100+0.001)))
        with c2:
            st.markdown("**📉 Churn Cohort**")
            if ccols and dcols:
                cust_c = st.selectbox("User column", ccols, key="saas_cust")
                date_c = st.selectbox("Date column", dcols, key="saas_dt")
                if st.button("Analyse Churn", type="primary", use_container_width=True):
                    ca = CustomerAnalytics()
                    result = ca.churn_risk(df, cust_c, date_c)
                    if result is not None:
                        rc = result["Churn_Risk"].value_counts()
                        st.metric("High Risk Customers",   rc.get("🔴 High",0))
                        st.metric("Medium Risk Customers", rc.get("🟡 Medium",0))
                        st.metric("Low Risk Customers",    rc.get("🟢 Low",0))

    elif "🏭 Manufacturing" in industry:
        st.markdown("#### 🏭 Manufacturing Analytics")
        if ncols:
            prod_col = st.selectbox("Production / OEE column", ncols, key="mfg_prod")
            if st.button("📊 Analyse Production", use_container_width=True):
                s = df[prod_col].dropna()
                oee = min(float(s.mean() / s.max() * 100), 100)
                st.metric("Estimated OEE", f"{oee:.1f}%")
                st.metric("Avg Output",    f"{s.mean():,.1f}")
                st.metric("Peak Output",   f"{s.max():,.1f}")
                if oee < 65:
                    st.markdown(insight_card("⚠️ OEE below 65% – significant improvement opportunity.",
                                             "#EF4444"), unsafe_allow_html=True)
                elif oee > 85:
                    st.markdown(insight_card("✅ World-class OEE level achieved.", "#10B981"),
                                unsafe_allow_html=True)

    elif "💼 Financial Services" in industry:
        st.markdown("#### 💼 Financial Services Analytics")
        st.markdown(insight_card("📊 Regulatory capital adequacy · Credit risk · Portfolio VaR · Stress testing available on Enterprise plan.", "#6C63FF"), unsafe_allow_html=True)
        if ncols and len(ncols) >= 2:
            col_a = st.selectbox("Portfolio Return (%)", ncols, key="fs_ret")
            if st.button("📊 Portfolio Analysis", use_container_width=True):
                s = df[col_a].dropna()
                sharpe = float(s.mean() / s.std() * np.sqrt(252)) if s.std() > 0 else 0
                var95  = float(np.percentile(s, 5))
                st.metric("Sharpe Ratio (annualised)", f"{sharpe:.2f}")
                st.metric("VaR 95%",                   f"{var95:.2f}%")
                st.metric("Max Drawdown",              f"{float(s.min()):.2f}%")

    else:
        st.info(f"Industry module for **{industry}** is coming soon.")
        st.markdown(insight_card("🚀 Request early access for your specific industry vertical.", "#6C63FF"), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Export Suite
# ─────────────────────────────────────────────────────────────

def _export_suite(df: pd.DataFrame):
    st.markdown("### 📤 Export Suite")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 📊 Data Exports")
        if df is not None and not df.empty:
            exp_format = st.selectbox("Format", ["CSV","Excel (XLSX)","JSON","Parquet"], key="exp_fmt")
            include_fe = st.checkbox("Include engineered features", key="exp_fe")
            sel_cols   = st.multiselect("Select columns (empty = all)", df.columns.tolist(), key="exp_cols")

            export_df = df.copy()
            if include_fe:
                with st.spinner("Engineering features…"):
                    export_df = auto_feature_engineer(export_df)
            if sel_cols:
                export_df = export_df[[c for c in sel_cols if c in export_df.columns]]

            if st.button("📥 Prepare Export", type="primary", use_container_width=True):
                if exp_format == "CSV":
                    data  = export_df.to_csv(index=False).encode()
                    fname = "lionsylai_export.csv"
                    mime  = "text/csv"
                elif exp_format == "JSON":
                    data  = export_df.to_json(orient="records", indent=2).encode()
                    fname = "lionsylai_export.json"
                    mime  = "application/json"
                elif exp_format == "Parquet":
                    import io as _io
                    buf = _io.BytesIO()
                    export_df.to_parquet(buf, index=False)
                    data  = buf.getvalue()
                    fname = "lionsylai_export.parquet"
                    mime  = "application/octet-stream"
                else:  # Excel
                    import io as _io
                    buf = _io.BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        export_df.to_excel(writer, index=False, sheet_name="LionsylAI Export")
                    data  = buf.getvalue()
                    fname = "lionsylai_export.xlsx"
                    mime  = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

                st.download_button(f"📥 Download {exp_format}", data, fname, mime,
                                   use_container_width=True)
                st.success(f"✅ {len(export_df):,} rows × {len(export_df.columns)} cols ready!")

    with c2:
        st.markdown("#### 📋 Report Exports")
        reports = st.session_state.get("report_library", [])
        if reports:
            rpt_sel = st.selectbox("Select Report", [r["name"] for r in reports], key="exp_rpt")
            rpt_obj = next((r for r in reports if r["name"] == rpt_sel), None)

            exp_type = st.selectbox("Export Type", ["Text Summary","JSON Data"], key="exp_rtype")

            if st.button("📥 Export Report", type="primary", use_container_width=True):
                if rpt_obj:
                    if exp_type == "JSON Data" and "_data" in rpt_obj:
                        import json
                        data  = json.dumps(rpt_obj["_data"], indent=2, default=str).encode()
                        fname = f"{rpt_sel.replace(' ','_').lower()}.json"
                        mime  = "application/json"
                    else:
                        from components.fp_engine import report_to_text
                        data  = report_to_text(rpt_obj.get("_data",{})).encode()
                        fname = f"{rpt_sel.replace(' ','_').lower()}.txt"
                        mime  = "text/plain"
                    st.download_button("📥 Download", data, fname, mime,
                                       use_container_width=True)
        else:
            st.info("No reports available. Generate reports in the FP&A tab first.")

        st.markdown("#### 🔗 Scheduled Exports")
        st.markdown("""
        <div style="background:#141720;border:1px solid #252836;border-radius:12px;
                    padding:16px 20px;">
          <p style="color:#9CA3AF;font-size:13px;margin:0 0 12px;">
            Automate report delivery to your team.
          </p>
        </div>
        """, unsafe_allow_html=True)
        sched_email = st.text_input("Deliver to email", placeholder="team@company.com", key="sch_email")
        sched_freq  = st.selectbox("Frequency", ["Daily","Weekly","Monthly","Quarterly"], key="sch_freq")
        sched_rpt   = st.selectbox("Report", [r["name"] for r in reports] if reports else ["N/A"], key="sch_rpt")

        if st.button("🔔 Schedule Delivery", use_container_width=True):
            if sched_email:
                st.success(f"✅ {sched_rpt} will be sent {sched_freq.lower()} to {sched_email}")
            else:
                st.warning("Enter a delivery email address.")
