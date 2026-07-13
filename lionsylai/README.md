# 🦁 LionsylAI – Enterprise Analytics Intelligence Platform

> **Production-ready, 2026-grade business intelligence platform built with Streamlit, MySQL, Stripe, SSLCommerz, and SMTP/SendGrid.**

---

## 📁 Project Structure

```
lionsylai/
├── app.py                    # Main Streamlit entry point + persistent session restore
├── database.py               # MySQL + SQLite ORM: users, sessions, teams, billing, 2FA
├── design.py                 # Design system (CSS, HTML components)
├── requirements.txt          # Python dependencies
├── test_all.py               # 74-test end-to-end suite
├── Dockerfile                # Production Docker image
├── docker-compose.yml        # Full-stack deployment (MySQL + Redis + Nginx)
├── .env.example               # Environment variable template
│
├── config/settings.py         # All environment config & constants
│
├── utils/
│   ├── auth.py                 # JWT, OTP, bcrypt, TOTP 2FA (QR codes)
│   ├── email_service.py        # SMTP (Gmail-ready) → SendGrid → dev-mode fallback
│   └── payment.py              # Stripe (world) + SSLCommerz (Bangladesh)
│
├── components/
│   ├── data_engine.py          # Universal loader, cleaner, column detector
│   ├── ml_engine.py            # XGBoost, LightGBM, forecasting, clustering
│   └── fp_engine.py            # FP&A automation, budget, cash, reports
│
├── pages/
│   ├── auth_page.py            # Login (+Remember Me), register, verify, 2FA, reset, pricing
│   ├── dashboard_tab.py .. advanced_tab.py   # Tabs 1–11
│   └── settings_tab.py         # Tab 12: Profile, Security, Billing, Data, Preferences, Email Setup
│
└── scripts/init.sql            # MySQL schema + seed data
```

---

## 🚀 Quick Start (Local Development)

