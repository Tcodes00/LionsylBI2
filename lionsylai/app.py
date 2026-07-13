"""
LionsylAI - Main Application Entry Point
Enterprise Analytics Intelligence Platform 2026

Run:  streamlit run app.py
"""
from __future__ import annotations
import sys, logging, warnings
from pathlib import Path

import streamlit as st

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("lionsylai.app")

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(
    page_title="LionsylAI - Enterprise Analytics",
    page_icon="🦁", layout="wide", initial_sidebar_state="expanded",
    menu_items={
        "Get Help":     "https://docs.lionsylai.com",
        "Report a bug": "https://github.com/lionsylai/issues",
        "About":        "LionsylAI - Enterprise Analytics Intelligence Platform 2026",
    },
)


@st.cache_resource
def _boot_db():
    try:
        from database import init_db
        return init_db()
    except Exception as e:
        log.warning(f"DB init warning: {e}")
        return False

_db_ready = _boot_db()

from design import custom_css, sidebar_header, WELCOME_HEADER, STATS_GRID, FEATURE_GRID, QUICK_START_GUIDE

# ---- Session state bootstrap ----------------------------------
_DEFAULTS = {
    "authenticated": False, "user_id": None, "username": "", "user_email": "",
    "user_full_name": "", "user_role": "user", "subscription": "free",
    "org_name": "", "access_token": None, "session_token": None,
    "workspace_owner_id": None, "is_team_member": False, "team_role": "Owner",
    "app_df": None, "consolidated_df": None, "budget_data": None,
    "report_library": [], "last_report": None, "auth_view": "login",
    "show_reg": False, "rt_history": [], "comments_cache": [],
    "me_checklist": {}, "webhooks": [], "generated_api_key": None,
    "viewing_report": None, "_session_checked": False,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---- Restore session from URL token (survives page refresh) ------
def _restore_session_from_token():
    """
    On every rerun (including a hard browser refresh), Streamlit's
    session_state resets but st.query_params does NOT - the browser
    keeps the URL. We stash a session token in the URL on login and
    use it here to silently re-authenticate.
    """
    if st.session_state.authenticated or st.session_state._session_checked:
        return
    st.session_state._session_checked = True

    params = st.query_params
    token = params.get("s")
    if not token:
        return

    from database import SessionRepo, UserRepo, resolve_session_workspace
    sess = SessionRepo.get_valid(token)
    if not sess:
        # stale/expired token in URL - clear it
        try:
            st.query_params.clear()
        except Exception:
            pass
        return

    user = UserRepo.get_by_id(sess.user_id)
    if not user or not user.is_active:
        return

    st.session_state.authenticated  = True
    st.session_state.user_id        = user.id
    st.session_state.username       = user.username
    st.session_state.user_email     = user.email
    st.session_state.user_full_name = user.full_name or user.username
    st.session_state.user_role      = user.role
    st.session_state.subscription   = user.subscription
    st.session_state.org_name       = user.org_name
    st.session_state.session_token  = token
    st.session_state.update(resolve_session_workspace(user.id))
    UserRepo.touch_last_seen(user.id)


_restore_session_from_token()
st.markdown(custom_css(), unsafe_allow_html=True)


# ---- Authentication gate ---------------------------------------
if not st.session_state.authenticated:
    params = st.query_params
    if "payment" in params:
        status = params.get("payment")
        if status == "success":
            st.session_state.subscription = "pro"
            st.success("Payment successful! Pro features activated.")
        elif status == "cancel":
            st.info("Payment cancelled. You can upgrade any time.")
        elif status == "failed":
            st.error("Payment failed. Please try again or use a different method.")
        try:
            st.query_params.clear()
        except Exception:
            pass

    if "reset_token" in params:
        st.session_state.auth_view   = "reset"
        st.session_state.reset_token = params.get("reset_token")
        try:
            st.query_params.clear()
        except Exception:
            pass

    from pages.auth_page import render_auth
    render_auth()
    st.stop()

# Keep the URL session token in sync so refresh keeps working even
# after query_params got cleared by some other branch above.
if st.session_state.get("session_token"):
    try:
        if st.query_params.get("s") != st.session_state.session_token:
            st.query_params["s"] = st.session_state.session_token
    except Exception:
        pass


# ---- Authenticated Application ----------------------------------
from components.data_engine import load_file, quick_stats
from design import kpi_card, section_header

import pages.dashboard_tab    as tab_dash
import pages.profit_tab       as tab_profit
import pages.ai_studio_tab    as tab_ai
import pages.strategy_tab     as tab_strategy
import pages.analytics_tab    as tab_analytics
import pages.fpa_tab          as tab_fpa
import pages.monthend_tab     as tab_monthend
import pages.cash_tab         as tab_cash
import pages.integrations_tab as tab_integrations
import pages.team_tab         as tab_team
import pages.advanced_tab     as tab_advanced
import pages.settings_tab     as tab_settings


def _render_sidebar():
    with st.sidebar:
        st.markdown(sidebar_header(), unsafe_allow_html=True)

        uname = st.session_state.user_full_name or st.session_state.username
        sub   = st.session_state.subscription
        sub_badge_color = "#10B981" if sub == "pro" else "#6B7280"
        st.markdown(f"""
        <div style="background:#1A1F2E;border:1px solid #252836;border-radius:12px;
                    padding:14px 16px;margin:8px 0 16px;">
          <div style="font-weight:700;color:#F0F2FF;font-size:14px;">{uname}</div>
          <div style="font-size:12px;color:#9CA3AF;">{st.session_state.user_email}</div>
          <div style="margin-top:6px;">
            <span style="background:{sub_badge_color}22;color:{sub_badge_color};
                         border:1px solid {sub_badge_color}55;border-radius:20px;
                         padding:2px 10px;font-size:11px;font-weight:700;
                         text-transform:uppercase;">{sub.title()}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**Upload Data**")
        uploaded = st.file_uploader(
            "CSV, Excel, JSON, Parquet",
            type=["csv","xlsx","xls","xlsm","json","parquet","tsv","feather"],
            label_visibility="collapsed",
        )

        if uploaded is not None:
            with st.spinner("Loading and cleaning data..."):
                df = load_file(uploaded)
            if df is not None:
                st.session_state.app_df = df
                stats = quick_stats(df)
                st.markdown(f"""
                <div style="background:#141720;border:1px solid #252836;
                            border-radius:12px;padding:14px 16px;margin-top:8px;">
                  <div style="font-size:11px;color:#6B7280;text-transform:uppercase;
                              letter-spacing:0.1em;margin-bottom:8px;">Dataset Loaded</div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                    <div><div style="font-size:11px;color:#9CA3AF;">Rows</div>
                         <div style="font-weight:700;color:#F0F2FF;">{stats['rows']:,}</div></div>
                    <div><div style="font-size:11px;color:#9CA3AF;">Cols</div>
                         <div style="font-weight:700;color:#F0F2FF;">{stats['cols']}</div></div>
                    <div><div style="font-size:11px;color:#9CA3AF;">Numeric</div>
                         <div style="font-weight:700;color:#F0F2FF;">{stats['numeric']}</div></div>
                    <div><div style="font-size:11px;color:#9CA3AF;">Missing</div>
                         <div style="font-weight:700;color:{'#EF4444' if stats['missing_pct']>5 else '#10B981'};">
                           {stats['missing_pct']}%</div></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
                st.success("Data ready!")

        if st.session_state.app_df is None:
            st.markdown(QUICK_START_GUIDE, unsafe_allow_html=True)

        if st.session_state.subscription != "pro":
            st.markdown("""
            <div style="background:linear-gradient(135deg,#6C63FF22,#0AEFFF22);
                        border:1px solid #6C63FF55;border-radius:12px;
                        padding:14px 16px;margin-top:16px;text-align:center;">
              <div style="font-size:12px;font-weight:700;color:#6C63FF;
                          text-transform:uppercase;letter-spacing:0.1em;">Upgrade to Pro</div>
              <div style="font-size:11px;color:#9CA3AF;margin:4px 0 8px;">
                Unlock all 12 modules
              </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Upgrade - from $49/mo", use_container_width=True):
                st.session_state["_jump_to_billing"] = True
                st.rerun()

        st.markdown("---")

        if st.button("Logout", use_container_width=True):
            from database import AuditRepo, SessionRepo
            AuditRepo.log(st.session_state.user_id, "logout",
                          f"{st.session_state.username} logged out")
            tok = st.session_state.get("session_token")
            if tok:
                SessionRepo.delete(tok)
            try:
                st.query_params.clear()
            except Exception:
                pass
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.markdown("""
        <div style="text-align:center;padding:16px 0 4px;color:#374151;font-size:11px;">
          LionsylAI v2.1 &middot; &copy; 2026<br/>
          <a href="https://docs.lionsylai.com" style="color:#6C63FF;text-decoration:none;">Docs</a> &middot;
          <a href="mailto:support@lionsylai.com" style="color:#6C63FF;text-decoration:none;">Support</a>
        </div>
        """, unsafe_allow_html=True)


_render_sidebar()

if st.session_state.get("_real_identity"):
    real = st.session_state["_real_identity"]
    bcol, xcol = st.columns([5, 1])
    with bcol:
        st.markdown(f"""
        <div style="background:linear-gradient(90deg,#F59E0B22,#F59E0B0D);border:1px solid #F59E0B55;
                    border-radius:10px;padding:10px 18px;margin-bottom:8px;height:100%;
                    display:flex;align-items:center;">
          <span style="color:#F59E0B;font-size:13px;font-weight:600;">
            &#128065; Viewing as <strong>{st.session_state.get('user_full_name') or st.session_state.get('username')}</strong>
            ({st.session_state.get('team_role')}) &mdash; you're really
            {real.get('user_full_name') or real.get('username')}
          </span>
        </div>
        """, unsafe_allow_html=True)
    with xcol:
        if st.button("Exit", key="exit_impersonation", use_container_width=True):
            tab_team.stop_impersonation()
            st.rerun()

df = st.session_state.get("app_df")

st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:0 0 20px;border-bottom:1px solid #252836;margin-bottom:24px;">
  <div>
    <h1 style="font-family:'Space Grotesk',sans-serif;font-size:28px;font-weight:900;
               background:linear-gradient(90deg,#fff,#9CA3AF);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;
               background-clip:text;margin:0;">LionsylAI</h1>
    <p style="color:#6B7280;font-size:13px;margin:2px 0 0;">
      Enterprise Analytics Intelligence &middot; {'Data Loaded' if df is not None else 'Upload data to begin'}
    </p>
  </div>
  <div style="text-align:right;">
    <div style="font-size:12px;color:#9CA3AF;">{st.session_state.user_full_name or st.session_state.username}</div>
    <div style="font-size:11px;color:#6B7280;">
      {'Pro' if st.session_state.subscription=='pro' else 'Free'}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

if df is None:
    st.markdown(WELCOME_HEADER, unsafe_allow_html=True)
    st.markdown(STATS_GRID, unsafe_allow_html=True)
    st.markdown(FEATURE_GRID, unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center;padding:24px 0;">
      <p style="color:#9CA3AF;font-size:16px;">
        Upload your data in the sidebar to unlock all 12 analytics modules
      </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

tabs = st.tabs([
    "Dashboard", "Profit", "AI Studio", "Strategy",
    "Analytics", "FP&A", "Month-End", "Cash",
    "Integrations", "Team", "Advanced", "Settings",
])

with tabs[0]:  tab_dash.render(df)
with tabs[1]:  tab_profit.render(df)
with tabs[2]:  tab_ai.render(df)
with tabs[3]:  tab_strategy.render(df)
with tabs[4]:  tab_analytics.render(df)
with tabs[5]:  tab_fpa.render(df)
with tabs[6]:  tab_monthend.render(df)
with tabs[7]:  tab_cash.render(df)
with tabs[8]:  tab_integrations.render()
with tabs[9]:  tab_team.render()
with tabs[10]: tab_advanced.render(df)
with tabs[11]: tab_settings.render()
