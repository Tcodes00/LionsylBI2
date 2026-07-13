"""
LionsylAI - Authentication Pages
Login (+Remember Me) - Sign-Up - Email Verification - Password Reset - Pricing/Checkout
"""
from __future__ import annotations
import re
from datetime import datetime, timedelta

import streamlit as st

from database import (
    UserRepo, AuditRepo, NotificationRepo, SessionRepo, LoginAttemptRepo,
    TeamRepo, resolve_session_workspace,
)
from utils.auth import (
    generate_otp, generate_secure_token, password_strength,
    create_access_token, totp_verify,
)
from utils.email_service import (
    send_verification_email, send_password_reset, email_delivery_configured,
)
from utils.payment import create_checkout_session, render_pricing_html
from config.settings import (
    PLANS, APP_URL, ENABLE_PAYMENTS,
    LOGIN_LOCKOUT_MAX_ATTEMPTS, LOGIN_LOCKOUT_WINDOW_MIN,
)


def _valid_email(e: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e))


def _init_auth_state():
    for k, v in {
        "auth_view": "login", "pending_user_id": None, "pending_email": "",
        "pending_otp": "", "otp_expires": None, "reset_token": "",
        "pending_2fa_user_id": None, "login_identifier_cache": "",
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render_auth():
    _init_auth_state()
    _render_brand_hero()
    view = st.session_state.auth_view
    if view == "login":       _render_login()
    elif view == "register":  _render_register()
    elif view == "verify":    _render_verify_email()
    elif view == "totp":      _render_totp_challenge()
    elif view == "forgot":    _render_forgot_password()
    elif view == "reset":     _render_reset_password()
    elif view == "pricing":   _render_pricing()


def _render_brand_hero():
    st.markdown("""
    <div style="text-align:center;padding:32px 0 20px;">
      <div style="font-size:56px;line-height:1;">🦁</div>
      <h1 style="font-family:'Space Grotesk',sans-serif;font-size:36px;font-weight:900;
                 background:linear-gradient(90deg,#6C63FF,#0AEFFF);
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                 background-clip:text;margin:8px 0 4px;">LionsylAI</h1>
      <p style="color:#6B7280;font-size:14px;letter-spacing:0.12em;
                text-transform:uppercase;margin:0;">Enterprise Analytics Intelligence</p>
    </div>
    """, unsafe_allow_html=True)


def _email_status_banner():
    """Shown near code-sending forms so users know if delivery is real."""
    if not email_delivery_configured():
        st.markdown("""
        <div style="background:#F59E0B15;border:1px solid #F59E0B44;border-radius:10px;
                    padding:10px 14px;margin-bottom:12px;font-size:12px;color:#F59E0B;">
          Email delivery is not configured on this server yet, so codes/links won't
          reach your inbox. An administrator can add SMTP settings in <code>.env</code>
          (see Settings &rarr; Email Setup for instructions).
        </div>
        """, unsafe_allow_html=True)


# ---- Login -------------------------------------------------------

def _render_login():
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown("""
        <div style="background:#141720;border:1px solid #252836;border-radius:20px;
                    padding:36px 32px;box-shadow:0 8px 40px rgba(0,0,0,0.4);">
          <h2 style="font-family:'Space Grotesk',sans-serif;font-size:22px;font-weight:700;
                     color:#fff;text-align:center;margin:0 0 28px;">Welcome back</h2>
        </div>
        """, unsafe_allow_html=True)

        identifier = st.text_input("Email or Username", placeholder="you@company.com")
        password   = st.text_input("Password", type="password", placeholder="••••••••••••")
        remember   = st.checkbox("Remember me for 30 days", value=True)

        col_a, col_b = st.columns([3, 2])
        with col_a:
            if st.button("Sign In", type="primary", use_container_width=True):
                if not identifier or not password:
                    st.error("Please fill in both fields.")
                else:
                    _attempt_login(identifier, password, remember)
        with col_b:
            if st.button("Forgot password?", use_container_width=True):
                st.session_state.auth_view = "forgot"
                st.rerun()

        st.markdown("<hr style='border-color:#252836;margin:20px 0;'/>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Create Account", use_container_width=True):
                st.session_state.auth_view = "register"
                st.rerun()
        with c2:
            if st.button("View Pricing", use_container_width=True):
                st.session_state.auth_view = "pricing"
                st.rerun()

        with st.expander("Demo credentials"):
            st.code("Username: admin\nPassword: Admin@2026!", language="text")
            st.caption("Full admin access to all features.")


def _attempt_login(identifier: str, password: str, remember: bool):
    # Brute-force lockout check
    failures = LoginAttemptRepo.count_recent_failures(identifier, LOGIN_LOCKOUT_WINDOW_MIN)
    if failures >= LOGIN_LOCKOUT_MAX_ATTEMPTS:
        st.error(
            f"Too many failed attempts. Please try again in {LOGIN_LOCKOUT_WINDOW_MIN} minutes, "
            f"or use 'Forgot password?' to reset."
        )
        return

    user = UserRepo.verify(identifier, password)
    if not user:
        LoginAttemptRepo.record(identifier, success=False)
        remaining = LOGIN_LOCKOUT_MAX_ATTEMPTS - failures - 1
        if remaining <= 2 and remaining >= 0:
            st.error(f"Invalid credentials. {remaining} attempt(s) remaining before temporary lockout.")
        else:
            st.error("Invalid credentials. Please try again.")
        return

    LoginAttemptRepo.record(identifier, success=True)
    LoginAttemptRepo.clear_for(identifier)

    if not user.is_email_verified:
        st.warning("Please verify your email first.")
        st.session_state.pending_user_id = user.id
        st.session_state.pending_email   = user.email
        _send_otp(user.id, user.email, user.full_name or user.username)
        st.session_state.auth_view = "verify"
        st.rerun()
        return

    if user.two_fa_enabled:
        st.session_state.pending_2fa_user_id = user.id
        st.session_state["_2fa_remember"] = remember
        st.session_state.auth_view = "totp"
        st.rerun()
        return

    _complete_login(user, remember)


def _complete_login(user, remember: bool = False):
    token = create_access_token({"sub": user.id, "role": user.role})
    sess_token = SessionRepo.create(user.id, remember_me=remember,
                                    user_agent="streamlit-client", ip_address="")

    st.session_state.authenticated  = True
    st.session_state.user_id        = user.id
    st.session_state.username       = user.username
    st.session_state.user_email     = user.email
    st.session_state.user_full_name = user.full_name or user.username
    st.session_state.user_role      = user.role
    st.session_state.subscription   = user.subscription
    st.session_state.org_name       = user.org_name
    st.session_state.access_token   = token
    st.session_state.session_token  = sess_token
    st.session_state.update(resolve_session_workspace(user.id))

    if sess_token:
        try:
            st.query_params["s"] = sess_token
        except Exception:
            pass

    AuditRepo.log(user.id, "login", f"Successful login - {user.username}")
    st.rerun()


def _render_totp_challenge():
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        st.markdown("""
        <div style="background:#141720;border:1px solid #252836;border-radius:20px;
                    padding:36px 32px;text-align:center;">
          <div style="font-size:40px;margin-bottom:12px;">🔐</div>
          <h2 style="font-family:'Space Grotesk',sans-serif;color:#fff;margin:0 0 8px;">
            Two-Factor Authentication</h2>
          <p style="color:#9CA3AF;font-size:14px;margin:0 0 20px;">
            Enter the 6-digit code from your authenticator app.</p>
        </div>
        """, unsafe_allow_html=True)

        code = st.text_input("Authentication Code", placeholder="000000", max_chars=6)
        if st.button("Verify & Sign In", type="primary", use_container_width=True):
            uid  = st.session_state.pending_2fa_user_id
            user = UserRepo.get_by_id(uid)
            if user and user.two_fa_secret and totp_verify(user.two_fa_secret, code):
                remember = st.session_state.get("_2fa_remember", False)
                _complete_login(user, remember)
            else:
                st.error("Invalid code. Please try again.")

        if st.button("← Back to Login", use_container_width=True):
            st.session_state.auth_view = "login"
            st.rerun()


# ---- Register ------------------------------------------------------

def _render_register():
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        st.markdown("""
        <div style="background:#141720;border:1px solid #252836;border-radius:20px;
                    padding:36px 32px;box-shadow:0 8px 40px rgba(0,0,0,0.4);">
          <h2 style="font-family:'Space Grotesk',sans-serif;font-size:22px;font-weight:700;
                     color:#fff;text-align:center;margin:0 0 8px;">Create your account</h2>
          <p style="text-align:center;color:#9CA3AF;font-size:13px;margin:0 0 28px;">
            Start free. Upgrade to Pro any time.</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1: full_name = st.text_input("Full Name *", placeholder="Jane Smith")
        with col2: username  = st.text_input("Username *",  placeholder="janesmith")
        email = st.text_input("Work Email *", placeholder="jane@company.com")
        col3, col4 = st.columns(2)
        with col3: pw1 = st.text_input("Password *",         type="password", placeholder="Min 8 chars")
        with col4: pw2 = st.text_input("Confirm Password *", type="password", placeholder="Repeat")

        if pw1:
            strength = password_strength(pw1)
            st.markdown(f"""
            <div style="height:4px;background:#252836;border-radius:2px;margin:4px 0 2px;">
              <div style="height:4px;width:{strength['score']*25}%;background:{strength['color']};
                          border-radius:2px;"></div>
            </div>
            <small style="color:{strength['color']};font-size:11px;">{strength['label']}</small>
            """, unsafe_allow_html=True)

        terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")

        if st.button("Create Free Account", type="primary", use_container_width=True):
            errors = []
            if not full_name:          errors.append("Full name required.")
            if not username:           errors.append("Username required.")
            if not _valid_email(email):errors.append("Valid email required.")
            if len(pw1) < 8:           errors.append("Password min 8 characters.")
            if pw1 != pw2:             errors.append("Passwords do not match.")
            if not terms:              errors.append("Accept Terms of Service.")
            for e in errors: st.error(e)
            if not errors:
                user = UserRepo.create(username=username, email=email, password=pw1,
                                       full_name=full_name, role="user", subscription="free")
                if user is None:
                    st.error("Username or email already taken.")
                else:
                    AuditRepo.log(user.id, "register", f"New user: {username}")
                    linked = TeamRepo.link_pending_invites(email, user.id)
                    if linked:
                        st.session_state["_joined_team_on_signup"] = True
                    _send_otp(user.id, email, full_name)
                    st.session_state.pending_user_id = user.id
                    st.session_state.pending_email   = email
                    st.session_state.auth_view = "verify"
                    st.rerun()

        st.markdown("<hr style='border-color:#252836;margin:16px 0;'/>", unsafe_allow_html=True)
        if st.button("← Back to Sign In", use_container_width=True):
            st.session_state.auth_view = "login"
            st.rerun()


# ---- Email Verification --------------------------------------------

def _send_otp(user_id: int, email: str, name: str) -> bool:
    """Generate + send an OTP. Returns True if actually delivered."""
    otp = generate_otp(6)
    st.session_state.pending_otp = otp
    st.session_state.otp_expires = datetime.utcnow() + timedelta(minutes=15)
    ok, detail = send_verification_email(email, name, otp)
    st.session_state["_last_email_status"] = (ok, detail)
    return ok


def _render_verify_email():
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        email = st.session_state.pending_email
        st.markdown(f"""
        <div style="background:#141720;border:1px solid #252836;border-radius:20px;
                    padding:36px 32px;text-align:center;">
          <div style="font-size:48px;margin-bottom:16px;">📧</div>
          <h2 style="font-family:'Space Grotesk',sans-serif;color:#fff;margin:0 0 8px;">
            Check your inbox</h2>
          <p style="color:#9CA3AF;font-size:14px;margin:0 0 12px;">
            We sent a 6-digit code to <strong style="color:#0AEFFF;">{email}</strong></p>
        </div>
        """, unsafe_allow_html=True)

        ok, detail = st.session_state.get("_last_email_status", (False, ""))
        if ok:
            st.success("Verification email sent successfully.")
        else:
            _email_status_banner()
            with st.expander("Show my code here instead (dev/demo mode)"):
                st.info(
                    "Since no email server is configured, here's your code directly "
                    "so you can continue testing the app:"
                )
                st.code(st.session_state.get("pending_otp", ""), language=None)

        code = st.text_input("Verification Code", placeholder="Enter 6-digit code", max_chars=6)
        if st.button("Verify Email", type="primary", use_container_width=True):
            if not code:
                st.error("Please enter the verification code.")
            elif not st.session_state.otp_expires or datetime.utcnow() > st.session_state.otp_expires:
                st.error("Code expired. Request a new one.")
            elif code.strip() != st.session_state.pending_otp:
                st.error("Incorrect code. Please try again.")
            else:
                uid = st.session_state.pending_user_id
                UserRepo.update_fields(uid, is_email_verified=True, email_verify_token=None)
                NotificationRepo.add(uid, "Email verified! Welcome to LionsylAI.")
                AuditRepo.log(uid, "email_verified", email)
                user = UserRepo.get_by_id(uid)
                if user:
                    _complete_login(user, remember=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Resend Code", use_container_width=True):
                uid  = st.session_state.pending_user_id
                user = UserRepo.get_by_id(uid)
                if user:
                    ok = _send_otp(uid, user.email, user.full_name or user.username)
                    if ok:
                        st.success("New code sent!")
                    else:
                        st.warning("Email not configured - see the code above instead.")
                        st.rerun()
        with c2:
            if st.button("← Back to Login", use_container_width=True):
                st.session_state.auth_view = "login"
                st.rerun()


# ---- Forgot / Reset Password ----------------------------------------

def _render_forgot_password():
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("""
        <div style="background:#141720;border:1px solid #252836;border-radius:20px;
                    padding:36px 32px;text-align:center;">
          <h2 style="font-family:'Space Grotesk',sans-serif;color:#fff;margin:0 0 12px;">
            Reset your password</h2>
          <p style="color:#9CA3AF;font-size:14px;margin:0 0 16px;">
            Enter your email and we'll send a reset link.</p>
        </div>
        """, unsafe_allow_html=True)

        _email_status_banner()
        email = st.text_input("Email Address", placeholder="you@company.com")

        if st.button("Send Reset Link", type="primary", use_container_width=True):
            if not _valid_email(email):
                st.error("Enter a valid email address.")
            else:
                user = UserRepo.get_by_email(email)
                if user:
                    token   = generate_secure_token(48)
                    expires = datetime.utcnow() + timedelta(hours=1)
                    UserRepo.update_verify_token(user.id, token, expires)
                    link = f"{APP_URL}?reset_token={token}"
                    ok, detail = send_password_reset(email, user.full_name or user.username, link)
                    AuditRepo.log(user.id, "password_reset_requested", email)
                    if ok:
                        st.success("Reset link sent! Check your inbox.")
                    else:
                        st.warning(
                            "Email isn't configured on this server, so the link "
                            "couldn't be delivered. Use the link below instead (dev/demo mode):"
                        )
                        st.code(link, language=None)
                else:
                    # Don't reveal whether email exists — but still give a consistent message
                    st.success("If that email is registered, you'll receive a reset link shortly.")

        if st.button("← Back to Login", use_container_width=True):
            st.session_state.auth_view = "login"
            st.rerun()


def _render_reset_password():
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("""
        <div style="background:#141720;border:1px solid #252836;border-radius:20px;
                    padding:36px 32px;">
          <h2 style="font-family:'Space Grotesk',sans-serif;color:#fff;text-align:center;
                     margin:0 0 24px;">Create new password</h2>
        </div>
        """, unsafe_allow_html=True)

        pw1 = st.text_input("New Password",     type="password")
        pw2 = st.text_input("Confirm Password", type="password")
        if st.button("Reset Password", type="primary", use_container_width=True):
            if len(pw1) < 8:
                st.error("Password must be at least 8 characters.")
            elif pw1 != pw2:
                st.error("Passwords do not match.")
            else:
                token = st.session_state.get("reset_token", "")
                from database import get_db, User
                from utils.auth import hash_password
                try:
                    with get_db() as db:
                        u = db.query(User).filter_by(email_verify_token=token).first()
                        if u and u.email_verify_expires and u.email_verify_expires > datetime.utcnow():
                            u.password_hash = hash_password(pw1)
                            u.email_verify_token = None
                            found_uid = u.id
                        else:
                            found_uid = None
                    if found_uid:
                        AuditRepo.log(found_uid, "password_reset_completed", "")
                        st.success("Password reset successfully! Please sign in.")
                        st.session_state.auth_view = "login"
                        st.rerun()
                    else:
                        st.error("Token expired or invalid. Request a new reset link.")
                except Exception as e:
                    st.error(f"Reset failed: {e}")


# ---- Pricing / Checkout ---------------------------------------------

def _render_pricing():
    st.markdown("""
    <div style="text-align:center;padding:32px 0 24px;">
      <h2 style="font-family:'Space Grotesk',sans-serif;font-size:32px;font-weight:800;color:#fff;">
        Simple, transparent pricing</h2>
      <p style="color:#9CA3AF;font-size:16px;">One plan. Everything included. Cancel any time.</p>
    </div>
    """, unsafe_allow_html=True)

    billing_choice = st.radio("Billing", ["Monthly", "Annual (save 17%)"],
                              horizontal=True, label_visibility="collapsed")
    billing = "month" if "Monthly" in billing_choice else "year"

    st.markdown(render_pricing_html(billing, "USD"), unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        if st.button("Continue to Checkout", type="primary", use_container_width=True):
            uid = st.session_state.get("user_id")
            if not uid:
                st.warning("Please sign in before subscribing.")
                st.session_state.auth_view = "login"
                st.rerun()
            else:
                st.session_state.auth_view = "login"
                st.info("Go to Settings → Billing after signing in to complete checkout "
                        "(supports Stripe worldwide and SSLCommerz for Bangladesh).")

    st.markdown("<hr style='border-color:#252836;margin:24px 0;'/>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back to Login", use_container_width=True):
            st.session_state.auth_view = "login"
            st.rerun()
    with c2:
        if st.button("Start Free", use_container_width=True):
            st.session_state.auth_view = "register"
            st.rerun()

    st.markdown("<h3 style='color:#fff;margin-top:32px;'>Frequently Asked Questions</h3>",
                unsafe_allow_html=True)
    faqs = [
        ("Can I cancel at any time?",
         "Yes. Cancel directly from your billing portal — no questions asked."),
        ("What payment methods are accepted?",
         "Cards worldwide via Stripe. In Bangladesh, bKash, Nagad, Rocket and local "
         "cards are also supported via SSLCommerz."),
        ("Is my data secure?",
         "All data is encrypted at rest and in transit. We never share your data."),
        ("Do you offer a free trial?",
         "The free plan gives you access to core features. Upgrade to Pro for everything."),
    ]
    for q, a in faqs:
        with st.expander(q):
            st.write(a)