```bash
git clone <your-repo> && cd lionsylai
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Open **http://localhost:8501**. Demo login: `admin` / `Admin@2026!`

---

## ✅ What's New in v2.1 (this release)

| Area | Before | Now |
|---|---|---|
| **Session persistence** | Refreshing the browser logged you out | Login state is stored server-side (`user_sessions` table) and restored via a token in the URL — refresh keeps you signed in |
| **Remember Me** | Not available | Checkbox on login; extends session from 1 day to 30 days |
| **Email verification / reset** | Silently "succeeded" even with no email configured | Honestly reports delivery status; shows the code/link directly in the UI as a fallback when no SMTP/SendGrid is set up |
| **Email delivery** | SendGrid-only, required a paid account | SMTP first (works instantly with a free Gmail App Password), SendGrid as fallback |
| **Team invites** | Added to a list, no email ever sent | Sends a real invitation email; UI clearly states when delivery isn't configured |
| **Team presence** | Static "Active/Away/Inactive" text | Live presence — "Online now", "Active 12m ago" etc, computed from real `last_active` timestamps |
| **Team roles** | N/A | Full roles & permissions matrix (Admin/Manager/Analyst/Viewer/Finance Manager/Developer) |
| **Payments** | Stripe only, silently faked success when unconfigured | Stripe (worldwide) **and** SSLCommerz (bKash/Nagad/Rocket/cards for Bangladesh), country-aware routing, real transaction history |
| **2FA** | Not available | TOTP-based (Google Authenticator/Authy compatible) with QR code setup |
| **Brute-force protection** | Not available | Login lockout after 5 failed attempts within 15 minutes |
| **Active sessions** | Not available | View and revoke individual signed-in devices from Settings → Security |

### How email delivery works now
1. If `SMTP_HOST` + `SMTP_USER` + `SMTP_PASSWORD` are set → sends via SMTP (works with Gmail, Outlook, Zoho, Amazon SES, etc.)
2. Else if `SENDGRID_API_KEY` is set → sends via SendGrid
3. Else → **honestly tells the user** delivery isn't configured, and — for verification codes and reset links only — shows the value directly in the UI so the demo/dev flow still works end-to-end.

Set this up in **Settings → Email Setup** inside the app for step-by-step Gmail instructions, or see `.env.example`.

### How payments work now
- **International**: Stripe Checkout, routed automatically when the selected country isn't Bangladesh.
- **Bangladesh**: SSLCommerz gateway supporting bKash, Nagad, Rocket, local Visa/Mastercard, and bank transfer, with BDT pricing (৳1,499/mo or ৳14,990/yr).
- If neither gateway is configured, the app clearly labels it and offers a demo upgrade (no real charge) so development/testing isn't blocked.
- All successful payments — real or demo — are recorded in `transactions` and shown in Settings → Billing → Invoice History.

---

## 🐳 Production Deployment (Docker)

```bash
cp .env.example .env   # fill in DB, SMTP, Stripe/SSLCommerz keys
mkdir -p nginx/ssl && cp your_cert.pem nginx/ssl/cert.pem && cp your_key.pem nginx/ssl/key.pem
docker-compose up -d
docker-compose logs -f app
```

---

## ⚙️ Environment Variables (key additions)

| Variable | Required | Description |
|---|---|---|
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | For real email | Gmail/Outlook/any SMTP provider |
| `SENDGRID_API_KEY` | Alt. to SMTP | SendGrid fallback |
| `STRIPE_SECRET_KEY` / `STRIPE_PRICE_ID` | For international payments | Stripe |
| `SSLCOMMERZ_STORE_ID` / `SSLCOMMERZ_STORE_PASSWD` | For Bangladesh payments | SSLCommerz (free sandbox at merchant.sslcommerz.com) |
| `LOGIN_LOCKOUT_MAX_ATTEMPTS` | No (default 5) | Failed logins before temporary lockout |
| `SESSION_DAYS_REMEMBER_ME` | No (default 30) | Days a "Remember Me" session lasts |
| `TOTP_ISSUER_NAME` | No (default LionsylAI) | Name shown in authenticator apps |

Full list in `.env.example`.

---

## 📊 Feature Overview

### 12 Analytics Modules
Dashboard · Profit Analytics · AI Studio (XGBoost/LightGBM/SARIMA/clustering) ·
Strategic Insights · Advanced Analytics · FP&A Automation · Month-End Close ·
Cash Management · Integrations · **Team Collaboration (enterprise-grade)** ·
Advanced Mode · **Settings (Security/Billing/Email Setup)**

### Authentication & Security
- Email + password with bcrypt hashing
- 6-digit email verification OTP with in-UI fallback
- Password reset via email link with in-UI fallback
- **Persistent sessions surviving browser refresh**
- **Remember Me (30-day sessions)**
- **TOTP 2FA with QR code setup**
- **Brute-force lockout (5 attempts / 15 min)**
- **Active session management (view & revoke devices)**
- Full audit trail

### Subscription & Payments
- Free plan (1 seat) and Pro plan (5 seats, $49/mo or ৳1,499/mo)
- **Stripe** for international cards
- **SSLCommerz** for Bangladesh (bKash, Nagad, Rocket, local cards)
- Country-aware pricing and gateway routing
- Billing history / invoices per user

### Team Collaboration
- Real invitation emails
- **Live presence** ("Online now" / "Active 12m ago")
- Seat-limit enforcement based on plan
- Full **roles & permissions matrix**
- Shared reports, comments, notifications, audit trail

---

## 🛠 Tech Stack

Streamlit 1.35 · Python 3.11 · XGBoost/LightGBM/scikit-learn/statsmodels ·
MySQL 8 / SQLite fallback · SQLAlchemy 2.0 · bcrypt + python-jose (JWT) +
**pyotp/qrcode (2FA)** · SMTP/SendGrid · **Stripe + SSLCommerz** ·
Plotly · Pandas/NumPy · Nginx · Docker

---

## ✅ Test Suite

```bash
python test_all.py
```

74 tests covering: config, database CRUD, session persistence & Remember Me,
login lockout, email delivery honesty, Stripe/SSLCommerz configuration,
TOTP 2FA, team invite + live presence, ML training/forecasting/clustering,
FP&A engine, auto-clean pipeline, and syntax validation for every page.

---

© 2026 LionsylAI. All rights reserved.
