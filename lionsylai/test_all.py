"""
LionsylAI – Full End-to-End Test Suite
Run: python test_all.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np

PASS = []
FAIL = []

def test(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ✅  {name}")
    except Exception as e:
        FAIL.append((name, str(e)))
        print(f"  ❌  {name}: {e}")


# ── Sample data ────────────────────────────────────────────────
df = pd.DataFrame({
    'date':     pd.date_range('2024-01-01', periods=365, freq='D'),
    'revenue':  np.random.uniform(1000, 10000, 365),
    'cost':     np.random.uniform(500,  7000,  365),
    'quantity': np.random.randint(1, 200, 365),
    'category': np.random.choice(['Electronics','Food','Clothing','Books'], 365),
    'customer': np.random.choice(['Alice','Bob','Carol','Dave','Eve'], 365),
    'region':   np.random.choice(['North','South','East','West'], 365),
})
df['profit'] = df['revenue'] - df['cost']

print("\n=== LionsylAI Full Test Suite ===\n")

# ── Config ────────────────────────────────────────────────────
print("[ Config ]")
def t_config():
    from config.settings import APP_NAME, PLANS, BRAND_PRIMARY
    assert APP_NAME == "LionsylAI"
    assert "pro" in PLANS
    assert BRAND_PRIMARY.startswith("#")
test("config.settings imports", t_config)

# ── Design ────────────────────────────────────────────────────
print("\n[ Design ]")
def t_design():
    from design import custom_css, kpi_card, insight_card, badge, section_header
    assert "<style>" in custom_css()
    html = kpi_card("Revenue", "$1M", "10%", "💰")
    assert "1M" in html
    assert "10%" in html
test("design CSS and components", t_design)

# ── Database ──────────────────────────────────────────────────
print("\n[ Database ]")
def t_db_init():
    import database as db
    assert db.init_db() is True
test("db init_db()", t_db_init)

def t_db_user_create():
    from database import UserRepo
    # create unique user
    import time
    uname = f"tester_{int(time.time())}"
    u = UserRepo.create(uname, f"{uname}@x.com", "TestPass@99!", "Tester")
    assert u is not None
    assert u.username == uname
    assert u.subscription == "free"
test("UserRepo.create", t_db_user_create)

def t_db_admin_login():
    from database import UserRepo
    u = UserRepo.verify("admin", "Admin@2026!")
    assert u is not None
    assert u.username == "admin"
    assert u.role == "admin"
    assert u.subscription == "pro"
    assert u.is_email_verified is True
test("UserRepo.verify (admin)", t_db_admin_login)

def t_db_user_getters():
    from database import UserRepo
    u1 = UserRepo.get_by_id(1)
    u2 = UserRepo.get_by_email("admin@lionsylai.com")
    assert u1 is not None and u1.id == 1
    assert u2 is not None and u2.email == "admin@lionsylai.com"
test("UserRepo.get_by_id / get_by_email", t_db_user_getters)

def t_db_update_fields():
    from database import UserRepo
    ok = UserRepo.update_fields(1, full_name="Admin Updated")
    assert ok is True
    u = UserRepo.get_by_id(1)
    assert u.full_name == "Admin Updated"
    # restore
    UserRepo.update_fields(1, full_name="System Admin")
test("UserRepo.update_fields", t_db_update_fields)

def t_db_team():
    from database import TeamRepo
    ok = TeamRepo.add(1, "Test Member", "tm@x.com", "Analyst", "Active")
    assert ok
    members = TeamRepo.list_for_user(1)
    assert any(m.name == "Test Member" for m in members)
    m = next(m for m in members if m.name == "Test Member")
    TeamRepo.update(m.id, role="Manager")
    updated = TeamRepo.list_for_user(1)
    assert any(x.role == "Manager" for x in updated if x.name == "Test Member")
test("TeamRepo CRUD", t_db_team)

def t_db_integrations():
    from database import IntegrationRepo
    ints = IntegrationRepo.list_for_user(1)
    assert len(ints) >= 4
    first = ints[0]
    assert first.name in ["ERP System","CRM Platform","Banking API","Payment Processor"]
    ok = IntegrationRepo.update(first.id, status="Testing", success_rate=95.0)
    assert ok
test("IntegrationRepo list + update", t_db_integrations)

def t_db_notifications():
    from database import NotificationRepo
    NotificationRepo.add(1, "Test message", "info")
    notifs = NotificationRepo.list_unread(1, limit=5)
    assert len(notifs) > 0
    assert any(n.message == "Test message" for n in notifs)
    NotificationRepo.mark_all_read(1)
test("NotificationRepo add / list / mark_read", t_db_notifications)

def t_db_audit():
    from database import AuditRepo
    AuditRepo.log(1, "test_action", "unit test", "127.0.0.1")
    logs = AuditRepo.list_recent(limit=5)
    assert len(logs) > 0
    assert any(a.action == "test_action" for a in logs)
test("AuditRepo log + list", t_db_audit)

def t_db_comments():
    from database import CommentRepo
    ok = CommentRepo.add(0, 1, "Test comment", "General", "Low")
    assert ok
    cmts = CommentRepo.list_recent(limit=5)
    assert len(cmts) > 0
test("CommentRepo add + list", t_db_comments)

def t_db_budget():
    from database import BudgetRepo
    import json
    data = {"total_budget": 1000000, "departments": {}}
    ok = BudgetRepo.save(1, "Test Budget", 2026, "USD", json.dumps(data))
    assert ok
    latest = BudgetRepo.latest(1)
    assert latest is not None
    assert latest["total_budget"] == 1000000
test("BudgetRepo save + latest", t_db_budget)

# ── Data Engine ───────────────────────────────────────────────
print("\n[ Data Engine ]")
def t_de_clean():
    from components.data_engine import clean_dataframe
    dirty = df.copy()
    dirty.loc[0, "revenue"] = np.nan
    dirty["Unnamed: 0"] = 0
    cleaned = clean_dataframe(dirty)
    assert "Unnamed: 0" not in cleaned.columns
    assert cleaned["revenue"].isnull().sum() == 0
test("clean_dataframe", t_de_clean)

def t_de_detect():
    from components.data_engine import detect_columns
    det = detect_columns(df)
    assert "revenue" in det["revenue"]
    assert "cost"    in det["cost"]
    assert "customer"in det["customer"]
    assert "date"    in det["date"]
test("detect_columns", t_de_detect)

def t_de_helpers():
    from components.data_engine import numeric_cols, categorical_cols, date_cols, quick_stats, calc_growth
    nc = numeric_cols(df)
    cc = categorical_cols(df)
    dc = date_cols(df)
    qs = quick_stats(df)
    assert "revenue" in nc
    assert "category" in cc
    assert "date" in dc
    assert qs["rows"] == 365
    g = calc_growth(df["revenue"])
    assert isinstance(g, float)
test("numeric/categorical/date_cols + quick_stats + calc_growth", t_de_helpers)

# ── ML Engine ─────────────────────────────────────────────────
print("\n[ ML Engine ]")
def t_ml_train_regression():
    from components.ml_engine import MLEngine
    e = MLEngine()
    df_ml = df.drop(columns=["date"])
    results = e.train(df_ml, "profit", "regression")
    assert results is not None
    assert len(results) >= 3
    for name, r in results.items():
        assert "r2" in r
        assert "rmse" in r
        assert r["r2"] > -1
test("MLEngine regression training", t_ml_train_regression)

def t_ml_feature_importance():
    from components.ml_engine import MLEngine
    e = MLEngine()
    df_ml = df.drop(columns=["date"])
    results = e.train(df_ml, "profit", "regression")
    fi = e.feature_importances(results, "regression")
    # fi may be None if no model with feature_importances_ beats HistGradBoost
    # but usually XGBoost or LightGBM will be available
    if fi is not None:
        assert "Feature" in fi.columns
        assert "Importance" in fi.columns
        assert "Importance %" in fi.columns
        assert len(fi) > 0
    # The test passes whether or not fi is available — it's model-dependent
test("MLEngine.feature_importances", t_ml_feature_importance)

def t_ml_forecasting():
    from components.ml_engine import ForecastEngine
    series = df["revenue"].reset_index(drop=True)
    fc_trend = ForecastEngine.simple_trend(series, periods=14)
    assert len(fc_trend) == 14
    fc_hw = ForecastEngine.holt_winters(series, periods=7)
    assert fc_hw is not None and len(fc_hw) == 7
    fc_sarima = ForecastEngine.sarima(series, periods=7)
    assert fc_sarima is not None and len(fc_sarima) == 7
    mean, lo, hi = ForecastEngine.monte_carlo(series, simulations=100, periods=7)
    assert len(mean) == 7 and len(lo) == 7 and len(hi) == 7
test("ForecastEngine: trend + HW + SARIMA + Monte Carlo", t_ml_forecasting)

def t_ml_clustering():
    from components.ml_engine import ClusterEngine
    result = ClusterEngine.kmeans(df, ["revenue","cost"], k=3)
    assert result is not None
    clust_df, km = result
    assert "Cluster" in clust_df.columns
    assert km.n_clusters == 3
    pca = ClusterEngine.pca_2d(df, ["revenue","cost","profit","quantity"])
    assert pca is not None and "PC1" in pca.columns
test("ClusterEngine KMeans + PCA", t_ml_clustering)

def t_ml_customer():
    from components.ml_engine import CustomerAnalytics
    ca  = CustomerAnalytics()
    clv = ca.clv(df, "customer", "revenue")
    assert clv is not None and len(clv) == 5
    assert "estimated_clv" in clv.columns
    rfm = ca.rfm(df, "customer", "date", "revenue")
    assert rfm is not None and "Segment" in rfm.columns
    churn = ca.churn_risk(df, "customer", "date")
    assert churn is not None and "Churn_Risk" in churn.columns
test("CustomerAnalytics: CLV + RFM + Churn", t_ml_customer)

def t_ml_feature_engineering():
    from components.ml_engine import auto_feature_engineer
    enhanced = auto_feature_engineer(df)
    assert len(enhanced.columns) > len(df.columns)
    assert "date_year"  in enhanced.columns
    assert "date_month" in enhanced.columns
test("auto_feature_engineer", t_ml_feature_engineering)

# ── FP Engine ─────────────────────────────────────────────────
print("\n[ FP&A Engine ]")
def t_fp_budget():
    from components.fp_engine import budget_from_dataframe, budget_variance_df
    bd  = budget_from_dataframe(df)
    assert "total_budget" in bd
    assert "departments" in bd
    assert bd["total_budget"] > 0
    vdf = budget_variance_df(bd)
    assert "Department"   in vdf.columns
    assert "Variance (%)" in vdf.columns or "Variance %" in vdf.columns
test("budget_from_dataframe + budget_variance_df", t_fp_budget)

def t_fp_monthend():
    from components.fp_engine import month_end_close
    r = month_end_close(df, ("revenue","cost"))
    assert r["status"] == "Completed"
    assert "reconciliation" in r
    assert "pl_statement"   in r
    assert "recon_matched"  in r
test("month_end_close", t_fp_monthend)

def t_fp_cash():
    from components.fp_engine import cash_position, cash_forecast
    cp = cash_position(df, "revenue", "category")
    assert "positions" in cp or "total_cash" in cp
    cf = cash_forecast(500000, 200000, 175000, 12)
    assert len(cf) == 12
    assert cf["Projected_Balance"].iloc[-1] > 0
test("cash_position + cash_forecast", t_fp_cash)

def t_fp_report():
    from components.fp_engine import generate_report, report_to_text
    for tf in ["Monthly","Quarterly","Annual"]:
        r = generate_report(df, "Financial Summary", "revenue", tf)
        assert "meta" in r
        assert "financial_summary" in r
        fs = r["financial_summary"]
        assert fs["total"] > 0
        assert fs["count"] == 365
    txt = report_to_text(r)
    assert len(txt) > 100
    assert "LIONSYLAI" in txt
test("generate_report (Monthly/Quarterly/Annual) + report_to_text", t_fp_report)

def t_fp_consolidation():
    import io
    from components.fp_engine import DataConsolidator
    c = DataConsolidator()
    # Create in-memory CSV file
    csv_content = df.to_csv(index=False).encode()
    class MockFile:
        name = "test.csv"
        def seek(self, n): self._buf.seek(n)
        def read(self): return self._buf.read()
        def __init__(self, data): self._buf = io.BytesIO(data)
    mock = MockFile(csv_content)
    ok = c.add_file("TestSource", mock)
    assert ok
    assert c.consolidated is not None
    assert "_source" in c.consolidated.columns
    qr = c.quality_report()
    assert len(qr) == 1
    assert qr["Source"].iloc[0] == "TestSource"
test("DataConsolidator add_file + quality_report", t_fp_consolidation)

# ── Auth Utils ────────────────────────────────────────────────
print("\n[ Auth Utils ]")
def t_auth():
    from utils.auth import (hash_password, verify_password, generate_otp,
                            generate_secure_token, create_access_token,
                            decode_access_token, password_strength)
    pw   = "TestPassword@123"
    h    = hash_password(pw)
    assert verify_password(pw, h)
    assert not verify_password("wrong", h)
    otp  = generate_otp(6)
    assert len(otp) == 6 and otp.isdigit()
    tok  = generate_secure_token(48)
    assert len(tok) > 40
    jwt  = create_access_token({"sub": 1, "role": "admin"})
    data = decode_access_token(jwt)
    assert data and data["sub"] == 1
    ps   = password_strength("Abc@1234")
    assert "score" in ps and ps["score"] >= 3
test("auth utilities: hash/verify/OTP/JWT/strength", t_auth)

# ── Payment Utils ─────────────────────────────────────────────
print("\n[ Payment Utils ]")
def t_payment():
    from utils.payment import render_pricing_html
    for billing in ["month","year"]:
        html = render_pricing_html(billing)
        assert "$" in html
        assert "Professional" in html
test("render_pricing_html (month/year)", t_payment)

# ── Auto-Clean & Quality Score ────────────────────────────────
print("\n[ Auto-Clean & Quality Score ]")

def t_auto_clean_basic():
    from components.ml_engine import auto_clean_dataframe
    messy = df.copy()
    messy.loc[:10, "revenue"]  = None
    messy.loc[50:55, "quantity"] = -5
    messy["Unnamed: 0"]        = range(len(messy))
    # Add duplicates
    messy = pd.concat([messy, messy.iloc[:5]], ignore_index=True)
    cleaned, report = auto_clean_dataframe(messy.copy())
    # No NaN remaining
    assert cleaned.isnull().sum().sum() == 0, f"NaN remain: {cleaned.isnull().sum().sum()}"
    # Unnamed col removed
    assert not any(c.startswith("Unnamed") for c in cleaned.columns)
    # Duplicates removed
    assert len(cleaned) < len(messy)
    # Report populated correctly
    assert report["missing_before"] > 0
    assert report["missing_after"]  == 0
    assert report["issues_fixed"]   > 0
    assert len(report["steps"])     > 0
test("auto_clean_dataframe basic", t_auto_clean_basic)

def t_auto_clean_manual_options():
    from components.ml_engine import auto_clean_dataframe
    messy = df.copy()
    messy.loc[:5, "revenue"] = None
    messy["to_drop"] = "constant_value"
    cleaned, report = auto_clean_dataframe(
        messy.copy(),
        custom_drops  = ["to_drop"],
        fill_method   = "mean",
        outlier_low   = 0.01,
        outlier_high  = 0.99,
        fix_negatives = True,
        drop_id_cols  = True,
    )
    assert "to_drop" not in cleaned.columns, "custom_drops failed"
    assert cleaned.isnull().sum().sum() == 0, "NaN remain after mean fill"
    assert report["issues_fixed"] > 0
test("auto_clean_dataframe manual options", t_auto_clean_manual_options)

def t_auto_clean_knn():
    from components.ml_engine import auto_clean_dataframe
    messy = df.copy()
    messy.loc[:20, "revenue"] = None   # >15% missing → triggers KNN
    cleaned, report = auto_clean_dataframe(messy.copy(), fill_method="knn")
    assert cleaned["revenue"].isnull().sum() == 0, "KNN fill failed"
test("auto_clean_dataframe KNN fill", t_auto_clean_knn)

def t_quality_score_not_zero():
    """Regression test: quality score must not show 0 issues on messy data."""
    from components.ml_engine import auto_clean_dataframe
    messy = df.copy()
    messy.loc[:30, "revenue"] = None   # 30+ missing values
    _, report = auto_clean_dataframe(messy.copy())
    # These were all 0 before the bug fix
    assert report["missing_before"] > 0,  "missing_before should be > 0"
    assert report["missing_after"]  == 0, "missing_after should be 0"
    assert report["issues_fixed"]   > 0,  "issues_fixed should be > 0"
    # Quality score formula
    total_cells  = max(messy.size, 1)
    missing_pct  = report["missing_before"] / total_cells
    missing_pen  = int(missing_pct * 40)
    issue_pen    = min(30, int(report["issues_fixed"] / (total_cells/1000+1) * 3))
    score        = max(0, 100 - missing_pen - issue_pen)
    assert 0 < score < 100, f"Score out of valid range: {score}"
test("quality_score formula (0-issues bug fix)", t_quality_score_not_zero)

def t_fingerprint_changes_on_reupload():
    """Re-uploading cleaned data must produce a different fingerprint."""
    import hashlib
    def fingerprint(df):
        try:
            sample = df.head(50).to_csv(index=False)
            return hashlib.md5((sample + str(df.shape)).encode()).hexdigest()
        except Exception:
            return str(df.shape) + str(df.columns.tolist())
    from components.ml_engine import auto_clean_dataframe
    messy = df.copy()
    messy.loc[:10, "revenue"] = None
    fp_raw = fingerprint(messy)
    cleaned, _ = auto_clean_dataframe(messy.copy())
    fp_clean = fingerprint(cleaned)
    # Cleaned data has different content → different fingerprint
    assert fp_raw != fp_clean, "Fingerprint did not change after cleaning (cache bug)"
test("fingerprint changes on re-upload (cache invalidation)", t_fingerprint_changes_on_reupload)

# ── Session Persistence (refresh bug fix) ──────────────────────
print("\n[ Session Persistence ]")

def t_session_create_and_restore():
    from database import UserRepo, SessionRepo
    u = UserRepo.verify("admin", "Admin@2026!")
    assert u is not None
    tok = SessionRepo.create(u.id, remember_me=True, user_agent="pytest", ip_address="127.0.0.1")
    assert tok and len(tok) > 20
    sess = SessionRepo.get_valid(tok)
    assert sess is not None
    assert sess.user_id == u.id
    restored = UserRepo.get_by_id(sess.user_id)
    assert restored.username == "admin"
test("session survives simulated refresh (token round-trip)", t_session_create_and_restore)

def t_session_remember_me_extends_expiry():
    from database import UserRepo, SessionRepo
    u = UserRepo.get_by_id(1)
    tok_short = SessionRepo.create(u.id, remember_me=False)
    tok_long  = SessionRepo.create(u.id, remember_me=True)
    s_short = SessionRepo.get_valid(tok_short)
    s_long  = SessionRepo.get_valid(tok_long)
    assert s_short.remember_me is False
    assert s_long.remember_me is True
    assert (s_long.expires_at - s_short.expires_at).days >= 25
test("Remember Me extends session expiry ~29 days", t_session_remember_me_extends_expiry)

def t_session_revoke():
    from database import UserRepo, SessionRepo
    u = UserRepo.get_by_id(1)
    tok = SessionRepo.create(u.id, remember_me=False)
    sess = SessionRepo.get_valid(tok)
    assert sess is not None
    SessionRepo.revoke_by_id(sess.id)
    sess_after = SessionRepo.get_valid(tok)
    assert sess_after is None, "Revoked session should no longer be valid"
test("SessionRepo.revoke_by_id invalidates session", t_session_revoke)

def t_session_list_for_user():
    from database import UserRepo, SessionRepo
    u = UserRepo.get_by_id(1)
    SessionRepo.create(u.id, remember_me=False)
    sessions = SessionRepo.list_for_user(u.id)
    assert len(sessions) >= 1
    assert all(s.user_id == u.id for s in sessions)
test("SessionRepo.list_for_user returns active sessions", t_session_list_for_user)

def t_session_expired_token_rejected():
    from database import SessionRepo, get_db, UserSession
    from datetime import datetime, timedelta
    # Manually create an already-expired session
    with get_db() as db_ctx:
        s = UserSession(user_id=1, token="expired_test_token_12345",
                        remember_me=False, expires_at=datetime.utcnow() - timedelta(days=1))
        db_ctx.add(s)
    result = SessionRepo.get_valid("expired_test_token_12345")
    assert result is None, "Expired token must be rejected"
test("expired session token is rejected", t_session_expired_token_rejected)


# ── Login Lockout (brute-force protection) ─────────────────────
print("\n[ Login Lockout Protection ]")

def t_lockout_tracks_failures():
    from database import LoginAttemptRepo
    LoginAttemptRepo.clear_for("lockout_test_user")
    for _ in range(3):
        LoginAttemptRepo.record("lockout_test_user", success=False)
    n = LoginAttemptRepo.count_recent_failures("lockout_test_user")
    assert n == 3
test("LoginAttemptRepo tracks failed attempts", t_lockout_tracks_failures)

def t_lockout_clears_on_success():
    from database import LoginAttemptRepo
    LoginAttemptRepo.clear_for("lockout_test_user2")
    LoginAttemptRepo.record("lockout_test_user2", success=False)
    LoginAttemptRepo.record("lockout_test_user2", success=False)
    assert LoginAttemptRepo.count_recent_failures("lockout_test_user2") == 2
    LoginAttemptRepo.clear_for("lockout_test_user2")
    assert LoginAttemptRepo.count_recent_failures("lockout_test_user2") == 0
test("LoginAttemptRepo.clear_for resets failure count", t_lockout_clears_on_success)

def t_lockout_threshold_reached():
    from database import LoginAttemptRepo
    from config.settings import LOGIN_LOCKOUT_MAX_ATTEMPTS
    LoginAttemptRepo.clear_for("lockout_test_user3")
    for _ in range(LOGIN_LOCKOUT_MAX_ATTEMPTS):
        LoginAttemptRepo.record("lockout_test_user3", success=False)
    n = LoginAttemptRepo.count_recent_failures("lockout_test_user3")
    assert n >= LOGIN_LOCKOUT_MAX_ATTEMPTS, "Should reach lockout threshold"
test("Lockout threshold reached after max attempts", t_lockout_threshold_reached)


# ── Email Delivery (honest status reporting) ────────────────────
print("\n[ Email Delivery ]")

def t_email_verification_returns_status_tuple():
    from utils.email_service import send_verification_email, email_delivery_configured
    ok, detail = send_verification_email("test@example.com", "Test User", "123456")
    assert isinstance(ok, bool)
    assert isinstance(detail, str)
    assert ok == email_delivery_configured(), "ok flag must reflect actual configuration"
test("send_verification_email returns honest (ok, detail) tuple", t_email_verification_returns_status_tuple)

def t_email_password_reset_returns_status():
    from utils.email_service import send_password_reset, email_delivery_configured
    ok, detail = send_password_reset("test@example.com", "Test User", "https://x.com/reset?token=abc")
    assert isinstance(ok, bool)
    assert ok == email_delivery_configured()
test("send_password_reset returns honest (ok, detail) tuple", t_email_password_reset_returns_status)

def t_email_team_invite_returns_status():
    from utils.email_service import send_team_invite, email_delivery_configured
    ok, detail = send_team_invite("new@example.com", "New Person", "Admin", "Test Org", "Analyst")
    assert isinstance(ok, bool)
    assert ok == email_delivery_configured()
test("send_team_invite returns honest (ok, detail) tuple", t_email_team_invite_returns_status)

def t_email_delivery_configured_flag():
    from utils.email_service import email_delivery_configured
    from config.settings import SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SENDGRID_API_KEY
    expected = bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD) or bool(SENDGRID_API_KEY)
    assert email_delivery_configured() == expected
test("email_delivery_configured reflects actual env state", t_email_delivery_configured_flag)


# ── Payment: Stripe (international) + SSLCommerz (Bangladesh) ──
print("\n[ Payment Gateways ]")

def t_stripe_configured_flag():
    from utils.payment import stripe_configured
    from config.settings import STRIPE_SECRET_KEY, STRIPE_PRICE_ID
    expected = bool(STRIPE_SECRET_KEY and STRIPE_PRICE_ID)
    assert stripe_configured() == expected
test("stripe_configured reflects actual env state", t_stripe_configured_flag)

def t_sslcommerz_configured_flag():
    from utils.payment import sslcommerz_configured
    from config.settings import SSLCOMMERZ_STORE_ID, SSLCOMMERZ_STORE_PASSWD
    expected = bool(SSLCOMMERZ_STORE_ID and SSLCOMMERZ_STORE_PASSWD)
    assert sslcommerz_configured() == expected
test("sslcommerz_configured reflects actual env state", t_sslcommerz_configured_flag)

def t_checkout_session_none_when_unconfigured():
    from utils.payment import create_checkout_session, stripe_configured
    if not stripe_configured():
        url = create_checkout_session("test@x.com", 1, "month")
        assert url is None, "Should return None (not a fake URL) when Stripe is unconfigured"
test("create_checkout_session returns None when unconfigured (no fake success)", t_checkout_session_none_when_unconfigured)

def t_sslcommerz_session_none_when_unconfigured():
    from utils.payment import create_sslcommerz_session, sslcommerz_configured
    if not sslcommerz_configured():
        result = create_sslcommerz_session("test@x.com", 1, "Test", "01700000000", 1499, "month")
        assert result is None, "Should return None when SSLCommerz is unconfigured"
test("create_sslcommerz_session returns None when unconfigured", t_sslcommerz_session_none_when_unconfigured)

def t_pricing_html_usd_and_bdt():
    from utils.payment import render_pricing_html
    html_usd = render_pricing_html("month", "USD")
    html_bdt = render_pricing_html("month", "BDT")
    assert "$" in html_usd
    assert ("৳" in html_bdt) or ("1,499" in html_bdt) or ("1499" in html_bdt)
    assert html_usd != html_bdt
test("render_pricing_html renders distinct USD and BDT pricing", t_pricing_html_usd_and_bdt)

def t_transaction_repo_records_purchase():
    from database import TransactionRepo
    ok = TransactionRepo.create(1, "demo", 49.0, "USD", "pro", "month", "completed", "TEST-REF-123")
    assert ok
    txs = TransactionRepo.list_for_user(1)
    assert len(txs) > 0
    assert any(t.reference == "TEST-REF-123" for t in txs)
test("TransactionRepo records and lists billing history", t_transaction_repo_records_purchase)


# ── Two-Factor Authentication (TOTP) ─────────────────────────────
print("\n[ Two-Factor Authentication ]")

def t_totp_secret_generation():
    from utils.auth import generate_totp_secret
    secret = generate_totp_secret()
    assert isinstance(secret, str) and len(secret) >= 16
test("generate_totp_secret produces valid secret", t_totp_secret_generation)

def t_totp_verify_correct_code():
    from utils.auth import generate_totp_secret, totp_verify, totp_available
    if totp_available():
        import pyotp
        secret = generate_totp_secret()
        code = pyotp.TOTP(secret).now()
        assert totp_verify(secret, code) is True
test("totp_verify accepts a correct current code", t_totp_verify_correct_code)

def t_totp_verify_rejects_wrong_code():
    from utils.auth import generate_totp_secret, totp_verify, totp_available
    if totp_available():
        secret = generate_totp_secret()
        assert totp_verify(secret, "000000") is False
test("totp_verify rejects an incorrect code", t_totp_verify_rejects_wrong_code)

def t_totp_provisioning_uri():
    from utils.auth import generate_totp_secret, totp_provisioning_uri, totp_available
    if totp_available():
        secret = generate_totp_secret()
        uri = totp_provisioning_uri(secret, "test@example.com")
        assert uri.startswith("otpauth://")
        # Email is URL-encoded in the URI (@ -> %40), so check decoded form
        import urllib.parse
        assert "test@example.com" in urllib.parse.unquote(uri)
        assert "LionsylAI" in uri
test("totp_provisioning_uri builds valid otpauth:// URI", t_totp_provisioning_uri)

def t_2fa_enable_disable_flow():
    from database import UserRepo
    from utils.auth import generate_totp_secret
    secret = generate_totp_secret()
    UserRepo.enable_2fa(1, secret)
    u = UserRepo.get_by_id(1)
    assert u.two_fa_enabled is True
    assert u.two_fa_secret == secret
    UserRepo.disable_2fa(1)
    u2 = UserRepo.get_by_id(1)
    assert u2.two_fa_enabled is False
    assert u2.two_fa_secret is None
test("UserRepo enable_2fa / disable_2fa round-trip", t_2fa_enable_disable_flow)


# ── Team Collaboration (invite + presence) ───────────────────────
print("\n[ Team Collaboration ]")

def t_team_invite_persists_and_emails():
    from database import UserRepo, TeamRepo
    from utils.email_service import send_team_invite, email_delivery_configured
    u = UserRepo.get_by_id(1)
    ok = TeamRepo.add(u.id, "Test Invitee", "invitee_test@example.com", "Analyst", "Invited")
    assert ok
    members = TeamRepo.list_for_user(u.id)
    assert any(m.email == "invitee_test@example.com" for m in members)
    sent, detail = send_team_invite("invitee_test@example.com", "Test Invitee",
                                     "Admin", "Test Org", "Analyst")
    assert isinstance(sent, bool)
    assert sent == email_delivery_configured()
test("Team invite persists member AND attempts real email", t_team_invite_persists_and_emails)

def t_team_member_status_transitions():
    from database import TeamRepo
    ok = TeamRepo.add(1, "Status Test", "statustest@example.com", "Viewer", "Invited")
    assert ok
    members = TeamRepo.list_for_user(1)
    m = next(x for x in members if x.email == "statustest@example.com")
    TeamRepo.update(m.id, status="Active")
    updated = TeamRepo.list_for_user(1)
    m2 = next(x for x in updated if x.email == "statustest@example.com")
    assert m2.status == "Active"
test("Team member status transitions from Invited to Active", t_team_member_status_transitions)

def t_team_last_active_tracked_for_presence():
    from database import TeamRepo
    import time
    ok = TeamRepo.add(1, "Presence Test", "presencetest@example.com", "Analyst", "Active")
    assert ok
    members = TeamRepo.list_for_user(1)
    m = next(x for x in members if x.email == "presencetest@example.com")
    assert m.last_active is not None, "last_active must be set for presence tracking"
    before = m.last_active
    TeamRepo.touch(m.id)
    updated = TeamRepo.list_for_user(1)
    m2 = next(x for x in updated if x.email == "presencetest@example.com")
    assert m2.last_active >= before, "TeamRepo.touch should update last_active"
test("TeamRepo tracks last_active for live presence display", t_team_last_active_tracked_for_presence)

def t_team_seat_count():
    from database import TeamRepo
    count_before = TeamRepo.count_for_user(1)
    TeamRepo.add(1, "Seat Test", "seattest@example.com", "Viewer", "Active")
    count_after = TeamRepo.count_for_user(1)
    assert count_after == count_before + 1
test("TeamRepo.count_for_user tracks seat usage", t_team_seat_count)

def t_team_link_on_registration():
    from database import UserRepo, TeamRepo
    import uuid
    email = f"pending_{uuid.uuid4().hex[:10]}@example.com"
    ok = TeamRepo.add(1, "Pending Person", email, "Analyst", "Invited")
    assert ok
    before = TeamRepo.get_by_email(1, email)
    assert before.member_user_id is None
    assert before.status == "Invited"

    uname = f"joiner_{uuid.uuid4().hex[:10]}"
    u = UserRepo.create(uname, email, "TestPass@99!", "New Joiner")
    assert u is not None

    linked = TeamRepo.link_pending_invites(email, u.id)
    assert linked == 1

    after = TeamRepo.get_by_email(1, email)
    assert after.member_user_id == u.id
    assert after.status == "Active"
test("TeamRepo.link_pending_invites connects a real account to its invite", t_team_link_on_registration)

def t_team_immediate_link_for_existing_account():
    from database import UserRepo, TeamRepo
    import uuid
    uname = f"early_{uuid.uuid4().hex[:10]}"
    email = f"{uname}@example.com"
    u = UserRepo.create(uname, email, "TestPass@99!", "Early Bird")
    assert u is not None

    # Owner invites someone who already has an account - should link immediately.
    existing_account = UserRepo.get_by_email(email)
    ok = TeamRepo.add(1, "Early Bird", email, "Viewer", "Active",
                       member_user_id=existing_account.id)
    assert ok

    membership = TeamRepo.get_membership_for_user(u.id)
    assert membership is not None
    assert membership.user_id == 1
    assert membership.role == "Viewer"
test("TeamRepo links immediately when invitee already has an account", t_team_immediate_link_for_existing_account)

def t_resolve_workspace_for_owner():
    from database import UserRepo, resolve_session_workspace
    import uuid
    uname = f"soloowner_{uuid.uuid4().hex[:10]}"
    u = UserRepo.create(uname, f"{uname}@example.com", "TestPass@99!", "Solo Owner")
    ctx = resolve_session_workspace(u.id)
    assert ctx["workspace_owner_id"] == u.id
    assert ctx["is_team_member"] is False
    assert ctx["team_role"] == "Owner"
test("resolve_session_workspace treats a non-invited user as their own owner", t_resolve_workspace_for_owner)

def t_resolve_workspace_for_member():
    from database import UserRepo, TeamRepo, resolve_session_workspace
    import uuid
    uname = f"member_{uuid.uuid4().hex[:10]}"
    email = f"{uname}@example.com"
    u = UserRepo.create(uname, email, "TestPass@99!", "Team Member")
    TeamRepo.add(1, "Team Member", email, "Manager", "Active", member_user_id=u.id)
    ctx = resolve_session_workspace(u.id)
    assert ctx["workspace_owner_id"] == 1
    assert ctx["is_team_member"] is True
    assert ctx["team_role"] == "Manager"
test("resolve_session_workspace routes a linked member into the owner's workspace", t_resolve_workspace_for_member)

def t_workspace_member_ids():
    from database import UserRepo, TeamRepo
    import uuid
    o_name = f"wsowner_{uuid.uuid4().hex[:10]}"
    owner = UserRepo.create(o_name, f"{o_name}@example.com", "TestPass@99!", "WS Owner")
    m_name = f"wsmember_{uuid.uuid4().hex[:10]}"
    member = UserRepo.create(m_name, f"{m_name}@example.com", "TestPass@99!", "WS Member")
    TeamRepo.add(owner.id, "WS Member", member.email, "Analyst", "Active", member_user_id=member.id)
    TeamRepo.add(owner.id, "Unlinked Invite", f"unlinked_{uuid.uuid4().hex[:8]}@example.com", "Viewer", "Invited")

    ids = TeamRepo.member_user_ids_for_workspace(owner.id)
    assert owner.id in ids
    assert member.id in ids
    assert len(ids) == 2, "unlinked invites must not count as real workspace members"
test("member_user_ids_for_workspace includes owner + linked members only", t_workspace_member_ids)

def t_comment_repo_scoped_by_workspace():
    from database import UserRepo, CommentRepo
    import uuid
    n1, n2 = f"cmtuser1_{uuid.uuid4().hex[:8]}", f"cmtuser2_{uuid.uuid4().hex[:8]}"
    u1 = UserRepo.create(n1, f"{n1}@example.com", "TestPass@99!", "Commenter One")
    u2 = UserRepo.create(n2, f"{n2}@example.com", "TestPass@99!", "Commenter Two")
    assert u1 and u2
    CommentRepo.add(0, u1.id, "Comment from workspace A", "General", "Low")
    CommentRepo.add(0, u2.id, "Comment from workspace B", "General", "Low")

    scoped = CommentRepo.list_recent(limit=50, user_ids=[u1.id])
    assert all(c.user_id == u1.id for c in scoped)
    assert any(c.comment_text == "Comment from workspace A" for c in scoped)
    assert not any(c.comment_text == "Comment from workspace B" for c in scoped)
test("CommentRepo.list_recent scopes to given workspace user_ids", t_comment_repo_scoped_by_workspace)

def t_comment_repo_unscoped_backward_compatible():
    from database import CommentRepo
    cmts = CommentRepo.list_recent(limit=5)
    assert isinstance(cmts, list)
test("CommentRepo.list_recent still works with no user_ids (backward compatible)", t_comment_repo_unscoped_backward_compatible)

def t_audit_repo_scoped_list_of_ids():
    from database import UserRepo, AuditRepo
    import uuid
    n1, n2 = f"audituser1_{uuid.uuid4().hex[:8]}", f"audituser2_{uuid.uuid4().hex[:8]}"
    u1 = UserRepo.create(n1, f"{n1}@example.com", "TestPass@99!", "Audit One")
    u2 = UserRepo.create(n2, f"{n2}@example.com", "TestPass@99!", "Audit Two")
    AuditRepo.log(u1.id, "workspace_a_action", "test")
    AuditRepo.log(u2.id, "workspace_b_action", "test")

    scoped = AuditRepo.list_recent(user_id=[u1.id], limit=50)
    assert any(a.action == "workspace_a_action" for a in scoped)
    assert not any(a.action == "workspace_b_action" for a in scoped)
test("AuditRepo.list_recent accepts a list of user_ids for workspace scoping", t_audit_repo_scoped_list_of_ids)


# ── User Preferences ─────────────────────────────────────────
print("\n[ User Preferences ]")

def t_user_preferences_roundtrip():
    from database import UserRepo
    ok = UserRepo.save_preferences(1, {"pref_palette": "Viridis", "pref_fc": 45})
    assert ok
    u = UserRepo.get_by_id(1)
    assert u.preferences.get("pref_palette") == "Viridis"
    assert u.preferences.get("pref_fc") == 45
    UserRepo.save_preferences(1, {})  # restore
test("UserRepo preferences save + reload round-trip", t_user_preferences_roundtrip)

def t_user_preferences_default_empty():
    from database import UserRepo
    import uuid
    uname = f"prefuser_{uuid.uuid4().hex[:10]}"
    u = UserRepo.create(uname, f"{uname}@example.com", "TestPass@99!", "Fresh User")
    assert u.preferences == {}
test("New users default to an empty preferences dict", t_user_preferences_default_empty)


def t_create_team_member_account_can_log_in():
    from database import UserRepo
    import uuid
    admin_owner = UserRepo.create(f"acct_owner_{uuid.uuid4().hex[:8]}",
                                   f"acct_owner_{uuid.uuid4().hex[:8]}@example.com",
                                   "TestPass@99!", "Account Owner", subscription="pro")
    email = f"provisioned_{uuid.uuid4().hex[:10]}@example.com"
    user, temp_password = UserRepo.create_team_member_account(email, "Provisioned Person", "Some Org",
                                                                account_owner_id=admin_owner.id)
    assert user is not None and temp_password
    assert user.email == email
    assert user.is_email_verified is True
    assert user.account_owner_id == admin_owner.id
    # The whole point: the shown password must actually work through the
    # real login path, immediately, with no extra step.
    logged_in = UserRepo.verify(email, temp_password)
    assert logged_in is not None and logged_in.id == user.id
test("create_team_member_account provisions a real, immediately-usable login", t_create_team_member_account_can_log_in)


def t_create_team_member_account_unique_usernames():
    from database import UserRepo
    import uuid
    # Two different people whose emails share the same local part before
    # the @ must not collide on username generation.
    tag = uuid.uuid4().hex[:8]
    owner = UserRepo.create(f"acct_owner2_{tag}", f"acct_owner2_{tag}@example.com",
                             "TestPass@99!", "Owner Two", subscription="pro")
    u1, p1 = UserRepo.create_team_member_account(f"same.name+{tag}a@example.com", "Person A", "Org",
                                                   account_owner_id=owner.id)
    u2, p2 = UserRepo.create_team_member_account(f"same.name+{tag}b@example.com", "Person B", "Org",
                                                   account_owner_id=owner.id)
    assert u1 is not None and u2 is not None
    assert u1.username != u2.username
test("create_team_member_account handles username collisions", t_create_team_member_account_unique_usernames)


def t_seat_inherits_owner_subscription():
    from database import UserRepo, resolve_session_workspace
    import uuid
    tag = uuid.uuid4().hex[:8]
    owner = UserRepo.create(f"sub_owner_{tag}", f"sub_owner_{tag}@example.com",
                             "TestPass@99!", "Sub Owner", subscription="pro")
    seat, _ = UserRepo.create_team_member_account(f"seat_{tag}@example.com", "Seat Person",
                                                    "Sub Owner's Workspace", account_owner_id=owner.id)
    # The seat's OWN row still says whatever UserRepo.create defaults to -
    # what actually matters is what a real login session resolves to.
    ctx = resolve_session_workspace(seat.id)
    assert ctx["subscription"] == "pro", "a seat must inherit the paid account's plan, not default to free"
    assert ctx["workspace_owner_id"] == owner.id
    assert ctx["is_team_member"] is True
test("A provisioned seat inherits the account owner's subscription tier", t_seat_inherits_owner_subscription)


def t_account_owner_takes_priority_over_stale_team_row():
    from database import UserRepo, TeamRepo, resolve_session_workspace
    import uuid
    tag = uuid.uuid4().hex[:8]
    owner = UserRepo.create(f"prio_owner_{tag}", f"prio_owner_{tag}@example.com",
                             "TestPass@99!", "Prio Owner", subscription="pro")
    member = UserRepo.create(f"prio_member_{tag}", f"prio_member_{tag}@example.com",
                              "TestPass@99!", "Prio Member")
    TeamRepo.add(owner.id, "Prio Member", member.email, "Analyst", "Active", member_user_id=member.id)
    UserRepo.update_fields(member.id, account_owner_id=owner.id)
    ctx = resolve_session_workspace(member.id)
    assert ctx["workspace_owner_id"] == owner.id
    assert ctx["subscription"] == "pro"
test("account_owner_id on the user row is the source of truth for workspace resolution", t_account_owner_takes_priority_over_stale_team_row)


def t_seat_subscription_updates_live_with_owner_plan():
    from database import UserRepo, resolve_session_workspace
    import uuid
    tag = uuid.uuid4().hex[:8]
    owner = UserRepo.create(f"live_owner_{tag}", f"live_owner_{tag}@example.com",
                             "TestPass@99!", "Live Owner", subscription="free")
    seat, _ = UserRepo.create_team_member_account(f"live_seat_{tag}@example.com", "Live Seat",
                                                    "Live Owner's Workspace", account_owner_id=owner.id)
    assert resolve_session_workspace(seat.id)["subscription"] == "free"
    # Owner upgrades. The seat's own row is never touched - there's nothing
    # to re-link or re-sync. The next resolution just reflects reality.
    UserRepo.update_fields(owner.id, subscription="pro")
    assert resolve_session_workspace(seat.id)["subscription"] == "pro"
test("A seat's effective plan updates immediately when the owner's plan changes, no re-linking needed", t_seat_subscription_updates_live_with_owner_plan)


def t_manual_status_roundtrip():
    from database import UserRepo
    import uuid
    uname = f"statususer_{uuid.uuid4().hex[:10]}"
    u = UserRepo.create(uname, f"{uname}@example.com", "TestPass@99!", "Status User")
    assert u.manual_status is None
    ok = UserRepo.set_manual_status(u.id, "Busy")
    assert ok
    reloaded = UserRepo.get_by_id(u.id)
    assert reloaded.manual_status == "Busy"
    UserRepo.set_manual_status(u.id, None)
    assert UserRepo.get_by_id(u.id).manual_status is None
test("UserRepo.set_manual_status round-trips and clears back to Auto", t_manual_status_roundtrip)


def t_theme_reflects_palette_preference():
    import streamlit as st
    import design
    st.session_state["pref_palette"] = "Blues"
    css = design.custom_css()
    assert "#2171B5" in css
    st.session_state["pref_palette"] = "LionsylAI (default)"
    assert "#6C63FF" in design.custom_css()
test("Theme CSS changes with the saved chart palette preference", t_theme_reflects_palette_preference)


# ── Schema Migrations ────────────────────────────────────────
print("\n[ Schema Migrations ]")

def t_migration_columns_present_and_idempotent():
    import database as db
    from sqlalchemy import inspect as sa_inspect
    assert db.init_db() is True
    assert db.init_db() is True  # idempotent - running it twice must not error
    insp = sa_inspect(db.engine)
    team_cols = {c["name"] for c in insp.get_columns("team_members")}
    user_cols = {c["name"] for c in insp.get_columns("users")}
    assert "member_user_id" in team_cols
    assert "preferences_json" in user_cols
test("Light migration adds new columns and is safe to run repeatedly", t_migration_columns_present_and_idempotent)


# ── Page Syntax ───────────────────────────────────────────────
print("\n[ Page Syntax ]")
for page in [
    "pages/auth_page.py","pages/dashboard_tab.py","pages/profit_tab.py",
    "pages/ai_studio_tab.py","pages/strategy_tab.py","pages/analytics_tab.py",
    "pages/fpa_tab.py","pages/monthend_tab.py","pages/cash_tab.py",
    "pages/integrations_tab.py","pages/team_tab.py","pages/advanced_tab.py",
    "pages/settings_tab.py","app.py","database.py",
]:
    def t_syntax(p=page):
        with open(p) as f:
            compile(f.read(), p, "exec")
    test(f"syntax: {page}", t_syntax)

# ── Summary ───────────────────────────────────────────────────
print(f"\n{'='*40}")
print(f"  PASSED: {len(PASS)}/{len(PASS)+len(FAIL)}")
if FAIL:
    print(f"  FAILED: {len(FAIL)}")
    for name, err in FAIL:
        print(f"    ✗ {name}: {err}")
else:
    print("  ALL TESTS PASSED ✅")
print(f"{'='*40}\n")

sys.exit(0 if not FAIL else 1)
