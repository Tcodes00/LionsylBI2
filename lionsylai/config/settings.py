"""
LionsylAI - Centralized Configuration
"""
import os
from dotenv import load_dotenv

# ============ BULLETPROOF .env LOADER ============
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)

POSSIBLE_ENV_PATHS = [
    os.path.join(PROJECT_ROOT, ".env"),
    os.path.join(os.getcwd(), ".env"),
    os.path.join(os.path.expanduser("~"), ".env"),
]

ENV_LOADED = False
for env_path in POSSIBLE_ENV_PATHS:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        ENV_LOADED = True
        print(f"[CONFIG] Loaded .env from: {env_path}")
        break

if not ENV_LOADED:
    load_dotenv()
    print(f"[CONFIG] No .env file found!")

# ---- Helper: safe int from env (handles empty strings) ----
def _int_env(key: str, default: int) -> int:
    val = os.getenv(key, "")
    return int(val) if val.strip() else default

def _str_env(key: str, default: str = "") -> str:
    return os.getenv(key, "") or default

# ---- Application --------------------------------------------
APP_NAME        = _str_env("APP_NAME", "LionsylAI")
APP_ENV         = _str_env("APP_ENV", "development")
APP_URL         = _str_env("APP_URL", "http://localhost:8501")
APP_SECRET_KEY  = _str_env("APP_SECRET_KEY", "dev-secret-change-in-prod-64chars!")

# ---- Database --------------------------------------------------
DB_HOST     = _str_env("DB_HOST", "localhost")
DB_PORT     = _int_env("DB_PORT", 3306)
DB_NAME     = _str_env("DB_NAME", "lionsylai")
DB_USER     = _str_env("DB_USER", "root")
DB_PASSWORD = _str_env("DB_PASSWORD", "")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)
SQLITE_URL = "sqlite:///lionsylai_dev.db"

# ---- Email: SMTP first (real delivery), SendGrid fallback -----
SMTP_HOST       = _str_env("SMTP_HOST", "")
SMTP_PORT       = _int_env("SMTP_PORT", 587)
SMTP_USER       = _str_env("SMTP_USER", "")
SMTP_PASSWORD   = _str_env("SMTP_PASSWORD", "")
SMTP_USE_TLS    = _str_env("SMTP_USE_TLS", "true").lower() == "true"

SENDGRID_API_KEY = _str_env("SENDGRID_API_KEY", "")
FROM_EMAIL       = _str_env("FROM_EMAIL", SMTP_USER or "noreply@lionsylai.com")
FROM_NAME        = _str_env("FROM_NAME", "LionsylAI")

# ---- Payment: Stripe (international) ---------------------------
STRIPE_SECRET_KEY      = _str_env("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = _str_env("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET  = _str_env("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID        = _str_env("STRIPE_PRICE_ID", "")

# ---- Payment: SSLCommerz (Bangladesh - bKash/Nagad/Rocket/Cards) --
SSLCOMMERZ_STORE_ID     = _str_env("SSLCOMMERZ_STORE_ID", "")
SSLCOMMERZ_STORE_PASSWD = _str_env("SSLCOMMERZ_STORE_PASSWD", "")
SSLCOMMERZ_SANDBOX      = _str_env("SSLCOMMERZ_SANDBOX", "true").lower() == "true"
SSLCOMMERZ_API_URL = (
    "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
    if SSLCOMMERZ_SANDBOX else
    "https://securepay.sslcommerz.com/gwprocess/v4/api.php"
)
SSLCOMMERZ_VALIDATION_URL = (
    "https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php"
    if SSLCOMMERZ_SANDBOX else
    "https://securepay.sslcommerz.com/validator/api/validationserverAPI.php"
)

# ---- JWT ---------------------------------------------------------
JWT_SECRET          = _str_env("JWT_SECRET", APP_SECRET_KEY)
JWT_ALGORITHM       = _str_env("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES  = _int_env("JWT_EXPIRE_MINUTES", 60)

# ---- Security: lockout / sessions -------------------------------
LOGIN_LOCKOUT_MAX_ATTEMPTS = _int_env("LOGIN_LOCKOUT_MAX_ATTEMPTS", 5)
LOGIN_LOCKOUT_WINDOW_MIN   = _int_env("LOGIN_LOCKOUT_WINDOW_MIN", 15)
SESSION_DAYS_DEFAULT       = _int_env("SESSION_DAYS_DEFAULT", 1)
SESSION_DAYS_REMEMBER_ME   = _int_env("SESSION_DAYS_REMEMBER_ME", 30)
TOTP_ISSUER_NAME           = _str_env("TOTP_ISSUER_NAME", "LionsylAI")

# ---- Feature Flags -------------------------------------------
ENABLE_2FA           = _str_env("ENABLE_2FA", "true").lower() == "true"
ENABLE_EMAIL_VERIFY  = _str_env("ENABLE_EMAIL_VERIFY", "true").lower() == "true"
ENABLE_PAYMENTS      = _str_env("ENABLE_PAYMENTS", "true").lower() == "true"
MAX_UPLOAD_MB        = _int_env("MAX_UPLOAD_MB", 200)

# ---- Subscription Plans (USD international + BDT Bangladesh) -----
PLANS = {
    "pro": {
        "name":            "Professional",
        "price_month":     49,
        "price_year":      490,
        "price_bdt_month": 1499,
        "price_bdt_year":  14990,
        "currency":        "USD",
        "seats":           5,
        "features": [
            "Unlimited data uploads",
            "All 12 analytics modules",
            "AI-powered predictions",
            "Advanced FP&A automation",
            "Priority email support",
            "Team collaboration (5 seats)",
            "Custom report templates",
            "API access",
            "Monthly executive reports",
        ],
    }
}
FREE_PLAN_SEATS = 1

# ---- Country / payment-method routing -----------------------------
SUPPORTED_COUNTRIES = [
    "Bangladesh", "United States", "United Kingdom", "Canada", "Australia",
    "India", "Singapore", "United Arab Emirates", "Other / International",
]
BD_PAYMENT_METHODS   = ["bKash", "Nagad", "Rocket", "Visa/Mastercard (via SSLCommerz)", "Bank Transfer"]
INTL_PAYMENT_METHODS = ["Visa/Mastercard/Amex (via Stripe)", "Google Pay", "Apple Pay"]

# ---- UI Constants ----------------------------------------------
BRAND_PRIMARY   = "#6C63FF"
BRAND_SECONDARY = "#0AEFFF"
BRAND_ACCENT    = "#FF6B6B"
BRAND_DARK      = "#0D0F14"
BRAND_CARD      = "#141720"
BRAND_BORDER    = "#252836"

SUPPORTED_FORMATS = ["csv", "xlsx", "xls", "xlsm", "json", "parquet", "tsv", "feather"]

TAB_NAMES = [
    "Dashboard", "Profit", "AI Studio", "Strategy",
    "Analytics", "FP&A", "Month-End", "Cash",
    "Integrations", "Team", "Advanced", "Settings",
]