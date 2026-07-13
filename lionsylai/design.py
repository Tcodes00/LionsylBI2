"""
LionsylAI – Design System 2026
Dark-first, violet-cyan accent palette by default. The accent colors below
are driven by Settings -> Preferences -> Chart colour palette, so picking a
different palette re-themes the whole app (buttons, active tabs, borders,
glows) - not just the charts on the Dashboard.
"""
import streamlit as st

# Accent roles per palette choice. "LionsylAI (default)" reproduces the
# original violet-cyan look exactly, so anyone who never touches this
# preference sees no change at all.
_THEME_COLORS = {
    "LionsylAI (default)": {"primary": "#6C63FF", "light": "#8B84FF", "cyan": "#0AEFFF", "accent": "#FF6B6B"},
    "Viridis": {"primary": "#35B779", "light": "#6FDD9B", "cyan": "#26828E", "accent": "#FDE725"},
    "Plasma":  {"primary": "#CC4778", "light": "#F1844B", "cyan": "#9C179E", "accent": "#F0F921"},
    "Inferno": {"primary": "#BB3754", "light": "#F98C0A", "cyan": "#781C6D", "accent": "#FCFFA4"},
    "Blues":   {"primary": "#2171B5", "light": "#6BAED6", "cyan": "#4292C6", "accent": "#08589E"},
}


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"


def theme() -> dict:
    """The active accent colors, resolved from the current session's saved
    chart palette preference (falls back to the original default)."""
    key = st.session_state.get("pref_palette", "LionsylAI (default)")
    return _THEME_COLORS.get(key, _THEME_COLORS["LionsylAI (default)"])


