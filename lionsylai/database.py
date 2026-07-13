"""
LionsylAI - Database Layer
Primary: MySQL via SQLAlchemy (connection-pooled, thread-safe)
Fallback: SQLite for development / demo
All schema creation, migrations, and CRUD helpers live here.
"""
from __future__ import annotations
import logging, secrets
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

log = logging.getLogger("lionsylai.db")

try:
    from sqlalchemy import (
        create_engine, text, pool,
        Column, Integer, String, Boolean, Text, DateTime, Float, ForeignKey,
    )
    from sqlalchemy.orm import declarative_base, sessionmaker, Session
    from sqlalchemy.exc import OperationalError, IntegrityError
    SQLALCHEMY_OK = True
except ImportError:
    SQLALCHEMY_OK = False

from config.settings import DATABASE_URL, SQLITE_URL, APP_ENV

def _build_engine():
    if not SQLALCHEMY_OK:
        return None, True
    try:
        engine = create_engine(
            DATABASE_URL, pool_size=10, max_overflow=20, pool_timeout=30,
            pool_recycle=3600, pool_pre_ping=True, echo=False,
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log.info("MySQL connection established")
        return engine, False
    except Exception as e:
        log.warning(f"MySQL unavailable ({e}), falling back to SQLite")
    fallback = create_engine(
        SQLITE_URL, connect_args={"check_same_thread": False},
        poolclass=pool.StaticPool, echo=False,
    )
    log.info("SQLite fallback active")
    return fallback, True

engine, _using_sqlite = _build_engine()

if SQLALCHEMY_OK and engine:
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base = declarative_base()
else:
    SessionLocal = None
    Base = None


# ---- ORM Models ------------------------------------------------

if SQLALCHEMY_OK and Base is not None:

    class User(Base):
        __tablename__ = "users"
        id                      = Column(Integer, primary_key=True, autoincrement=True)
        username                = Column(String(80),  unique=True, nullable=False, index=True)
        email                   = Column(String(120), unique=True, nullable=False, index=True)
        password_hash           = Column(String(256), nullable=False)
        full_name               = Column(String(120), nullable=True)
        org_name                = Column(String(150), nullable=True)
        role                    = Column(String(20), default="user")
        subscription            = Column(String(20), default="free")
        is_active               = Column(Boolean, default=True)
        is_email_verified       = Column(Boolean, default=False)
        email_verify_token      = Column(String(128), nullable=True)
        email_verify_expires    = Column(DateTime, nullable=True)
        two_fa_secret           = Column(String(64), nullable=True)
        two_fa_enabled          = Column(Boolean, default=False)
        stripe_customer_id      = Column(String(64), nullable=True)
        stripe_sub_id           = Column(String(64), nullable=True)
        sub_expires_at          = Column(DateTime, nullable=True)
        avatar_url              = Column(String(256), nullable=True)
        preferences_json        = Column(Text, nullable=True)
        # Which paid account this login belongs to. NULL = this user IS the
        # account (a paying owner, or a solo free user). Set = this user is
        # one of that account's seats; their effective plan, seat count, and
        # workspace all come from the account row, not from this one.
        account_owner_id        = Column(Integer, ForeignKey("users.id"), nullable=True)
        manual_status            = Column(String(20), nullable=True)
        created_at              = Column(DateTime, default=datetime.utcnow)
        last_login               = Column(DateTime, nullable=True)
        last_seen                = Column(DateTime, nullable=True)

    class TeamMember(Base):
        __tablename__ = "team_members"
        id              = Column(Integer, primary_key=True, autoincrement=True)
        user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
        name            = Column(String(120), nullable=False)
        email           = Column(String(120), nullable=False)
        role            = Column(String(60), default="Analyst")
        status          = Column(String(20), default="Active")
        is_owner        = Column(Boolean, default=False)
        # Real account link: set once the invited email actually registers/logs in.
        # Until then this member is a name-only placeholder with no real activity.
        member_user_id  = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
        last_active     = Column(DateTime, default=datetime.utcnow)
        created_at      = Column(DateTime, default=datetime.utcnow)

    class Integration(Base):
        __tablename__ = "integrations"
        id           = Column(Integer, primary_key=True, autoincrement=True)
        user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
        name         = Column(String(120), nullable=False)
        itype        = Column(String(60), nullable=False)
        status       = Column(String(30), default="Not Configured")
        api_endpoint = Column(String(256), nullable=True)
        api_key_enc  = Column(Text, nullable=True)
        success_rate = Column(Float, default=0.0)
        last_sync    = Column(DateTime, nullable=True)
        sync_freq    = Column(String(20), default="Daily")
        created_at   = Column(DateTime, default=datetime.utcnow)

    class Report(Base):
        __tablename__ = "reports"
        id          = Column(Integer, primary_key=True, autoincrement=True)
        user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
        name        = Column(String(200), nullable=False)
        rtype       = Column(String(60), nullable=False)
        status      = Column(String(30), default="Generated")
        description = Column(Text, nullable=True)
        data_json   = Column(Text, nullable=True)
        file_size   = Column(String(20), default="0 KB")
        created_at  = Column(DateTime, default=datetime.utcnow)

    class SharedReport(Base):
        __tablename__ = "shared_reports"
        id             = Column(Integer, primary_key=True, autoincrement=True)
        report_id      = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
        owner_id       = Column(Integer, ForeignKey("users.id",   ondelete="CASCADE"), nullable=False)
        shared_with_id = Column(Integer, ForeignKey("users.id",   ondelete="CASCADE"), nullable=False)
        permission     = Column(String(20), default="view")
        created_at     = Column(DateTime, default=datetime.utcnow)

    class Comment(Base):
        __tablename__ = "comments"
        id           = Column(Integer, primary_key=True, autoincrement=True)
        report_id    = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
        user_id      = Column(Integer, ForeignKey("users.id",   ondelete="CASCADE"), nullable=False)
        comment_text = Column(Text, nullable=False)
        ctype        = Column(String(30), default="General")
        urgency      = Column(String(20), default="Low")
        created_at   = Column(DateTime, default=datetime.utcnow)

    class Notification(Base):
        __tablename__ = "notifications"
        id         = Column(Integer, primary_key=True, autoincrement=True)
        user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
        message    = Column(Text, nullable=False)
        ntype      = Column(String(30), default="info")
        is_read    = Column(Boolean, default=False)
        created_at = Column(DateTime, default=datetime.utcnow)

    class AuditLog(Base):
        __tablename__ = "audit_logs"
        id         = Column(Integer, primary_key=True, autoincrement=True)
        user_id    = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
        action     = Column(String(80), nullable=False)
        details    = Column(Text, nullable=True)
        ip_address = Column(String(45), nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)

    class BudgetSnapshot(Base):
        __tablename__ = "budget_snapshots"
        id          = Column(Integer, primary_key=True, autoincrement=True)
        user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
        name        = Column(String(120), nullable=False)
        fiscal_year = Column(Integer, nullable=False)
        currency    = Column(String(10), default="USD")
        data_json   = Column(Text, nullable=False)
        created_at  = Column(DateTime, default=datetime.utcnow)
        updated_at  = Column(DateTime, default=datetime.utcnow)

    class UserSession(Base):
        __tablename__ = "user_sessions"
        id          = Column(Integer, primary_key=True, autoincrement=True)
        user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
        token       = Column(String(128), unique=True, nullable=False, index=True)
        remember_me = Column(Boolean, default=False)
        user_agent  = Column(String(256), nullable=True)
        ip_address  = Column(String(45), nullable=True)
        created_at  = Column(DateTime, default=datetime.utcnow)
        expires_at  = Column(DateTime, nullable=False)
        last_seen   = Column(DateTime, default=datetime.utcnow)

    class LoginAttempt(Base):
        __tablename__ = "login_attempts"
        id         = Column(Integer, primary_key=True, autoincrement=True)
        identifier = Column(String(120), nullable=False, index=True)
        success    = Column(Boolean, default=False)
        ip_address = Column(String(45), nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)

    class Transaction(Base):
        __tablename__ = "transactions"
        id            = Column(Integer, primary_key=True, autoincrement=True)
        user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
        gateway       = Column(String(30), nullable=False)
        amount        = Column(Float, nullable=False)
        currency      = Column(String(10), default="USD")
        status        = Column(String(20), default="completed")
        plan          = Column(String(30), default="pro")
        billing_cycle = Column(String(10), default="month")
        reference     = Column(String(120), nullable=True)
        created_at    = Column(DateTime, default=datetime.utcnow)


# ---- Plain dataclasses (session-safe) --------------------------

@dataclass
class UserData:
    id: int
    username: str
    email: str
    full_name: str
    role: str
    subscription: str
    is_active: bool
    is_email_verified: bool
    org_name: str = ""
    two_fa_enabled: bool = False
    two_fa_secret: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_sub_id: Optional[str] = None
    email_verify_token: Optional[str] = None
    email_verify_expires: Optional[datetime] = None
    password_hash: str = ""
    last_seen: Optional[datetime] = None
    preferences: dict = field(default_factory=dict)
    manual_status: Optional[str] = None
    account_owner_id: Optional[int] = None

@dataclass
class TeamMemberData:
    id: int
    user_id: int
    name: str
    email: str
    role: str
    status: str
    is_owner: bool = False
    last_active: Optional[datetime] = None
    member_user_id: Optional[int] = None

@dataclass
class IntegrationData:
    id: int
    user_id: int
    name: str
    itype: str
    status: str
    success_rate: float
    last_sync: Optional[datetime] = None
    sync_freq: str = "Daily"
    api_endpoint: Optional[str] = None

@dataclass
class NotificationData:
    id: int
    user_id: int
    message: str
    ntype: str
    is_read: bool
    created_at: Optional[datetime] = None

@dataclass
class AuditData:
    id: int
    user_id: Optional[int]
    action: str
    details: str
    ip_address: str
    created_at: Optional[datetime] = None
    username: str = "System"

@dataclass
class CommentData:
    id: int
    report_id: int
    user_id: int
    comment_text: str
    ctype: str
    urgency: str
    created_at: Optional[datetime] = None
    username: str = "User"

@dataclass
class SessionData:
    id: int
    user_id: int
    token: str
    remember_me: bool
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    user_agent: str = ""
    ip_address: str = ""

@dataclass
class TransactionData:
    id: int
    user_id: int
    gateway: str
    amount: float
    currency: str
    status: str
    plan: str
    billing_cycle: str
    reference: str = ""
    created_at: Optional[datetime] = None


# ---- Session context manager -----------------------------------

@contextmanager
def get_db():
    if SessionLocal is None:
        raise RuntimeError("Database not initialised")
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _run_light_migrations():
    """
    Add newly-introduced columns to tables that may already exist from a prior
    version, without pulling in a full migration framework. Safe to call every
    boot: it only ever ADDs a missing column, never touches existing data.
    Works the same way against MySQL and the SQLite fallback.
    """
    if engine is None:
        return
    try:
        from sqlalchemy import inspect as sa_inspect
        insp = sa_inspect(engine)
        tables = set(insp.get_table_names())

        wanted = {
            "team_members": [("member_user_id", "INTEGER")],
            "users":        [("preferences_json", "TEXT"), ("manual_status", "VARCHAR(20)"),
                              ("account_owner_id", "INTEGER")],
        }
        for table, cols in wanted.items():
            if table not in tables:
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for col_name, col_type in cols:
                if col_name in existing:
                    continue
                with engine.connect() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                log.info(f"Migrated: {table}.{col_name} added")
    except Exception as e:
        log.warning(f"Light migration skipped: {e}")


def init_db() -> bool:
    if engine is None:
        log.error("No DB engine available")
        return False
    try:
        if Base is not None:
            Base.metadata.create_all(bind=engine)
        _run_light_migrations()
        _seed_defaults()
        log.info("Database schema ready")
        return True
    except Exception as e:
        log.error(f"Schema creation error: {e}")
        return False


def resolve_session_workspace(user_id: int) -> dict:
    """
    Given a freshly-authenticated user, figure out which workspace their
    session should operate in for shared team data (roster, comments,
    audit trail); which paid plan, seat count, and org name actually apply
    to them (their own if they're an account owner, or their account's if
    they're a seat under someone else's paid plan - a seat doesn't have its
    own subscription, it inherits the account's); and preload their saved
    preferences (chart palette, currency, etc.) so the app's theme and
    settings are correct from the very first render.
    """
    user = UserRepo.get_by_id(user_id)
    membership = TeamRepo.get_membership_for_user(user_id)

    # account_owner_id on the user row is the direct, canonical answer.
    # Fall back to the team_members join for rows linked before that column
    # existed, so nothing already-working breaks.
    account_owner_id = (user.account_owner_id if user and user.account_owner_id
                         else (membership.user_id if membership else None))

    if account_owner_id:
        owner = UserRepo.get_by_id(account_owner_id)
        ctx = {
            "workspace_owner_id": account_owner_id,
            "is_team_member": True,
            "team_role": membership.role if membership else "Member",
            "subscription": owner.subscription if owner else (user.subscription if user else "free"),
            "org_name": owner.org_name if owner else (user.org_name if user else None),
        }
    else:
        ctx = {
            "workspace_owner_id": user_id,
            "is_team_member": False,
            "team_role": "Owner",
            "subscription": user.subscription if user else "free",
            "org_name": user.org_name if user else None,
        }

    if user and user.preferences:
        ctx.update(user.preferences)
    return ctx


def _seed_defaults():
    import bcrypt
    try:
        with get_db() as db:
            existing = db.query(User).filter_by(username="admin").first()
            if not existing:
                pw_hash = bcrypt.hashpw(b"Admin@2026!", bcrypt.gensalt()).decode()
                admin = User(
                    username="admin", email="admin@lionsylai.com",
                    password_hash=pw_hash, full_name="System Admin",
                    org_name="LionsylAI HQ",
                    role="admin", subscription="pro",
                    is_active=True, is_email_verified=True,
                )
                db.add(admin)
                db.flush()
                admin_id = admin.id
                for name, itype, status, rate in [
                    ("ERP System","ERP","Active",99.8),
                    ("CRM Platform","CRM","Active",98.5),
                    ("Banking API","Banking","Needs Attention",95.2),
                    ("Payment Processor","Payment","Active",99.9),
                ]:
                    db.add(Integration(user_id=admin_id, name=name, itype=itype,
                                       status=status, success_rate=rate))
                for n, e, r, s in [
                    ("Sarah Chen","sarah@lionsylai.com","Finance Manager","Active"),
                    ("Mike Rodriguez","mike@lionsylai.com","Analyst","Away"),
                    ("Jessica Wong","jessica@lionsylai.com","Viewer","Inactive"),
                ]:
                    db.add(TeamMember(user_id=admin_id, name=n, email=e, role=r, status=s))
    except Exception as e:
        log.warning(f"Seed skipped: {e}")


# ---- User Repo ---------------------------------------------------

class UserRepo:

    @staticmethod
    def _to_data(u) -> UserData:
        import json
        prefs = {}
        raw = getattr(u, "preferences_json", None)
        if raw:
            try:
                prefs = json.loads(raw) or {}
            except Exception:
                prefs = {}
        return UserData(
            id=u.id, username=u.username, email=u.email,
            full_name=u.full_name or "", org_name=u.org_name or f"{u.username}'s Workspace",
            role=u.role, subscription=u.subscription,
            is_active=u.is_active, is_email_verified=u.is_email_verified,
            two_fa_enabled=bool(u.two_fa_enabled), two_fa_secret=u.two_fa_secret,
            stripe_customer_id=u.stripe_customer_id, stripe_sub_id=u.stripe_sub_id,
            email_verify_token=u.email_verify_token, email_verify_expires=u.email_verify_expires,
            password_hash=u.password_hash, last_seen=u.last_seen,
            preferences=prefs, manual_status=getattr(u, "manual_status", None),
            account_owner_id=getattr(u, "account_owner_id", None),
        )

    @staticmethod
    def create(username, email, password, full_name="", role="user", subscription="free") -> Optional[UserData]:
        import bcrypt
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        try:
            with get_db() as db:
                user = User(username=username, email=email, password_hash=pw_hash,
                           full_name=full_name, org_name=f"{full_name or username}'s Workspace",
                           role=role, subscription=subscription)
                db.add(user); db.flush(); uid = user.id
            return UserRepo.get_by_id(uid)
        except IntegrityError:
            return None
        except Exception as e:
            log.error(f"UserRepo.create error: {e}"); return None

    @staticmethod
    def create_team_member_account(email: str, full_name: str, org_name: str, account_owner_id: int):
        """
        Provision a real, immediately-usable login for someone being added
        to a team, for when the invited email doesn't already have an
        account. Returns (UserData, temp_password) - the plaintext password
        is generated here and returned exactly once for the owner to hand
        off; only its bcrypt hash is ever stored. Email verification is
        skipped, since the workspace owner is vouching for this address
        directly rather than it being a public self-signup. account_owner_id
        is set immediately, so this seat's plan/org/seat-count all come from
        the paying account from the moment it exists - not inferred later.
        """
        import secrets, string, re as _re
        base = _re.sub(r"[^a-zA-Z0-9_]", "", email.split("@")[0])[:20] or "user"
        for attempt in range(6):
            candidate = base if attempt == 0 else f"{base}{secrets.randbelow(9000) + 1000}"
            parts = [secrets.choice(string.ascii_uppercase), secrets.choice(string.ascii_lowercase),
                     secrets.choice(string.digits), secrets.choice("!@#$%")]
            parts += [secrets.choice(string.ascii_letters + string.digits) for _ in range(8)]
            secrets.SystemRandom().shuffle(parts)
            temp_password = "".join(parts)
            user = UserRepo.create(candidate, email, temp_password, full_name)
            if user:
                UserRepo.update_fields(user.id, is_email_verified=True, org_name=org_name,
                                        account_owner_id=account_owner_id)
                return UserRepo.get_by_id(user.id), temp_password
        return None, None

    @staticmethod
    def verify(username_or_email: str, password: str) -> Optional[UserData]:
        import bcrypt
        try:
            with get_db() as db:
                user = (db.query(User)
                        .filter((User.username == username_or_email) | (User.email == username_or_email))
                        .filter_by(is_active=True).first())
                if not user: return None
                if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
                    return None
                user.last_login = datetime.utcnow()
                user.last_seen  = datetime.utcnow()
                return UserRepo._to_data(user)
        except Exception as e:
            log.error(f"UserRepo.verify error: {e}"); return None

    @staticmethod
    def get_by_id(user_id: int) -> Optional[UserData]:
        try:
            with get_db() as db:
                u = db.query(User).filter_by(id=user_id).first()
                return UserRepo._to_data(u) if u else None
        except Exception as e:
            log.error(f"UserRepo.get_by_id error: {e}"); return None

    @staticmethod
    def get_by_email(email: str) -> Optional[UserData]:
        try:
            with get_db() as db:
                u = db.query(User).filter_by(email=email).first()
                return UserRepo._to_data(u) if u else None
        except Exception as e:
            log.error(f"UserRepo.get_by_email error: {e}"); return None

    @staticmethod
    def update_fields(user_id: int, **kwargs) -> bool:
        try:
            with get_db() as db:
                u = db.query(User).filter_by(id=user_id).first()
                if u:
                    for k, v in kwargs.items():
                        setattr(u, k, v)
            return True
        except Exception as e:
            log.error(f"UserRepo.update_fields error: {e}"); return False

    @staticmethod
    def touch_last_seen(user_id: int):
        try:
            with get_db() as db:
                u = db.query(User).filter_by(id=user_id).first()
                if u: u.last_seen = datetime.utcnow()
        except Exception:
            pass

    @staticmethod
    def update_verify_token(user_id: int, token: str, expires: datetime):
        UserRepo.update_fields(user_id, email_verify_token=token, email_verify_expires=expires)

    @staticmethod
    def verify_email_token(token: str) -> bool:
        try:
            with get_db() as db:
                u = db.query(User).filter_by(email_verify_token=token).first()
                if u and u.email_verify_expires and u.email_verify_expires > datetime.utcnow():
                    u.is_email_verified = True; u.email_verify_token = None
                    return True
            return False
        except Exception as e:
            log.error(f"verify_email_token error: {e}"); return False

    @staticmethod
    def enable_2fa(user_id: int, secret: str):
        UserRepo.update_fields(user_id, two_fa_secret=secret, two_fa_enabled=True)

    @staticmethod
    def disable_2fa(user_id: int):
        UserRepo.update_fields(user_id, two_fa_secret=None, two_fa_enabled=False)

    @staticmethod
    def save_preferences(user_id: int, prefs: dict) -> bool:
        import json
        try:
            return UserRepo.update_fields(user_id, preferences_json=json.dumps(prefs or {}))
        except Exception as e:
            log.error(f"UserRepo.save_preferences error: {e}"); return False

    @staticmethod
    def set_manual_status(user_id: int, status: Optional[str]) -> bool:
        """status is one of 'Online'/'Away'/'Busy'/'Offline', or None to go
        back to automatic (based on real activity)."""
        try:
            return UserRepo.update_fields(user_id, manual_status=status)
        except Exception as e:
            log.error(f"UserRepo.set_manual_status error: {e}"); return False

    @staticmethod
    def set_manual_status(user_id: int, status: Optional[str]) -> bool:
        """status is one of MANUAL_STATUSES, or None to go back to automatic
        (presence inferred from actual last-seen activity)."""
        try:
            return UserRepo.update_fields(user_id, manual_status=status)
        except Exception as e:
            log.error(f"UserRepo.set_manual_status error: {e}"); return False


class TeamRepo:
    @staticmethod
    def list_for_user(user_id: int) -> List[TeamMemberData]:
        try:
            with get_db() as db:
                rows = db.query(TeamMember).filter_by(user_id=user_id).all()
                return [TeamMemberData(id=m.id, user_id=m.user_id, name=m.name, email=m.email,
                        role=m.role, status=m.status, is_owner=bool(m.is_owner),
                        last_active=m.last_active, member_user_id=m.member_user_id) for m in rows]
        except Exception as e:
            log.error(f"TeamRepo.list error: {e}"); return []

    @staticmethod
    def get_by_email(user_id: int, email: str) -> Optional[TeamMemberData]:
        try:
            with get_db() as db:
                m = db.query(TeamMember).filter_by(user_id=user_id, email=email).first()
                if m:
                    return TeamMemberData(id=m.id, user_id=m.user_id, name=m.name, email=m.email,
                        role=m.role, status=m.status, is_owner=bool(m.is_owner),
                        last_active=m.last_active, member_user_id=m.member_user_id)
            return None
        except Exception:
            return None

    @staticmethod
    def add(user_id, name, email, role, status, is_owner=False, member_user_id=None) -> bool:
        try:
            with get_db() as db:
                db.add(TeamMember(user_id=user_id, name=name, email=email,
                                  role=role, status=status, is_owner=is_owner,
                                  member_user_id=member_user_id))
            return True
        except Exception as e:
            log.error(f"TeamRepo.add error: {e}"); return False

    @staticmethod
    def get_membership_for_user(user_id: int) -> Optional[TeamMemberData]:
        """Is this real, logged-in user a linked member of someone else's workspace?
        Returns their most recent linked membership row, or None if they only
        operate under their own account (they're an owner, not a member)."""
        try:
            with get_db() as db:
                m = (db.query(TeamMember).filter_by(member_user_id=user_id)
                     .order_by(TeamMember.created_at.desc()).first())
                if m:
                    return TeamMemberData(id=m.id, user_id=m.user_id, name=m.name, email=m.email,
                        role=m.role, status=m.status, is_owner=bool(m.is_owner),
                        last_active=m.last_active, member_user_id=m.member_user_id)
            return None
        except Exception as e:
            log.error(f"TeamRepo.get_membership_for_user error: {e}"); return None

    @staticmethod
    def link_pending_invites(email: str, user_id: int) -> int:
        """Called right after a new account is created. If this email was
        already invited to one or more teams, connect those placeholder rows
        to the real account so presence/activity becomes genuine instead of
        a static invite record. Returns how many invites were linked."""
        linked = 0
        try:
            with get_db() as db:
                rows = (db.query(TeamMember)
                        .filter(TeamMember.email.ilike(email), TeamMember.member_user_id.is_(None))
                        .all())
                for m in rows:
                    m.member_user_id = user_id
                    if m.status == "Invited":
                        m.status = "Active"
                    m.last_active = datetime.utcnow()
                    linked += 1
                    if linked == 1:
                        # First (primary) workspace this account belongs to -
                        # this is what its effective plan/seats/org come from.
                        u = db.query(User).filter(User.id == user_id).first()
                        if u and not u.account_owner_id:
                            u.account_owner_id = m.user_id
        except Exception as e:
            log.error(f"TeamRepo.link_pending_invites error: {e}")
        return linked

    @staticmethod
    def member_user_ids_for_workspace(owner_id: int) -> List[int]:
        """Every real, linked account that belongs to this workspace (the
        owner plus any team members who have actually registered/logged in).
        Used to scope shared comments/notifications/audit trail to this team
        only, instead of leaking across unrelated workspaces."""
        ids = [owner_id]
        try:
            with get_db() as db:
                rows = (db.query(TeamMember.member_user_id)
                        .filter(TeamMember.user_id == owner_id,
                                TeamMember.member_user_id.isnot(None)).all())
                ids.extend(r[0] for r in rows)
        except Exception as e:
            log.error(f"TeamRepo.member_user_ids_for_workspace error: {e}")
        return ids

    @staticmethod
    def update(member_id, **kwargs) -> bool:
        try:
            with get_db() as db:
                m = db.query(TeamMember).filter_by(id=member_id).first()
                if m:
                    for k, v in kwargs.items(): setattr(m, k, v)
                    if "last_active" not in kwargs:
                        m.last_active = datetime.utcnow()
            return True
        except Exception as e:
            log.error(f"TeamRepo.update error: {e}"); return False

    @staticmethod
    def touch(member_id: int):
        TeamRepo.update(member_id, last_active=datetime.utcnow())

    @staticmethod
    def delete(member_id: int) -> bool:
        try:
            with get_db() as db:
                m = db.query(TeamMember).filter_by(id=member_id).first()
                if m: db.delete(m)
            return True
        except Exception as e:
            log.error(f"TeamRepo.delete error: {e}"); return False

    @staticmethod
    def count_for_user(user_id: int) -> int:
        try:
            with get_db() as db:
                return db.query(TeamMember).filter_by(user_id=user_id).count()
        except Exception:
            return 0


class IntegrationRepo:
    @staticmethod
    def list_for_user(user_id: int) -> List[IntegrationData]:
        try:
            with get_db() as db:
                rows = db.query(Integration).filter_by(user_id=user_id).all()
                return [IntegrationData(id=i.id, user_id=i.user_id, name=i.name, itype=i.itype,
                        status=i.status, success_rate=i.success_rate or 0.0, last_sync=i.last_sync,
                        sync_freq=i.sync_freq or "Daily", api_endpoint=i.api_endpoint) for i in rows]
        except Exception as e:
            log.error(f"IntegrationRepo.list error: {e}"); return []

    @staticmethod
    def add(user_id, name, itype, status="Testing", api_endpoint="", sync_freq="Daily") -> bool:
        try:
            with get_db() as db:
                db.add(Integration(user_id=user_id, name=name, itype=itype, status=status,
                                   api_endpoint=api_endpoint, sync_freq=sync_freq))
            return True
        except Exception as e:
            log.error(f"IntegrationRepo.add error: {e}"); return False

    @staticmethod
    def update(int_id, **kwargs) -> bool:
        try:
            with get_db() as db:
                i = db.query(Integration).filter_by(id=int_id).first()
                if i:
                    for k, v in kwargs.items(): setattr(i, k, v)
                    i.last_sync = datetime.utcnow()
            return True
        except Exception as e:
            log.error(f"IntegrationRepo.update error: {e}"); return False


class ReportRepo:
    @staticmethod
    def list_for_user(user_id: int) -> list:
        try:
            with get_db() as db:
                return [{"id": r.id, "name": r.name, "rtype": r.rtype, "status": r.status,
                         "description": r.description or "", "file_size": r.file_size,
                         "created_at": str(r.created_at)[:10] if r.created_at else ""}
                        for r in db.query(Report).filter_by(user_id=user_id)
                                  .order_by(Report.created_at.desc()).all()]
        except Exception as e:
            log.error(f"ReportRepo.list error: {e}"); return []

    @staticmethod
    def create(user_id, name, rtype, description="", data_json="") -> Optional[int]:
        try:
            with get_db() as db:
                r = Report(user_id=user_id, name=name, rtype=rtype,
                          description=description, data_json=data_json)
                db.add(r); db.flush(); return r.id
        except Exception as e:
            log.error(f"ReportRepo.create error: {e}"); return None

    @staticmethod
    def update_status(report_id, status):
        try:
            with get_db() as db:
                r = db.query(Report).filter_by(id=report_id).first()
                if r: r.status = status
        except Exception as e:
            log.error(f"ReportRepo.update_status error: {e}")


class NotificationRepo:
    @staticmethod
    def add(user_id, message, ntype="info"):
        try:
            with get_db() as db:
                db.add(Notification(user_id=user_id, message=message, ntype=ntype))
        except Exception as e:
            log.error(f"NotificationRepo.add error: {e}")

    @staticmethod
    def list_unread(user_id, limit=20) -> List[NotificationData]:
        try:
            with get_db() as db:
                rows = (db.query(Notification).filter_by(user_id=user_id)
                        .order_by(Notification.created_at.desc()).limit(limit).all())
                return [NotificationData(id=n.id, user_id=n.user_id, message=n.message,
                        ntype=n.ntype, is_read=n.is_read, created_at=n.created_at) for n in rows]
        except Exception as e:
            log.error(f"NotificationRepo.list error: {e}"); return []

    @staticmethod
    def mark_read(notif_id):
        try:
            with get_db() as db:
                n = db.query(Notification).filter_by(id=notif_id).first()
                if n: n.is_read = True
        except Exception as e:
            log.error(f"NotificationRepo.mark_read error: {e}")

    @staticmethod
    def mark_all_read(user_id):
        try:
            with get_db() as db:
                db.query(Notification).filter_by(user_id=user_id, is_read=False).update({"is_read": True})
        except Exception as e:
            log.error(f"NotificationRepo.mark_all_read error: {e}")


class AuditRepo:
    @staticmethod
    def log(user_id, action, details="", ip=""):
        try:
            with get_db() as db:
                db.add(AuditLog(user_id=user_id, action=action, details=details, ip_address=ip))
        except Exception:
            pass

    @staticmethod
    def list_recent(user_id=None, limit=50) -> List[AuditData]:
        try:
            with get_db() as db:
                q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
                if isinstance(user_id, (list, tuple, set)):
                    ids = list(user_id)
                    if ids:
                        q = q.filter(AuditLog.user_id.in_(ids))
                elif user_id:
                    q = q.filter_by(user_id=user_id)
                rows = q.limit(limit).all()
                result = []
                for a in rows:
                    uname = "System"
                    if a.user_id:
                        u = db.query(User).filter_by(id=a.user_id).first()
                        if u: uname = u.username
                    result.append(AuditData(id=a.id, user_id=a.user_id, action=a.action,
                        details=a.details or "", ip_address=a.ip_address or "",
                        created_at=a.created_at, username=uname))
                return result
        except Exception as e:
            log.error(f"AuditRepo.list error: {e}"); return []


class CommentRepo:
    @staticmethod
    def add(report_id, user_id, text, ctype="General", urgency="Low") -> bool:
        try:
            with get_db() as db:
                db.add(Comment(report_id=report_id, user_id=user_id, comment_text=text,
                               ctype=ctype, urgency=urgency))
            return True
        except Exception as e:
            log.error(f"CommentRepo.add error: {e}"); return False

    @staticmethod
    def list_recent(limit=20, user_ids=None) -> List[CommentData]:
        try:
            with get_db() as db:
                q = db.query(Comment).order_by(Comment.created_at.desc())
                if user_ids:
                    q = q.filter(Comment.user_id.in_(list(user_ids)))
                rows = q.limit(limit).all()
                result = []
                for c in rows:
                    uname = "User"
                    u = db.query(User).filter_by(id=c.user_id).first()
                    if u: uname = u.username
                    result.append(CommentData(id=c.id, report_id=c.report_id, user_id=c.user_id,
                        comment_text=c.comment_text, ctype=c.ctype, urgency=c.urgency,
                        created_at=c.created_at, username=uname))
                return result
        except Exception as e:
            log.error(f"CommentRepo.list error: {e}"); return []


class BudgetRepo:
    @staticmethod
    def save(user_id, name, fiscal_year, currency, data_json) -> bool:
        try:
            with get_db() as db:
                db.add(BudgetSnapshot(user_id=user_id, name=name, fiscal_year=fiscal_year,
                                      currency=currency, data_json=data_json))
            return True
        except Exception as e:
            log.error(f"BudgetRepo.save error: {e}"); return False

    @staticmethod
    def latest(user_id) -> Optional[dict]:
        try:
            with get_db() as db:
                row = (db.query(BudgetSnapshot).filter_by(user_id=user_id)
                       .order_by(BudgetSnapshot.updated_at.desc()).first())
                if row:
                    import json
                    return json.loads(row.data_json)
            return None
        except Exception as e:
            log.error(f"BudgetRepo.latest error: {e}"); return None


# ---- Session Repo (persistent login) ----------------------------

class SessionRepo:
    @staticmethod
    def create(user_id: int, remember_me: bool = False,
              user_agent: str = "", ip_address: str = "") -> Optional[str]:
        token = secrets.token_urlsafe(48)
        days  = 30 if remember_me else 1
        expires = datetime.utcnow() + timedelta(days=days)
        try:
            with get_db() as db:
                db.add(UserSession(user_id=user_id, token=token, remember_me=remember_me,
                                   user_agent=user_agent[:250], ip_address=ip_address,
                                   expires_at=expires))
            return token
        except Exception as e:
            log.error(f"SessionRepo.create error: {e}"); return None

    @staticmethod
    def get_valid(token: str) -> Optional[SessionData]:
        if not token: return None
        try:
            with get_db() as db:
                s = db.query(UserSession).filter_by(token=token).first()
                if not s: return None
                if s.expires_at < datetime.utcnow():
                    db.delete(s); return None
                s.last_seen = datetime.utcnow()
                return SessionData(id=s.id, user_id=s.user_id, token=s.token,
                    remember_me=s.remember_me, created_at=s.created_at,
                    expires_at=s.expires_at, last_seen=s.last_seen,
                    user_agent=s.user_agent or "", ip_address=s.ip_address or "")
        except Exception as e:
            log.error(f"SessionRepo.get_valid error: {e}"); return None

    @staticmethod
    def delete(token: str):
        try:
            with get_db() as db:
                s = db.query(UserSession).filter_by(token=token).first()
                if s: db.delete(s)
        except Exception as e:
            log.error(f"SessionRepo.delete error: {e}")

    @staticmethod
    def list_for_user(user_id: int) -> List[SessionData]:
        try:
            with get_db() as db:
                rows = (db.query(UserSession).filter_by(user_id=user_id)
                        .order_by(UserSession.last_seen.desc()).all())
                return [SessionData(id=s.id, user_id=s.user_id, token=s.token,
                        remember_me=s.remember_me, created_at=s.created_at,
                        expires_at=s.expires_at, last_seen=s.last_seen,
                        user_agent=s.user_agent or "", ip_address=s.ip_address or "")
                        for s in rows]
        except Exception as e:
            log.error(f"SessionRepo.list_for_user error: {e}"); return []

    @staticmethod
    def revoke_by_id(session_id: int):
        try:
            with get_db() as db:
                s = db.query(UserSession).filter_by(id=session_id).first()
                if s: db.delete(s)
        except Exception as e:
            log.error(f"SessionRepo.revoke_by_id error: {e}")

    @staticmethod
    def cleanup_expired():
        try:
            with get_db() as db:
                db.query(UserSession).filter(UserSession.expires_at < datetime.utcnow()).delete()
        except Exception as e:
            log.error(f"SessionRepo.cleanup_expired error: {e}")


# ---- Login Attempt Repo (brute-force lockout) -------------------

class LoginAttemptRepo:
    @staticmethod
    def record(identifier: str, success: bool, ip: str = ""):
        try:
            with get_db() as db:
                db.add(LoginAttempt(identifier=identifier.lower(), success=success, ip_address=ip))
        except Exception as e:
            log.error(f"LoginAttemptRepo.record error: {e}")

    @staticmethod
    def count_recent_failures(identifier: str, minutes: int = 15) -> int:
        try:
            with get_db() as db:
                cutoff = datetime.utcnow() - timedelta(minutes=minutes)
                return (db.query(LoginAttempt)
                        .filter(LoginAttempt.identifier == identifier.lower())
                        .filter(LoginAttempt.success == False)
                        .filter(LoginAttempt.created_at >= cutoff)
                        .count())
        except Exception as e:
            log.error(f"count_recent_failures error: {e}"); return 0

    @staticmethod
    def clear_for(identifier: str):
        try:
            with get_db() as db:
                db.query(LoginAttempt).filter(LoginAttempt.identifier == identifier.lower()).delete()
        except Exception as e:
            log.error(f"clear_for error: {e}")


# ---- Transaction Repo (billing history) -------------------------

class TransactionRepo:
    @staticmethod
    def create(user_id, gateway, amount, currency, plan="pro",
              billing_cycle="month", status="completed", reference="") -> bool:
        try:
            with get_db() as db:
                db.add(Transaction(user_id=user_id, gateway=gateway, amount=amount,
                                   currency=currency, status=status, plan=plan,
                                   billing_cycle=billing_cycle, reference=reference))
            return True
        except Exception as e:
            log.error(f"TransactionRepo.create error: {e}"); return False

    @staticmethod
    def list_for_user(user_id: int, limit: int = 20) -> List[TransactionData]:
        try:
            with get_db() as db:
                rows = (db.query(Transaction).filter_by(user_id=user_id)
                        .order_by(Transaction.created_at.desc()).limit(limit).all())
                return [TransactionData(id=t.id, user_id=t.user_id, gateway=t.gateway,
                        amount=t.amount, currency=t.currency, status=t.status, plan=t.plan,
                        billing_cycle=t.billing_cycle, reference=t.reference or "",
                        created_at=t.created_at) for t in rows]
        except Exception as e:
            log.error(f"TransactionRepo.list error: {e}"); return []
