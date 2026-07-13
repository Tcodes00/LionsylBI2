"""
LionsylAI - Authentication Utilities
JWT token creation/verification, OTP generation, password helpers, TOTP 2FA.
"""
import secrets
import hashlib
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

try:
    from jose import jwt, JWTError
    JOSE_OK = True
except ImportError:
    JOSE_OK = False

try:
    import bcrypt
    BCRYPT_OK = True
except ImportError:
    BCRYPT_OK = False

try:
    import pyotp
    import qrcode
    import io as _io
    import base64 as _b64
    PYOTP_OK = True
except ImportError:
    PYOTP_OK = False

from config.settings import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES, TOTP_ISSUER_NAME


# ---- Password helpers --------------------------------------------

def hash_password(password: str) -> str:
    if BCRYPT_OK:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    if BCRYPT_OK:
        try:
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except Exception:
            pass
    return hashlib.sha256(plain.encode()).hexdigest() == hashed


def password_strength(pw: str) -> Dict[str, Any]:
    tips = []
    score = 0
    if len(pw) >= 8: score += 1
    else: tips.append("At least 8 characters")
    if any(c.isupper() for c in pw): score += 1
    else: tips.append("Add an uppercase letter")
    if any(c.islower() for c in pw): score += 1
    else: tips.append("Add a lowercase letter")
    if any(c.isdigit() for c in pw): score += 1
    else: tips.append("Add a number")
    if any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in pw): score += 1
    else: tips.append("Add a special character")
    labels = ["Very Weak", "Weak", "Fair", "Strong", "Very Strong"]
    colors = ["#EF4444", "#F97316", "#EAB308", "#22C55E", "#10B981"]
    return {"score": score, "label": labels[min(score, 4)],
            "color": colors[min(score, 4)], "tips": tips}


# ---- OTP / verification codes -------------------------------------

def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def generate_secure_token(length: int = 64) -> str:
    return secrets.token_urlsafe(length)


# ---- JWT -----------------------------------------------------------

def create_access_token(data: Dict[str, Any],
                        expires_minutes: int = JWT_EXPIRE_MINUTES) -> str:
    payload = data.copy()
    if "sub" in payload:
        payload["sub"] = str(payload["sub"])
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
    payload["iat"] = datetime.utcnow()
    if JOSE_OK:
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    import base64, json
    return base64.urlsafe_b64encode(json.dumps(payload, default=str).encode()).decode()


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    if JOSE_OK:
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if data and "sub" in data:
                try: data["sub"] = int(data["sub"])
                except (ValueError, TypeError): pass
            return data
        except JWTError:
            return None
    try:
        import base64, json
        padded = token + "=" * (4 - len(token) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
        exp_raw = payload.get("exp", "")
        if isinstance(exp_raw, str):
            try:
                exp_dt = datetime.fromisoformat(exp_raw)
            except ValueError:
                exp_dt = datetime.strptime(exp_raw[:19], "%Y-%m-%d %H:%M:%S")
        else:
            exp_dt = datetime.utcfromtimestamp(float(exp_raw))
        if exp_dt < datetime.utcnow():
            return None
        if "sub" in payload:
            try: payload["sub"] = int(payload["sub"])
            except (ValueError, TypeError): pass
        return payload
    except Exception:
        return None


# ---- TOTP Two-Factor Authentication --------------------------------

def totp_available() -> bool:
    return PYOTP_OK


def generate_totp_secret() -> str:
    if PYOTP_OK:
        return pyotp.random_base32()
    return secrets.token_hex(16).upper()


def totp_provisioning_uri(secret: str, account_email: str) -> str:
    if not PYOTP_OK:
        return ""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=account_email, issuer_name=TOTP_ISSUER_NAME
    )


def totp_qrcode_base64(uri: str) -> Optional[str]:
    """Return a base64-encoded PNG data URI for embedding via st.image / markdown."""
    if not PYOTP_OK or not uri:
        return None
    try:
        img = qrcode.make(uri)
        buf = _io.BytesIO()
        img.save(buf, format="PNG")
        b64 = _b64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None


def totp_verify(secret: str, code: str) -> bool:
    if not PYOTP_OK or not secret or not code:
        return False
    try:
        return pyotp.totp.TOTP(secret).verify(code.strip(), valid_window=1)
    except Exception:
        return False