# ─────────────────────────────────────────────────────────────
# CUSTOM CSS – injected fresh on every rerun, so it always reflects
# whatever palette is currently selected.
# ─────────────────────────────────────────────────────────────
def custom_css() -> str:
    t = theme()
    rgb = _hex_to_rgb(t["primary"])
    return f"""
<style>
/* ── Google Fonts ─────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@400;500;600;700&display=swap');

/* ── CSS Variables ─────────────────────────────────────── */
:root {{
  --bg-base:      #0D0F14;
  --bg-card:      #141720;
  --bg-hover:     #1A1F2E;
  --border:       #252836;
  --border-glow:  {t["primary"]}55;
  --primary:      {t["primary"]};
  --primary-light:{t["light"]};
  --cyan:         {t["cyan"]};
  --accent:       {t["accent"]};
  --success:      #10B981;
  --warning:      #F59E0B;
  --danger:       #EF4444;
  --text-primary: #F0F2FF;
  --text-secondary:#9CA3AF;
  --text-muted:   #6B7280;
  --gradient-1:   linear-gradient(135deg, {t["primary"]} 0%, {t["cyan"]} 100%);
  --gradient-2:   linear-gradient(135deg, {t["accent"]} 0%, #F59E0B 100%);
  --gradient-3:   linear-gradient(135deg, #10B981 0%, {t["cyan"]} 100%);
  --shadow-glow:  0 0 24px rgba({rgb}, 0.25);
  --radius-card:  16px;
  --radius-btn:   10px;
  --font-main:    'Inter', sans-serif;
  --font-display: 'Space Grotesk', sans-serif;
}}

/* ── Global Reset ─────────────────────────────────────── */
* {{ box-sizing: border-box; }}

.stApp {{
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: var(--font-main);
}}

/* ── Hide Streamlit chrome ────────────────────────────── */
#MainMenu, footer, header {{ visibility: hidden !important; }}
.stDeployButton {{ display: none !important; }}

/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebar"] {{
  background: var(--bg-card) !important;
  border-right: 1px solid var(--border) !important;
}}
[data-testid="stSidebar"] * {{ color: var(--text-primary) !important; }}

/* ── Buttons ──────────────────────────────────────────── */
.stButton > button {{
  border-radius: var(--radius-btn) !important;
  font-weight: 600 !important;
  font-family: var(--font-main) !important;
  transition: all 0.2s ease !important;
  border: 1px solid var(--border) !important;
  background: var(--bg-hover) !important;
  color: var(--text-primary) !important;
}}
.stButton > button:hover {{
  background: var(--primary) !important;
  border-color: var(--primary) !important;
  transform: translateY(-1px);
  box-shadow: var(--shadow-glow) !important;
}}
.stButton > button[kind="primary"] {{
  background: var(--gradient-1) !important;
  border: none !important;
  color: #fff !important;
  box-shadow: 0 4px 20px rgba(108, 99, 255, 0.4) !important;
}}
.stButton > button[kind="primary"]:hover {{
  filter: brightness(1.1) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 30px rgba(108, 99, 255, 0.5) !important;
}}

/* ── Inputs ───────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > select,
.stNumberInput > div > div > input {{
  background: var(--bg-hover) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-btn) !important;
  color: var(--text-primary) !important;
  font-family: var(--font-main) !important;
}}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {{
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.15) !important;
}}

/* ── Metrics ──────────────────────────────────────────── */
[data-testid="stMetric"] {{
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-card) !important;
  padding: 1.2rem 1.4rem !important;
  transition: border-color 0.2s;
}}
[data-testid="stMetric"]:hover {{ border-color: var(--primary) !important; }}
[data-testid="stMetricLabel"] > div {{ color: var(--text-secondary) !important; font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.08em; }}
[data-testid="stMetricValue"] > div {{ color: var(--text-primary) !important; font-size: 1.6rem !important; font-weight: 700 !important; font-family: var(--font-display) !important; }}

/* ── Tabs ─────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
  background: var(--bg-card) !important;
  border-radius: var(--radius-card) !important;
  padding: 6px !important;
  gap: 4px !important;
  border: 1px solid var(--border) !important;
  flex-wrap: wrap !important;
}}
.stTabs [data-baseweb="tab"] {{
  border-radius: 10px !important;
  color: var(--text-secondary) !important;
  font-weight: 500 !important;
  font-size: 0.82rem !important;
  padding: 8px 14px !important;
  transition: all 0.2s !important;
  white-space: nowrap !important;
}}
.stTabs [aria-selected="true"] {{
  background: var(--gradient-1) !important;
  color: #fff !important;
  font-weight: 700 !important;
  box-shadow: 0 2px 12px rgba(108,99,255,0.4) !important;
}}

/* ── DataFrames ──────────────────────────────────────── */
[data-testid="stDataFrameContainer"] {{
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-card) !important;
  overflow: hidden !important;
}}

/* ── Expander ─────────────────────────────────────────── */
.streamlit-expanderHeader {{
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-card) !important;
  color: var(--text-primary) !important;
  font-weight: 600 !important;
}}

/* ── Alerts ───────────────────────────────────────────── */
.stAlert {{ border-radius: var(--radius-card) !important; }}

/* ── Sliders ──────────────────────────────────────────── */
[data-testid="stSlider"] > div > div > div > div {{
  background: var(--gradient-1) !important;
}}

/* ── Progress bar ─────────────────────────────────────── */
.stProgress > div > div > div > div {{
  background: var(--gradient-1) !important;
}}

/* ── File uploader ────────────────────────────────────── */
[data-testid="stFileUploader"] > div {{
  background: var(--bg-hover) !important;
  border: 2px dashed var(--border-glow) !important;
  border-radius: var(--radius-card) !important;
  color: var(--text-primary) !important;
}}
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] p,
[data-testid="stFileUploader"] span {{ color: var(--text-primary) !important; }}

/* ── Checkboxes ───────────────────────────────────────── */
label[data-testid="stCheckbox"] > span {{ color: var(--text-primary) !important; }}

/* ── Labels / markdown headings ──────────────────────── */
h1, h2, h3, h4, h5, h6 {{ color: var(--text-primary) !important; font-family: var(--font-display) !important; }}
p, span, li, td, th {{ color: var(--text-primary) !important; }}
label {{ color: var(--text-secondary) !important; font-size: 0.83rem !important; font-weight: 500 !important; }}

/* ── Scrollbar ────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: var(--bg-base); }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--primary); }}

/* ── Plotly charts ────────────────────────────────────── */
.js-plotly-plot .plotly .bg {{ fill: transparent !important; }}
</style>
"""

# ─────────────────────────────────────────────────────────────
# Component HTML snippets
# ─────────────────────────────────────────────────────────────

def sidebar_header() -> str:
    t = theme()
    return f"""
<div style="padding:24px 8px 16px;text-align:center;">
  <div style="font-size:42px;margin-bottom:4px;">🦁</div>
  <div style="font-family:'Space Grotesk',sans-serif;font-size:20px;font-weight:800;
              background:linear-gradient(90deg,{t["primary"]},{t["cyan"]});
              -webkit-background-clip:text;-webkit-text-fill-color:transparent;
              background-clip:text;">LionsylAI</div>
  <div style="font-size:11px;color:#6B7280;letter-spacing:0.12em;text-transform:uppercase;
              margin-top:2px;">Enterprise Analytics</div>
</div>
"""

