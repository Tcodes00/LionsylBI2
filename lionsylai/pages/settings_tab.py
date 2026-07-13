"""
LionsylAI - Tab 12: Settings
Profile - Security (2FA, sessions) - Billing (Stripe + SSLCommerz) -
Data Management - Preferences - Email Setup
"""
from __future__ import annotations
from datetime import datetime

import streamlit as st

from database import UserRepo, AuditRepo, SessionRepo, TransactionRepo
from design import section_header, kpi_card, insight_card, badge
from utils.payment import (
    create_customer_portal, render_pricing_html, stripe_configured,
    sslcommerz_configured, create_checkout_session, create_sslcommerz_session,
)
from utils.email_service import email_delivery_configured, send_payment_receipt
from utils.prefs import chart_colors, currency_symbol, date_format
from utils.auth import (
    totp_available, generate_totp_secret, totp_provisioning_uri,
    totp_qrcode_base64, totp_verify,
)
from config.settings import (
    PLANS, APP_URL, SUPPORTED_COUNTRIES, BD_PAYMENT_METHODS, INTL_PAYMENT_METHODS,
)

_PREF_KEYS = [
    "pref_tab", "pref_palette", "pref_currency", "pref_datefmt",
    "pref_autins", "pref_autcol", "pref_ml", "pref_fc",
]


def render():
    st.markdown(section_header("Settings", "Profile - Security - Billing - Data - Preferences"),
                unsafe_allow_html=True)

    default_idx = 2 if st.session_state.pop("_jump_to_billing", False) else 0
    t1, t2, t3, t4, t5, t6 = st.tabs([
        "Profile", "Security", "Billing", "Data Management", "Preferences", "Email Setup"
    ])
    with t1: _profile()
    with t2: _security()
    with t3: _billing()
    with t4: _data_management()
    with t5: _preferences()
    with t6: _email_setup()


# ---- Profile -----------------------------------------------------------

