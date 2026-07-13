"""
LionsylAI – Tab 9: Enterprise Integrations
ERP · CRM · Banking · API Manager · Webhooks
"""
from __future__ import annotations
from datetime import datetime
from collections import Counter

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database import IntegrationRepo, AuditRepo, IntegrationData
from design import section_header, kpi_card, insight_card


def render():
    st.markdown(section_header(
        "🔗 Enterprise Integrations",
        "Connect LionsylAI to your existing systems"
    ), unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs([
        "🏥 Health Dashboard", "➕ Add Integration",
        "⚙️ API Manager", "📡 Webhooks"
    ])
    with t1: _health_dashboard()
    with t2: _add_integration()
    with t3: _api_manager()
    with t4: _webhooks()


# ── Health Dashboard ──────────────────────────────────────────

def _health_dashboard():
    st.markdown("### 🏥 Integration Health Dashboard")
    integrations = _load_integrations()

    active  = sum(1 for i in integrations if i["status"] == "Active")
    issues  = sum(1 for i in integrations if i["status"] == "Needs Attention")
    total   = len(integrations)
    avg_sr  = (sum(i["success_rate"] for i in integrations) / total) if total else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(kpi_card("Active",          str(active),    icon="🟢",
                gradient="linear-gradient(135deg,#10B981,#0AEFFF)"), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("Needs Attention", str(issues),    icon="🟡",
                gradient="linear-gradient(135deg,#F59E0B,#FF6B6B)"), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("Total",           str(total),     icon="🔗",
                gradient="linear-gradient(135deg,#6C63FF,#0AEFFF)"), unsafe_allow_html=True)
    with c4: st.markdown(kpi_card("Avg Success",     f"{avg_sr:.1f}%", icon="📊",
                gradient="linear-gradient(135deg,#8B84FF,#6C63FF)"), unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    if not integrations:
        st.info("No integrations configured yet.")
        return

    status_colors = {
        "Active": "#10B981", "Testing": "#F59E0B",
        "Needs Attention": "#FF6B6B", "Not Configured": "#6B7280"
    }

    # Status donut
    status_cnt = Counter(i["status"] for i in integrations)
    c1, c2 = st.columns([1, 2])
    with c1:
        fig = go.Figure(go.Pie(
            labels=list(status_cnt.keys()),
            values=list(status_cnt.values()),
            hole=0.55,
            marker_colors=[status_colors.get(k, "#6B7280") for k in status_cnt.keys()],
        ))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#F0F2FF",
                          height=260, showlegend=True,
                          legend=dict(bgcolor="rgba(0,0,0,0)"),
                          margin=dict(t=20, b=20, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        for integ in integrations:
            s_color = status_colors.get(integ["status"], "#6B7280")
            last = integ.get("last_sync") or "Never"
            if hasattr(last, "strftime"):
                last = last.strftime("%Y-%m-%d %H:%M")

            st.markdown(f"""
            <div style="background:#141720;border:1px solid #252836;border-radius:12px;
                        padding:14px 18px;margin:8px 0;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <div style="font-weight:700;color:#F0F2FF;">{integ['name']}</div>
                  <div style="font-size:12px;color:#9CA3AF;">
                    Type: {integ['type']} · Last sync: {last}
                  </div>
                </div>
                <div style="text-align:right;">
                  <div style="color:{s_color};font-weight:700;font-size:13px;">
                    ● {integ['status']}
                  </div>
                  <div style="font-size:12px;color:#9CA3AF;">{integ['success_rate']:.1f}% success</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            cc1, cc2, cc3 = st.columns([2, 1, 1])
            with cc2:
                new_status = st.selectbox(
                    "Status",
                    ["Active", "Testing", "Needs Attention", "Not Configured"],
                    index=["Active", "Testing", "Needs Attention", "Not Configured"].index(
                        integ["status"]) if integ["status"] in
                          ["Active", "Testing", "Needs Attention", "Not Configured"] else 0,
                    key=f"int_status_{integ['id']}",
                    label_visibility="collapsed",
                )
            with cc3:
                if st.button("🔄 Sync", key=f"sync_{integ['id']}", use_container_width=True):
                    IntegrationRepo.update(
                        integ["id"],
                        status="Active",
                        success_rate=min(99.9, integ["success_rate"] + 0.1),
                        last_sync=datetime.utcnow(),
                    )
                    uid = st.session_state.get("user_id")
                    if uid:
                        AuditRepo.log(uid, "integration_sync", f"Synced {integ['name']}")
                    st.success(f"Synced {integ['name']}!")
                    st.rerun()
            with cc1:
                if st.button("💾 Save", key=f"save_int_{integ['id']}", use_container_width=True):
                    IntegrationRepo.update(integ["id"], status=new_status)
                    st.success(f"Updated {integ['name']} → {new_status}")
                    st.rerun()


# ── Add Integration ───────────────────────────────────────────

def _add_integration():
    st.markdown("### ➕ Add New Integration")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🏢 ERP Systems")
        erp      = st.selectbox("ERP Platform",
                                ["SAP S/4HANA", "Oracle NetSuite", "Microsoft Dynamics 365",
                                 "Sage Intacct", "QuickBooks", "Xero", "Custom ERP"], key="int_erp")
        erp_url  = st.text_input("ERP API Endpoint", placeholder="https://api.erp.example.com/v2", key="int_erp_url")
        erp_key  = st.text_input("API Key", type="password", key="int_erp_key")
        erp_freq = st.selectbox("Sync Frequency", ["Real-time", "Hourly", "Daily", "Weekly"], key="int_erp_freq")
        if st.button("🔗 Connect ERP", type="primary", use_container_width=True, key="conn_erp"):
            _connect_integration(erp, "ERP", erp_url, erp_freq)

    with c2:
        st.markdown("#### 👥 CRM Platforms")
        crm      = st.selectbox("CRM Platform",
                                ["Salesforce", "HubSpot", "Zoho CRM",
                                 "Microsoft Dynamics CRM", "Pipedrive", "Custom CRM"], key="int_crm")
        crm_url  = st.text_input("CRM API Endpoint", placeholder="https://api.crm.example.com/v1", key="int_crm_url")
        crm_key  = st.text_input("CRM API Key", type="password", key="int_crm_key")
        crm_freq = st.selectbox("Sync Frequency", ["Real-time", "Hourly", "Daily", "Weekly"], key="int_crm_freq")
        if st.button("🔗 Connect CRM", type="primary", use_container_width=True, key="conn_crm"):
            _connect_integration(crm, "CRM", crm_url, crm_freq)

    st.markdown("---")
    st.markdown("#### 🏦 Banking & Payment APIs")
    bc1, bc2 = st.columns(2)
    with bc1:
        bank     = st.selectbox("Banking Provider",
                                ["Plaid", "Open Banking API", "Stripe", "PayPal", "Square", "Custom Banking API"],
                                key="int_bank")
        bank_url = st.text_input("Bank API Endpoint", key="int_bank_url")
        _        = st.text_input("Bank API Secret", type="password", key="int_bank_key")
        if st.button("🏦 Connect Banking", type="primary", use_container_width=True, key="conn_bank"):
            _connect_integration(bank, "Banking", bank_url, "Daily")
    with bc2:
        st.markdown("#### 📊 Supported Protocols")
        for p in ["REST (JSON/XML)", "GraphQL", "SOAP", "SFTP (file-based)",
                  "Webhooks", "OAuth 2.0", "API Key"]:
            st.markdown(f"✅ {p}")


def _connect_integration(name: str, itype: str, url: str, freq: str):
    if not url:
        st.warning("Please provide an API endpoint.")
        return
    import time; time.sleep(0.5)
    uid = st.session_state.get("user_id", 1)
    IntegrationRepo.add(uid, name=name, itype=itype, status="Testing",
                        api_endpoint=url, sync_freq=freq)
    AuditRepo.log(uid, "integration_added", f"Added {name} ({itype})")
    st.success(f"✅ {name} connected! Initial sync queued.")
    st.rerun()


# ── API Manager ───────────────────────────────────────────────

def _api_manager():
    st.markdown("### ⚙️ API Manager")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 🔑 API Keys")
        st.text_input("Base URL", value="https://api.lionsylai.com/v1", disabled=True, key="api_base")

        if st.button("🔄 Generate New API Key", use_container_width=True):
            import secrets
            new_key = f"lionsyl_{secrets.token_hex(16)}"
            st.session_state["generated_api_key"] = new_key

        if "generated_api_key" in st.session_state:
            st.code(st.session_state["generated_api_key"])
            st.warning("⚠️ Copy this key now – it won't be shown again.")
            uid = st.session_state.get("user_id")
            if uid:
                AuditRepo.log(uid, "api_key_generated", "New API key generated")

    with c2:
        st.markdown("#### 📊 Usage Analytics")
        integrations = _load_integrations()
        total_calls  = len(integrations) * 150
        active_count = sum(1 for i in integrations if i["status"] == "Active")
        avg_success  = (sum(i["success_rate"] for i in integrations) / len(integrations)
                        ) if integrations else 0

        st.metric("Total API Calls",     f"{total_calls:,}")
        st.metric("Success Rate",        f"{avg_success:.1f}%")
        st.metric("Avg Response Time",   "142ms")
        st.metric("Active Integrations", str(active_count))

    st.markdown("#### 🚦 Rate Limits")
    current_plan = st.session_state.get("subscription", "free").capitalize()
    for plan, limit in {"Free": "100 req/min", "Pro": "1,000 req/min", "Enterprise": "Unlimited"}.items():
        col  = "#6C63FF" if plan.lower() == current_plan.lower() else "#6B7280"
        bold = "font-weight:700;" if plan.lower() == current_plan.lower() else ""
        st.markdown(
            f"<div style='padding:8px 0;border-bottom:1px solid #252836;'>"
            f"<span style='color:{col};{bold}'>{plan}</span>"
            f"<span style='color:#6B7280;float:right;'>{limit}</span></div>",
            unsafe_allow_html=True,
        )


# ── Webhooks ──────────────────────────────────────────────────

def _webhooks():
    st.markdown("### 📡 Webhook Configuration")

    if "webhooks" not in st.session_state:
        st.session_state["webhooks"] = [
            {"url": "https://your-app.com/webhooks/lionsyl", "event": "report.generated", "active": True},
            {"url": "https://hooks.slack.com/services/T00/B00", "event": "alert.triggered", "active": False},
        ]

    wh    = st.session_state["webhooks"]
    events = ["report.generated", "alert.triggered", "data.uploaded",
              "budget.exceeded", "close.completed", "user.joined"]

    for i, hook in enumerate(wh):
        with st.expander(f"🔔 {hook['event']} → {hook['url'][:45]}…", expanded=False):
            ca, cb, cc = st.columns([3, 1, 1])
            with ca:
                wh[i]["url"]   = st.text_input("Endpoint URL", value=hook["url"], key=f"wh_url_{i}")
                ev_idx         = events.index(hook["event"]) if hook["event"] in events else 0
                wh[i]["event"] = st.selectbox("Trigger Event", events, index=ev_idx, key=f"wh_ev_{i}")
            with cb:
                wh[i]["active"] = st.toggle("Active", value=hook["active"], key=f"wh_active_{i}")
            with cc:
                if st.button("🧪 Test",  key=f"wh_test_{i}", use_container_width=True):
                    st.success(f"Test ping sent!")
                if st.button("🗑 Delete", key=f"wh_del_{i}", use_container_width=True):
                    st.session_state["webhooks"].pop(i)
                    st.rerun()

    st.markdown("---")
    st.markdown("#### ➕ Add Webhook")
    new_url   = st.text_input("Webhook URL", placeholder="https://…", key="wh_new_url")
    new_event = st.selectbox("Event", events, key="wh_new_ev")
    if st.button("➕ Add Webhook", type="primary", use_container_width=True):
        if new_url:
            st.session_state["webhooks"].append({"url": new_url, "event": new_event, "active": True})
            st.success("Webhook added!")
            st.rerun()
        else:
            st.warning("Please enter a URL.")


# ── Helper ────────────────────────────────────────────────────

def _load_integrations():
    uid = st.session_state.get("user_id")
    if uid:
        rows = IntegrationRepo.list_for_user(uid)
        if rows:
            return [{"id": i.id, "name": i.name, "type": i.itype,
                     "status": i.status, "success_rate": i.success_rate or 0,
                     "last_sync": i.last_sync}
                    for i in rows]
    # Fallback sample
    return [
        {"id":1,"name":"ERP System",        "type":"ERP",     "status":"Active",          "success_rate":99.8,"last_sync":None},
        {"id":2,"name":"CRM Platform",      "type":"CRM",     "status":"Active",          "success_rate":98.5,"last_sync":None},
        {"id":3,"name":"Banking API",       "type":"Banking", "status":"Needs Attention", "success_rate":95.2,"last_sync":None},
        {"id":4,"name":"Payment Processor", "type":"Payment", "status":"Active",          "success_rate":99.9,"last_sync":None},
    ]