def kpi_card(label: str, value: str, delta: str = "", icon: str = "📊",
             gradient: str = "var(--gradient-1)") -> str:
    delta_html = ""
    if delta:
        color = "#10B981" if not delta.startswith("-") else "#EF4444"
        arrow = "↑" if not delta.startswith("-") else "↓"
        delta_html = (f'<div style="font-size:12px;color:{color};font-weight:600;'
                      f'margin-top:4px;">{arrow} {delta}</div>')
    return f"""
<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-card);
            padding:22px 20px;transition:all 0.2s;position:relative;overflow:hidden;">
  <div style="position:absolute;top:0;left:0;right:0;height:3px;background:{gradient};"></div>
  <div style="font-size:28px;margin-bottom:8px;">{icon}</div>
  <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.1em;
              font-weight:600;">{label}</div>
  <div style="font-size:26px;font-weight:800;color:var(--text-primary);font-family:'Space Grotesk',sans-serif;
              margin-top:4px;">{value}</div>
  {delta_html}
</div>
"""

def insight_card(text: str, border_color: str = "var(--primary)") -> str:
    return f"""
<div style="background:var(--bg-card);border-left:4px solid {border_color};
            border-radius:0 12px 12px 0;padding:14px 18px;margin:8px 0;
            line-height:1.6;color:var(--text-primary);font-size:14px;">
  {text}
</div>
"""

def badge(text: str, color: str = None) -> str:
    color = color or theme()["primary"]
    return (f'<span style="background:{color}22;color:{color};border:1px solid {color}66;'
            f'border-radius:20px;padding:2px 10px;font-size:11px;font-weight:700;'
            f'letter-spacing:0.06em;text-transform:uppercase;">{text}</span>')

def section_header(title: str, subtitle: str = "") -> str:
    sub_html = (f'<p style="color:var(--text-secondary);font-size:14px;margin:4px 0 0;">'
                f'{subtitle}</p>') if subtitle else ""
    return f"""
<div style="margin-bottom:24px;">
  <h2 style="font-family:'Space Grotesk',sans-serif;font-size:24px;font-weight:700;
             background:linear-gradient(90deg,#fff,#9CA3AF);
             -webkit-background-clip:text;-webkit-text-fill-color:transparent;
             background-clip:text;margin:0;">{title}</h2>
  {sub_html}
</div>
"""

WELCOME_HEADER = """
<div style="text-align:center;padding:60px 20px 40px;">
  <div style="display:inline-block;background:linear-gradient(135deg,#6C63FF22,#0AEFFF22);
              border:1px solid #6C63FF55;border-radius:24px;padding:12px 28px;
              font-size:13px;font-weight:700;color:#0AEFFF;letter-spacing:2px;
              text-transform:uppercase;margin-bottom:24px;">
    Enterprise Analytics Intelligence Platform
  </div>
  <h1 style="font-family:'Space Grotesk',sans-serif;font-size:52px;font-weight:900;
             line-height:1.1;color:#fff;margin:0 0 20px;">
    Turn Data Into<br/>
    <span style="background:linear-gradient(90deg,#6C63FF,#0AEFFF);
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                 background-clip:text;">Competitive Edge</span>
  </h1>
  <p style="color:#9CA3AF;font-size:18px;max-width:560px;margin:0 auto 40px;line-height:1.7;">
    Upload your data, unlock AI-powered analytics, automate FP&amp;A,
    and get executive-grade insights in seconds.
  </p>
</div>
"""

STATS_GRID = """
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin:0 0 48px;">
  <div style="background:#141720;border:1px solid #252836;border-radius:16px;padding:24px;text-align:center;">
    <div style="font-size:36px;font-weight:900;background:linear-gradient(90deg,#6C63FF,#0AEFFF);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">12+</div>
    <div style="font-size:13px;color:#9CA3AF;margin-top:4px;">Analytics Modules</div>
  </div>
  <div style="background:#141720;border:1px solid #252836;border-radius:16px;padding:24px;text-align:center;">
    <div style="font-size:36px;font-weight:900;background:linear-gradient(90deg,#0AEFFF,#6C63FF);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">AI</div>
    <div style="font-size:13px;color:#9CA3AF;margin-top:4px;">Powered Predictions</div>
  </div>
  <div style="background:#141720;border:1px solid #252836;border-radius:16px;padding:24px;text-align:center;">
    <div style="font-size:36px;font-weight:900;background:linear-gradient(90deg,#10B981,#0AEFFF);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">99%</div>
    <div style="font-size:13px;color:#9CA3AF;margin-top:4px;">Uptime SLA</div>
  </div>
  <div style="background:#141720;border:1px solid #252836;border-radius:16px;padding:24px;text-align:center;">
    <div style="font-size:36px;font-weight:900;background:linear-gradient(90deg,#F59E0B,#FF6B6B);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">∞</div>
    <div style="font-size:13px;color:#9CA3AF;margin-top:4px;">Data Sources</div>
  </div>
</div>
"""