def _profile():
    st.markdown("### Profile Settings")
    uid       = st.session_state.get("user_id")
    username  = st.session_state.get("username", "")
    email     = st.session_state.get("user_email", "")
    full_name = st.session_state.get("user_full_name", "")
    org_name  = st.session_state.get("org_name", "")
    role      = st.session_state.get("user_role", "user")
    sub       = st.session_state.get("subscription", "free")

    c1, c2 = st.columns([1, 2])
    with c1:
        initials = (full_name or username or "U")[:2].upper()
        st.markdown(f"""
        <div style="width:96px;height:96px;border-radius:50%;
                    background:linear-gradient(135deg,#6C63FF,#0AEFFF);
                    display:flex;align-items:center;justify-content:center;
                    font-size:36px;font-weight:800;color:#fff;margin:0 auto 16px;">
          {initials}
        </div>
        <div style="text-align:center;">
          <div style="font-size:18px;font-weight:700;color:#F0F2FF;">{full_name or username}</div>
          <div style="font-size:13px;color:#9CA3AF;">{email}</div>
          <div style="font-size:12px;color:#6B7280;margin-top:4px;">{org_name}</div>
          <div style="margin-top:8px;">
            {badge(role.title())} {badge(sub.title(), '#10B981' if sub=='pro' else '#6B7280')}
          </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("#### Edit Profile")
        new_name  = st.text_input("Full Name",     value=full_name,  key="prof_name")
        new_org   = st.text_input("Organization",  value=org_name,   key="prof_org")
        new_email = st.text_input("Email Address", value=email,       key="prof_email")
        st.text_input("Username (read-only)", value=username, disabled=True)

        if st.button("Save Profile", type="primary", use_container_width=True):
            if uid:
                updates = {}
                if new_name:  updates["full_name"] = new_name
                if new_org:   updates["org_name"]  = new_org
                if new_email: updates["email"]     = new_email
                if updates:
                    UserRepo.update_fields(uid, **updates)
                st.session_state["user_full_name"] = new_name or full_name
                st.session_state["org_name"]       = new_org or org_name
                st.session_state["user_email"]     = new_email or email
                AuditRepo.log(uid, "profile_updated", "Profile fields updated")
            st.success("Profile updated!")

        st.markdown("---")
        st.markdown("#### Change Password")
        old_pw  = st.text_input("Current Password", type="password", key="pw_old")
        new_pw1 = st.text_input("New Password",     type="password", key="pw_new1")
        new_pw2 = st.text_input("Confirm Password", type="password", key="pw_new2")

        if st.button("Change Password", use_container_width=True):
            if not old_pw or not new_pw1:
                st.warning("Please fill in all password fields.")
            elif new_pw1 != new_pw2:
                st.error("New passwords do not match.")
            elif len(new_pw1) < 8:
                st.error("Password must be at least 8 characters.")
            else:
                if uid:
                    udata = UserRepo.get_by_id(uid)
                    if udata:
                        from utils.auth import verify_password, hash_password
                        if verify_password(old_pw, udata.password_hash):
                            new_hash = hash_password(new_pw1)
                            UserRepo.update_fields(uid, password_hash=new_hash)
                            AuditRepo.log(uid, "password_changed", "Password updated")
                            st.success("Password changed successfully!")
                        else:
                            st.error("Current password is incorrect.")


# ---- Security: 2FA + Active Sessions ------------------------------------

def _security():
    st.markdown("### Security")
    uid = st.session_state.get("user_id")
    udata = UserRepo.get_by_id(uid) if uid else None

    st.markdown("#### Two-Factor Authentication (2FA)")
    if not totp_available():
        st.warning("2FA library (pyotp) is not installed on this server.")
    elif udata and udata.two_fa_enabled:
        st.success("2FA is currently **enabled** on your account.")
        code_off = st.text_input("Enter a code from your app to disable 2FA", max_chars=6, key="2fa_disable_code")
        if st.button("Disable 2FA", use_container_width=True):
            if udata.two_fa_secret and totp_verify(udata.two_fa_secret, code_off):
                UserRepo.disable_2fa(uid)
                AuditRepo.log(uid, "2fa_disabled", "")
                st.success("2FA disabled.")
                st.rerun()
            else:
                st.error("Invalid code.")
    else:
        st.info("Add an extra layer of security. You'll need an authenticator app "
                "(Google Authenticator, Authy, 1Password, etc).")
        if st.button("Set up 2FA", use_container_width=True, key="2fa_setup_btn"):
            secret = generate_totp_secret()
            st.session_state["_2fa_pending_secret"] = secret

        pending_secret = st.session_state.get("_2fa_pending_secret")
        if pending_secret:
            uri = totp_provisioning_uri(pending_secret, st.session_state.get("user_email",""))
            qr  = totp_qrcode_base64(uri)
            c1, c2 = st.columns([1, 2])
            with c1:
                if qr:
                    st.markdown(f'<img src="{qr}" width="180" style="border-radius:12px;"/>',
                               unsafe_allow_html=True)
            with c2:
                st.write("Scan this QR code with your authenticator app, or enter the key manually:")
                st.code(pending_secret, language=None)
                confirm_code = st.text_input("Enter the 6-digit code to confirm", max_chars=6, key="2fa_confirm_code")
                if st.button("Confirm & Enable 2FA", type="primary", use_container_width=True):
                    if totp_verify(pending_secret, confirm_code):
                        UserRepo.enable_2fa(uid, pending_secret)
                        AuditRepo.log(uid, "2fa_enabled", "")
                        st.session_state.pop("_2fa_pending_secret", None)
                        st.success("2FA enabled successfully!")
                        st.rerun()
                    else:
                        st.error("Invalid code. Please try again.")

    st.markdown("---")
    st.markdown("#### Active Sessions")
    st.caption("Devices currently signed in to your account. Revoke any you don't recognise.")
    if uid:
        sessions = SessionRepo.list_for_user(uid)
        current_token = st.session_state.get("session_token")
        if sessions:
            for s in sessions:
                is_current = (s.token == current_token)
                last_seen = s.last_seen.strftime("%Y-%m-%d %H:%M") if s.last_seen else "—"
                expires   = s.expires_at.strftime("%Y-%m-%d") if s.expires_at else "—"
                bdr = "#6C63FF" if is_current else "#252836"
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"""
                    <div style="background:#141720;border:1px solid {bdr};border-radius:10px;
                                padding:12px 16px;margin:6px 0;">
                      <div style="font-weight:{'700' if is_current else '400'};color:#F0F2FF;">
                        {'This device (current session)' if is_current else 'Other device'}
                        {' &middot; Remember Me' if s.remember_me else ''}
                      </div>
                      <div style="font-size:12px;color:#6B7280;">
                        Last active: {last_seen} &middot; Expires: {expires}
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    if not is_current:
                        if st.button("Revoke", key=f"revoke_{s.id}", use_container_width=True):
                            SessionRepo.revoke_by_id(s.id)
                            st.success("Session revoked.")
                            st.rerun()
        else:
            st.info("No active sessions found.")


# ---- Billing: Stripe (world) + SSLCommerz (Bangladesh) -------------------

def _billing():
    st.markdown("### Billing & Subscription")
    sub = st.session_state.get("subscription", "free")
    uid = st.session_state.get("user_id")
    eml = st.session_state.get("user_email", "")
    name = st.session_state.get("user_full_name", "")

    if sub == "pro":
        st.markdown("""
        <div style="background:linear-gradient(135deg,#6C63FF22,#0AEFFF22);
                    border:1px solid #6C63FF55;border-radius:16px;padding:24px 28px;
                    margin-bottom:24px;display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="font-size:20px;font-weight:800;color:#fff;">Professional Plan — Active</div>
            <div style="color:#9CA3AF;font-size:14px;margin-top:4px;">Full access to all features</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Manage Billing (Stripe Portal)", use_container_width=True):
                udata = UserRepo.get_by_id(uid) if uid else None
                cid = udata.stripe_customer_id if udata else None
                if cid:
                    url = create_customer_portal(cid)
                    if url:
                        st.markdown(f'<meta http-equiv="refresh" content="0;url={url}">', unsafe_allow_html=True)
                    else:
                        st.info("Stripe portal not reachable right now.")
                else:
                    st.info("No Stripe billing record on this account (may have upgraded via SSLCommerz or demo mode).")
        with c2:
            if st.button("Cancel Subscription", use_container_width=True):
                st.warning("To cancel, use the Stripe billing portal above, or contact support@lionsylai.com.")

    else:
        st.markdown("""
        <div style="background:#141720;border:1px solid #252836;border-radius:16px;
                    padding:24px 28px;margin-bottom:24px;">
          <div style="font-size:18px;font-weight:700;color:#fff;margin-bottom:8px;">Free Plan</div>
          <div style="color:#9CA3AF;font-size:14px;">Core features - upgrade to Pro for full access</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Choose your country / payment region")
        country = st.selectbox("Country", SUPPORTED_COUNTRIES, key="bill_country")
        is_bd = country == "Bangladesh"

        billing = st.radio(
            "Billing cycle",
            ["Monthly", "Annual (save ~17%)"],
            horizontal=True, key="bill_cycle",
        )
        b_key = "month" if "Monthly" in billing else "year"

        st.markdown(render_pricing_html(b_key, "BDT" if is_bd else "USD"), unsafe_allow_html=True)

        if is_bd:
            st.markdown("#### Payment Method")
            method = st.selectbox("Choose method", BD_PAYMENT_METHODS, key="bd_method")
            phone  = st.text_input("Mobile Number (for bKash/Nagad/Rocket)", placeholder="01XXXXXXXXX", key="bd_phone")

            if not sslcommerz_configured():
                st.info(
                    "SSLCommerz isn't configured on this server yet. An administrator needs to "
                    "add `SSLCOMMERZ_STORE_ID` and `SSLCOMMERZ_STORE_PASSWD` in `.env` "
                    "(free sandbox account at merchant.sslcommerz.com)."
                )

            if st.button(f"Pay with {method}", type="primary", use_container_width=True):
                if not uid:
                    st.warning("Please sign in first.")
                else:
                    plan = PLANS["pro"]
                    amount_bdt = plan["price_bdt_month"] if b_key == "month" else plan["price_bdt_year"]
                    result = create_sslcommerz_session(eml, uid, name, phone, amount_bdt, b_key)
                    if result:
                        st.markdown(f'<meta http-equiv="refresh" content="0;url={result["gateway_url"]}">',
                                   unsafe_allow_html=True)
                        st.info("Redirecting to secure payment gateway...")
                        AuditRepo.log(uid, "checkout_started", f"SSLCommerz {result['transaction_id']}")
                    else:
                        st.warning("Payment gateway isn't configured — activating demo Pro access instead.")
                        _demo_upgrade(uid, "sslcommerz-demo", amount_bdt, "BDT", b_key)

        else:
            st.markdown("#### Payment Method")
            st.selectbox("Choose method", INTL_PAYMENT_METHODS, key="intl_method")

            if not stripe_configured():
                st.info(
                    "Stripe isn't configured on this server yet. An administrator needs to add "
                    "`STRIPE_SECRET_KEY` and `STRIPE_PRICE_ID` in `.env`."
                )

            if st.button("Continue to Stripe Checkout", type="primary", use_container_width=True):
                if not uid:
                    st.warning("Please sign in first.")
                else:
                    url = create_checkout_session(eml, uid, b_key)
                    if url:
                        st.markdown(f'<meta http-equiv="refresh" content="0;url={url}">', unsafe_allow_html=True)
                        st.info("Redirecting to Stripe...")
                        AuditRepo.log(uid, "checkout_started", f"Stripe {b_key}")
                    else:
                        st.warning("Payment gateway isn't configured — activating demo Pro access instead.")
                        plan = PLANS["pro"]
                        amount = plan["price_month"] if b_key == "month" else plan["price_year"]
                        _demo_upgrade(uid, "demo", amount, "USD", b_key)

    st.markdown("---")
    st.markdown("#### Invoice History")
    if uid:
        txs = TransactionRepo.list_for_user(uid, limit=20)
        if txs:
            import pandas as pd
            inv_df = pd.DataFrame([{
                "Date":   t.created_at.strftime("%Y-%m-%d") if t.created_at else "",
                "Amount": f"{t.amount:,.2f} {t.currency}",
                "Method": t.gateway,
                "Status": t.status.title(),
            } for t in txs])
            st.dataframe(inv_df, use_container_width=True, hide_index=True)
        else:
            st.info("No invoices yet.")


def _demo_upgrade(uid, gateway, amount, currency, billing_cycle):
    UserRepo.update_fields(uid, subscription="pro")
    TransactionRepo.create(uid, gateway, amount, currency, "pro", billing_cycle, "completed")
    st.session_state["subscription"] = "pro"
    AuditRepo.log(uid, "subscription_upgraded", f"Upgraded to Pro via {gateway} (demo)")
    eml  = st.session_state.get("user_email", "")
    name = st.session_state.get("user_full_name", "")
    if eml:
        send_payment_receipt(eml, name, f"{amount:,.2f}", currency, "Professional", gateway)
    st.success("Upgraded to Pro! (demo mode - no real charge was made)")
    st.rerun()


# ---- Data Management -----------------------------------------------------

def _data_management():
    st.markdown("### Data Management")
    uid = st.session_state.get("user_id")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Dataset Overview")
        df = st.session_state.get("app_df")
        if df is not None:
            missing      = int(df.isnull().sum().sum())
            total_cells  = int(df.size)
            missing_pct  = round(missing / total_cells * 100, 1) if total_cells else 0
            mem_mb       = round(df.memory_usage(deep=True).sum() / 1024 / 1024, 1)
            ncols        = len(df.select_dtypes(include=["number"]).columns)

            st.metric("Rows x Cols",    f"{len(df):,} x {len(df.columns)}")
            st.metric("Numeric Cols",   ncols)
            st.metric("Missing Values", f"{missing:,} ({missing_pct}%)")
            st.metric("Memory Usage",   f"{mem_mb} MB")

            if st.button("Clear All Session Data", use_container_width=True):
                for key in ["app_df","consolidated_df","last_report","report_library",
                            "budget_data","rt_history","comments_cache",
                            "me_checklist","webhooks","generated_api_key","viewing_report"]:
                    st.session_state.pop(key, None)
                st.success("Session data cleared!")
                st.rerun()
        else:
            st.info("No dataset loaded. Upload a file in the sidebar.")

    with c2:
        st.markdown("#### Data Privacy")
        for item in [
            "Data processed locally (not stored on our servers)",
            "Session data cleared on logout",
            "Passwords hashed with bcrypt",
            "HTTPS encryption in transit",
            "No data shared with third parties",
            "GDPR & CCPA compliant",
        ]:
            st.markdown(f"<div style='padding:8px 0;border-bottom:1px solid #252836;color:#E0E4F0;'>✅ {item}</div>",
                        unsafe_allow_html=True)

        st.markdown("#### Delete Account")
        confirm_del = st.text_input("Type DELETE to confirm", key="del_confirm")
        if st.button("Delete My Account", use_container_width=True):
            if confirm_del == "DELETE":
                if uid:
                    UserRepo.update_fields(uid, is_active=False)
                    AuditRepo.log(uid, "account_deleted", "Account deactivated by user")
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.success("Account deactivated. Goodbye!")
                st.rerun()
            else:
                st.warning("Type DELETE exactly to confirm.")


# ---- Preferences -----------------------------------------------------

def _preferences():
    st.markdown("### App Preferences")
    uid = st.session_state.get("user_id")

    # Load whatever was last saved, once per session, BEFORE the widgets
    # below are created - Streamlit gives a widget's session_state value
    # priority over its `value=` default, so this is what makes a saved
    # preference actually come back instead of resetting every visit.
    if uid and not st.session_state.get("_prefs_loaded"):
        u = UserRepo.get_by_id(uid)
        if u and u.preferences:
            for k, v in u.preferences.items():
                if k in _PREF_KEYS and k not in st.session_state:
                    st.session_state[k] = v
        st.session_state["_prefs_loaded"] = True
        st.session_state["_prefs_last_saved"] = {
            k: st.session_state.get(k) for k in _PREF_KEYS if k in st.session_state
        }

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Display")
        st.selectbox("Default landing tab",
                     ["Dashboard","Profit","AI Studio","Strategy"], key="pref_tab")
        st.selectbox("Chart colour palette",
                     ["LionsylAI (default)","Viridis","Plasma","Inferno","Blues"], key="pref_palette")
        st.selectbox("Currency display",
                     ["USD ($)","BDT (৳)","EUR (€)","GBP (£)","JPY (¥)"], key="pref_currency")
        st.selectbox("Date format", ["YYYY-MM-DD","DD/MM/YYYY","MM/DD/YYYY"], key="pref_datefmt")

        palette = chart_colors()
        swatches = "".join(f"<span style='display:inline-block;width:20px;height:20px;"
                            f"border-radius:5px;background:{c};margin-right:4px;'></span>" for c in palette)
        symbol = currency_symbol()
        date_str = datetime.now().strftime(date_format())
        st.markdown(f"""
        <div style="background:#141720;border:1px solid #252836;border-radius:10px;
                    padding:12px 14px;margin-top:10px;">
          <div style="font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:0.08em;
                      margin-bottom:8px;">Live preview</div>
          <div style="margin-bottom:8px;">{swatches}</div>
          <div style="font-size:13px;color:#E0E4F0;">Sample KPI: <strong>{symbol}14,990.00</strong> &middot; {date_str}</div>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Changes save instantly and apply to charts and currency on the Dashboard right away - not just here.")

    with c2:
        st.markdown("#### AI & Analytics")
        st.toggle("Auto-generate insights on upload", value=True, key="pref_autins")
        st.toggle("Auto-detect financial columns",    value=True, key="pref_autcol")
        st.selectbox("Default ML task", ["Auto-detect","Regression","Classification"], key="pref_ml")
        st.slider("Default forecast periods", 7, 365, 30, key="pref_fc")

    # Autosave - the instant anything above changes, persist it. No button,
    # no separate "did I save that" step: this rerun already has the latest
    # widget values in session_state, so we just diff against what was last
    # written and save if anything moved.
    if uid:
        current = {k: st.session_state.get(k) for k in _PREF_KEYS if k in st.session_state}
        if current != st.session_state.get("_prefs_last_saved"):
            UserRepo.save_preferences(uid, current)
            AuditRepo.log(uid, "preferences_saved", "App preferences updated")
            st.session_state["_prefs_last_saved"] = current
            st.toast("Preferences saved", icon="✅")
        st.caption("Changes here save instantly and reload automatically next time you sign in.")
    else:
        st.warning("Sign in to save preferences.")


# ---- Email Setup (admin help) -----------------------------------------

def _email_setup():
    st.markdown("### Email Delivery Setup")

    if email_delivery_configured():
        st.success("Email delivery is configured and active on this server.")
    else:
        st.warning(
            "Email delivery is **not configured**. Verification codes, password reset "
            "links, and team invites will not reach real inboxes until this is set up."
        )

    st.markdown("#### Option A — SMTP (recommended, works with Gmail in 2 minutes)")
    st.markdown("""
1. Go to your Google Account → **Security** → turn on **2-Step Verification**
2. Visit [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create an app password named "LionsylAI"
4. Add these to your `.env` file:
""")
    st.code(
        "SMTP_HOST=smtp.gmail.com\n"
        "SMTP_PORT=587\n"
        "SMTP_USER=youraddress@gmail.com\n"
        "SMTP_PASSWORD=<the 16-character app password>\n"
        "SMTP_USE_TLS=true",
        language="bash",
    )
    st.caption("Works with any SMTP provider (Outlook, Zoho, Amazon SES, etc) — just change the host/port.")

    st.markdown("#### Option B — SendGrid")
    st.code(
        "SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxx\n"
        "FROM_EMAIL=noreply@yourdomain.com",
        language="bash",
    )

    st.markdown("#### Payment Gateway Setup")
    st.markdown("**Stripe (international cards)**")
    st.code(
        "STRIPE_SECRET_KEY=sk_live_xxxx\n"
        "STRIPE_PUBLISHABLE_KEY=pk_live_xxxx\n"
        "STRIPE_PRICE_ID=price_xxxx",
        language="bash",
    )
    st.markdown("**SSLCommerz (Bangladesh: bKash, Nagad, Rocket, local cards)**")
    st.code(
        "SSLCOMMERZ_STORE_ID=your_store_id\n"
        "SSLCOMMERZ_STORE_PASSWD=your_store_password\n"
        "SSLCOMMERZ_SANDBOX=true",
        language="bash",
    )
    st.caption("Get a free sandbox account at merchant.sslcommerz.com to test before going live.")

    st.markdown("After editing `.env`, restart the app for changes to take effect.")