FEATURE_GRID = """
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:48px;">
  <div style="background:#141720;border:1px solid #252836;border-radius:16px;padding:28px;">
    <div style="font-size:32px;margin-bottom:12px;">📊</div>
    <h3 style="font-family:'Space Grotesk',sans-serif;font-size:17px;font-weight:700;
               color:#fff;margin:0 0 8px;">Business Intelligence</h3>
    <p style="color:#9CA3AF;font-size:14px;margin:0;line-height:1.6;">
      Real-time dashboards, correlation analysis, and multi-variable visualizations.
    </p>
  </div>
  <div style="background:#141720;border:1px solid #252836;border-radius:16px;padding:28px;">
    <div style="font-size:32px;margin-bottom:12px;">🤖</div>
    <h3 style="font-family:'Space Grotesk',sans-serif;font-size:17px;font-weight:700;
               color:#fff;margin:0 0 8px;">AI Predictions</h3>
    <p style="color:#9CA3AF;font-size:14px;margin:0;line-height:1.6;">
      XGBoost, LightGBM, Random Forest, SARIMA, and Monte Carlo forecasting.
    </p>
  </div>
  <div style="background:#141720;border:1px solid #252836;border-radius:16px;padding:28px;">
    <div style="font-size:32px;margin-bottom:12px;">🏦</div>
    <h3 style="font-family:'Space Grotesk',sans-serif;font-size:17px;font-weight:700;
               color:#fff;margin:0 0 8px;">FP&amp;A Automation</h3>
    <p style="color:#9CA3AF;font-size:14px;margin:0;line-height:1.6;">
      Budget management, month-end close, cash flow forecasting, and reporting.
    </p>
  </div>
  <div style="background:#141720;border:1px solid #252836;border-radius:16px;padding:28px;">
    <div style="font-size:32px;margin-bottom:12px;">🎯</div>
    <h3 style="font-family:'Space Grotesk',sans-serif;font-size:17px;font-weight:700;
               color:#fff;margin:0 0 8px;">Strategic Insights</h3>
    <p style="color:#9CA3AF;font-size:14px;margin:0;line-height:1.6;">
      Auto-generated profitability, growth, risk, and operational recommendations.
    </p>
  </div>
  <div style="background:#141720;border:1px solid #252836;border-radius:16px;padding:28px;">
    <div style="font-size:32px;margin-bottom:12px;">👥</div>
    <h3 style="font-family:'Space Grotesk',sans-serif;font-size:17px;font-weight:700;
               color:#fff;margin:0 0 8px;">Team Collaboration</h3>
    <p style="color:#9CA3AF;font-size:14px;margin:0;line-height:1.6;">
      Share reports, role-based access, comments, notifications, and audit trails.
    </p>
  </div>
  <div style="background:#141720;border:1px solid #252836;border-radius:16px;padding:28px;">
    <div style="font-size:32px;margin-bottom:12px;">🔗</div>
    <h3 style="font-family:'Space Grotesk',sans-serif;font-size:17px;font-weight:700;
               color:#fff;margin:0 0 8px;">Enterprise Integrations</h3>
    <p style="color:#9CA3AF;font-size:14px;margin:0;line-height:1.6;">
      ERP, CRM, Banking APIs, and custom REST connections — all managed in one place.
    </p>
  </div>
</div>
"""

QUICK_START_GUIDE = """
<div style="background:#141720;border:1px solid #252836;border-radius:16px;padding:20px;margin-top:16px;">
  <div style="font-size:13px;font-weight:700;color:#6C63FF;letter-spacing:0.1em;
              text-transform:uppercase;margin-bottom:12px;">Quick Start</div>
  <div style="font-size:13px;color:#9CA3AF;line-height:2;">
    1. Upload a CSV or Excel file above<br/>
    2. Insights generate automatically<br/>
    3. Explore all 12 analytics tabs<br/>
    4. Export reports with one click
  </div>
</div>
"""
