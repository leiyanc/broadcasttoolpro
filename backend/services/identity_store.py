import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from backend.services.tenant_store import (
    DATABASE_PATH,
    _slugify,
    _utc_now,
    _validate_timezone,
)


SESSION_HOURS = 12
MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW_MINUTES = 15
LOGIN_LOCK_MINUTES = 15
PASSWORD_RESET_MINUTES = 30
PASSWORD_RESET_COOLDOWN_MINUTES = 5
ROLE_RANK = {
    "viewer": 10,
    "operator": 20,
    "admin": 30,
    "owner": 40,
}


def _password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def _password_matches(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(expected)),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), expected)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


_DUMMY_PASSWORD_HASH = _password_hash(
    "broadcast-tool-pro-invalid-password-sentinel"
)


class AuthenticationLockedError(ValueError):
    pass


class IdentityStore:
    def __init__(self, database_path: Path = DATABASE_PATH):
        self.database_path = database_path

    def _connection(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    is_superuser INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS organization_memberships (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (
                        role IN ('owner', 'admin', 'operator', 'viewer')
                    ),
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (organization_id)
                        REFERENCES organizations(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id)
                        REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE (organization_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS user_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_memberships_user
                    ON organization_memberships(user_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_token
                    ON user_sessions(token_hash);

                CREATE TABLE IF NOT EXISTS login_security (
                    email TEXT PRIMARY KEY,
                    failed_attempts INTEGER NOT NULL DEFAULT 0,
                    first_failed_at TEXT NOT NULL,
                    locked_until TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS security_audit_log (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    email TEXT,
                    success INTEGER NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_security_audit_created
                    ON security_audit_log(created_at);

                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    used_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS account_activation_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    used_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );
            """)
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(users)")
            }
            if "is_superuser" not in columns:
                connection.execute(
                    """
                    ALTER TABLE users
                    ADD COLUMN is_superuser INTEGER NOT NULL DEFAULT 0
                    """
                )
            connection.execute("""
                UPDATE users
                SET is_superuser = 1
                WHERE id = (
                    SELECT id FROM users
                    ORDER BY created_at
                    LIMIT 1
                )
                AND NOT EXISTS (
                    SELECT 1 FROM users WHERE is_superuser = 1
                )
            """)

    def has_users(self) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT EXISTS(SELECT 1 FROM users)"
            ).fetchone()
        return bool(row[0])

    def bootstrap(
        self,
        *,
        organization_name: str,
        display_name: str,
        email: str,
        password: str,
    ) -> tuple[dict, dict, str]:
        timestamp = _utc_now()
        organization_id = str(uuid4())
        user_id = str(uuid4())
        session_id = str(uuid4())
        organization_slug = _slugify(organization_name)
        raw_token = secrets.token_urlsafe(32)
        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
        ).isoformat()

        try:
            with self._connection() as connection:
                if connection.execute(
                    "SELECT EXISTS(SELECT 1 FROM users)"
                ).fetchone()[0]:
                    raise ValueError(
                        "Platform bootstrap has already been completed."
                    )
                connection.execute(
                    """
                    INSERT INTO organizations (
                        id, name, slug, plan, status, created_at, updated_at
                    ) VALUES (?, ?, ?, 'professional', 'active', ?, ?)
                    """,
                    (
                        organization_id,
                        organization_name.strip(),
                        organization_slug,
                        timestamp,
                        timestamp,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO users (
                        id, email, display_name, password_hash, status,
                        is_superuser, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'active', 1, ?, ?)
                    """,
                    (
                        user_id,
                        email,
                        display_name.strip(),
                        _password_hash(password),
                        timestamp,
                        timestamp,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO organization_memberships (
                        id, organization_id, user_id, role, created_at
                    ) VALUES (?, ?, ?, 'owner', ?)
                    """,
                    (
                        str(uuid4()),
                        organization_id,
                        user_id,
                        timestamp,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO user_sessions (
                        id, user_id, token_hash, expires_at, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        user_id,
                        _token_hash(raw_token),
                        expires_at,
                        timestamp,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "The organization or owner account already exists."
            ) from exc

        return (
            self.get_user(user_id),
            self._organization_for_user(user_id, organization_id),
            raw_token,
        )

    def authenticate(
        self,
        email: str,
        password: str,
        *,
        session_hours: int = SESSION_HOURS,
    ) -> tuple[dict, str]:
        email = email.strip().lower()
        now = datetime.now(timezone.utc)
        with self._connection() as connection:
            security = connection.execute(
                "SELECT * FROM login_security WHERE email = ?",
                (email,),
            ).fetchone()
            if security and security["locked_until"]:
                locked_until = datetime.fromisoformat(
                    security["locked_until"]
                )
                if locked_until > now:
                    self._record_security_event(
                        connection,
                        event_type="login_blocked",
                        email=email,
                        success=False,
                        details="Temporary login lock is active.",
                    )
                    connection.commit()
                    raise AuthenticationLockedError(
                        "Too many sign-in attempts. Try again in 15 minutes."
                    )
            row = connection.execute(
                "SELECT * FROM users WHERE email = ? AND status = 'active'",
                (email,),
            ).fetchone()
            password_valid = _password_matches(
                password,
                row["password_hash"] if row else _DUMMY_PASSWORD_HASH,
            )
            if row is None or not password_valid:
                self._register_failed_login(connection, email, now)
                self._record_security_event(
                    connection,
                    event_type="login_failed",
                    email=email,
                    success=False,
                    details="Invalid credentials.",
                )
                connection.commit()
                raise ValueError("Invalid email or password.")
            connection.execute(
                "DELETE FROM login_security WHERE email = ?",
                (email,),
            )
            self._record_security_event(
                connection,
                event_type="login_succeeded",
                user_id=row["id"],
                email=email,
                success=True,
            )
        token = self.create_session(
            row["id"],
            session_hours=session_hours,
        )
        return self.get_user(row["id"]), token

    def register_customer(
        self,
        *,
        organization_name: str,
        channel_name: str | None = None,
        channel_code: str | None = None,
        channel_timezone: str = "UTC",
        channel_language: str = "und",
        channel_stream_monitoring: bool = False,
        display_name: str,
        email: str,
        password: str,
        plan_code: str,
    ) -> tuple[dict, dict, str]:
        internal_plan = (
            "starter" if plan_code == "programming_suite" else plan_code
        )
        if internal_plan not in {"starter", "professional", "enterprise"}:
            raise ValueError("A valid subscription plan is required.")
        timestamp = _utc_now()
        organization_id = str(uuid4())
        user_id = str(uuid4())
        organization_slug = (
            f"{_slugify(organization_name)}-{secrets.token_hex(3)}"
        )
        initial_channel_name = (channel_name or organization_name).strip()
        initial_channel_code = (
            channel_code or _slugify(initial_channel_name)
        ).strip()
        channel_timezone = _validate_timezone(channel_timezone)
        workspace_id = str(uuid4())
        channel_id = str(uuid4())
        try:
            with self._connection() as connection:
                if connection.execute(
                    "SELECT 1 FROM users WHERE email = ?",
                    (email,),
                ).fetchone():
                    raise ValueError(
                        "An account with this email address already exists."
                    )
                connection.execute(
                    """
                    INSERT INTO organizations (
                        id, name, slug, plan, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'active', ?, ?)
                    """,
                    (
                        organization_id,
                        organization_name.strip(),
                        organization_slug,
                        internal_plan,
                        timestamp,
                        timestamp,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO workspaces (
                        id, organization_id, name, slug, default_timezone,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, 'channel-operations', ?, ?, ?)
                    """,
                    (
                        workspace_id,
                        organization_id,
                        "Channel Operations",
                        channel_timezone,
                        timestamp,
                        timestamp,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO channels (
                        id, workspace_id, name, slug, channel_code, timezone,
                        primary_language, stream_monitoring, active,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        channel_id,
                        workspace_id,
                        initial_channel_name,
                        _slugify(initial_channel_name),
                        initial_channel_code,
                        channel_timezone,
                        channel_language,
                        int(channel_stream_monitoring),
                        timestamp,
                        timestamp,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO users (
                        id, email, display_name, password_hash, status,
                        is_superuser, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'active', 0, ?, ?)
                    """,
                    (
                        user_id,
                        email,
                        display_name.strip(),
                        _password_hash(password),
                        timestamp,
                        timestamp,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO organization_memberships (
                        id, organization_id, user_id, role, created_at
                    ) VALUES (?, ?, ?, 'owner', ?)
                    """,
                    (
                        str(uuid4()),
                        organization_id,
                        user_id,
                        timestamp,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "The customer account could not be created."
            ) from exc

        token = self.create_session(user_id)
        return (
            self.get_user(user_id),
            self._organization_for_user(user_id, organization_id),
            token,
        )

    def register_trial(
        self,
        *,
        organization_name: str,
        display_name: str,
        email: str,
        password: str,
    ) -> tuple[dict, dict, str]:
        return self.register_customer(
            organization_name=organization_name,
            display_name=display_name,
            email=email,
            password=password,
            plan_code="professional",
        )

    def create_session(
        self,
        user_id: str,
        *,
        session_hours: int = SESSION_HOURS,
    ) -> str:
        token = secrets.token_urlsafe(32)
        timestamp = _utc_now()
        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=session_hours)
        ).isoformat()
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM user_sessions WHERE expires_at <= ?",
                (timestamp,),
            )
            connection.execute(
                """
                INSERT INTO user_sessions (
                    id, user_id, token_hash, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    user_id,
                    _token_hash(token),
                    expires_at,
                    timestamp,
                ),
            )
        return token

    def user_from_session(self, token: str) -> dict | None:
        now = _utc_now()
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM user_sessions WHERE expires_at <= ?",
                (now,),
            )
            row = connection.execute(
                """
                SELECT users.*
                FROM user_sessions
                JOIN users ON users.id = user_sessions.user_id
                WHERE user_sessions.token_hash = ?
                  AND user_sessions.expires_at > ?
                  AND users.status = 'active'
                """,
                (_token_hash(token), now),
            ).fetchone()
        return self._public_user(row) if row else None

    def revoke_session(self, token: str) -> None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT users.id, users.email
                FROM user_sessions
                JOIN users ON users.id = user_sessions.user_id
                WHERE user_sessions.token_hash = ?
                """,
                (_token_hash(token),),
            ).fetchone()
            connection.execute(
                "DELETE FROM user_sessions WHERE token_hash = ?",
                (_token_hash(token),),
            )
            if row:
                self._record_security_event(
                    connection,
                    event_type="logout",
                    user_id=row["id"],
                    email=row["email"],
                    success=True,
                )

    def revoke_all_sessions(self, user_id: str) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM user_sessions WHERE user_id = ?",
                (user_id,),
            )
            user = connection.execute(
                "SELECT email FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            self._record_security_event(
                connection,
                event_type="all_sessions_revoked",
                user_id=user_id,
                email=user["email"] if user else None,
                success=True,
                details=f"{cursor.rowcount} sessions revoked.",
            )
            return cursor.rowcount

    @staticmethod
    def _record_security_event(
        connection: sqlite3.Connection,
        *,
        event_type: str,
        success: bool,
        user_id: str | None = None,
        email: str | None = None,
        details: str | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO security_audit_log (
                id, event_type, user_id, email, success, details, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                event_type,
                user_id,
                email,
                int(success),
                details,
                _utc_now(),
            ),
        )

    @staticmethod
    def _register_failed_login(
        connection: sqlite3.Connection,
        email: str,
        now: datetime,
    ) -> None:
        row = connection.execute(
            "SELECT * FROM login_security WHERE email = ?",
            (email,),
        ).fetchone()
        window = timedelta(minutes=FAILED_LOGIN_WINDOW_MINUTES)
        attempts = 1
        first_failed_at = now
        if row:
            previous_start = datetime.fromisoformat(
                row["first_failed_at"]
            )
            if now - previous_start <= window:
                attempts = row["failed_attempts"] + 1
                first_failed_at = previous_start
        locked_until = None
        if attempts >= MAX_FAILED_LOGINS:
            locked_until = (
                now + timedelta(minutes=LOGIN_LOCK_MINUTES)
            ).isoformat()
        connection.execute(
            """
            INSERT INTO login_security (
                email, failed_attempts, first_failed_at,
                locked_until, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                failed_attempts = excluded.failed_attempts,
                first_failed_at = excluded.first_failed_at,
                locked_until = excluded.locked_until,
                updated_at = excluded.updated_at
            """,
            (
                email,
                attempts,
                first_failed_at.isoformat(),
                locked_until,
                now.isoformat(),
            ),
        )

    def security_events(self, limit: int = 100) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM security_audit_log
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_password_reset(
        self,
        email: str,
    ) -> tuple[dict, str] | None:
        email = email.strip().lower()
        now = datetime.now(timezone.utc)
        with self._connection() as connection:
            user = connection.execute(
                "SELECT id, email FROM users WHERE email = ?",
                (email,),
            ).fetchone()
            if user is None:
                self._record_security_event(
                    connection,
                    event_type="password_reset_requested",
                    email=email,
                    success=True,
                    details="No matching active account disclosed.",
                )
                return None
            recent = connection.execute(
                """
                SELECT created_at
                FROM password_reset_tokens
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user["id"],),
            ).fetchone()
            if recent and datetime.fromisoformat(recent["created_at"]) > (
                now - timedelta(minutes=PASSWORD_RESET_COOLDOWN_MINUTES)
            ):
                self._record_security_event(
                    connection,
                    event_type="password_reset_throttled",
                    user_id=user["id"],
                    email=email,
                    success=False,
                    details="Recovery request cooldown is active.",
                )
                return None
            token = secrets.token_urlsafe(32)
            connection.execute(
                """
                UPDATE password_reset_tokens
                SET used_at = ?
                WHERE user_id = ? AND used_at IS NULL
                """,
                (now.isoformat(), user["id"]),
            )
            connection.execute(
                """
                INSERT INTO password_reset_tokens (
                    id, user_id, token_hash, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    user["id"],
                    _token_hash(token),
                    (
                        now + timedelta(minutes=PASSWORD_RESET_MINUTES)
                    ).isoformat(),
                    now.isoformat(),
                ),
            )
            organization = connection.execute(
                """
                SELECT organizations.id, organizations.name
                FROM organization_memberships
                JOIN organizations
                  ON organizations.id =
                     organization_memberships.organization_id
                WHERE organization_memberships.user_id = ?
                ORDER BY organization_memberships.created_at
                LIMIT 1
                """,
                (user["id"],),
            ).fetchone()
            self._record_security_event(
                connection,
                event_type="password_reset_requested",
                user_id=user["id"],
                email=email,
                success=True,
            )
        if organization is None:
            return None
        return {
            "user_id": user["id"],
            "email": user["email"],
            "organization_id": organization["id"],
            "organization_name": organization["name"],
        }, token

    def reset_password(self, token: str, new_password: str) -> dict:
        now = datetime.now(timezone.utc)
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT password_reset_tokens.*, users.email
                FROM password_reset_tokens
                JOIN users ON users.id = password_reset_tokens.user_id
                WHERE password_reset_tokens.token_hash = ?
                  AND password_reset_tokens.used_at IS NULL
                  AND password_reset_tokens.expires_at > ?
                  AND users.status = 'active'
                """,
                (_token_hash(token), now.isoformat()),
            ).fetchone()
            if row is None:
                raise ValueError(
                    "The password reset link is invalid or has expired."
                )
            connection.execute(
                """
                UPDATE users
                SET password_hash = ?, updated_at = ?
                WHERE id = ?
                """,
                (_password_hash(new_password), now.isoformat(), row["user_id"]),
            )
            connection.execute(
                """
                UPDATE password_reset_tokens
                SET used_at = ?
                WHERE user_id = ? AND used_at IS NULL
                """,
                (now.isoformat(), row["user_id"]),
            )
            connection.execute(
                "DELETE FROM user_sessions WHERE user_id = ?",
                (row["user_id"],),
            )
            connection.execute(
                "DELETE FROM login_security WHERE email = ?",
                (row["email"],),
            )
            self._record_security_event(
                connection,
                event_type="password_reset_completed",
                user_id=row["user_id"],
                email=row["email"],
                success=True,
            )
        return self.get_user(row["user_id"])

    def provision_customer(
        self,
        *,
        organization_name: str,
        display_name: str,
        email: str,
        plan: str,
    ) -> tuple[dict, dict, str]:
        if plan not in {"starter", "professional", "enterprise"}:
            raise ValueError("A valid paid plan is required.")
        now = datetime.now(timezone.utc)
        organization_id = str(uuid4())
        user_id = str(uuid4())
        activation_token = secrets.token_urlsafe(32)
        organization_slug = (
            f"{_slugify(organization_name)}-{secrets.token_hex(3)}"
        )
        try:
            with self._connection() as connection:
                if connection.execute(
                    "SELECT 1 FROM users WHERE email = ?",
                    (email.strip().lower(),),
                ).fetchone():
                    raise ValueError(
                        "An account with this email address already exists."
                    )
                connection.execute(
                    """
                    INSERT INTO organizations (
                        id, name, slug, plan, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'active', ?, ?)
                    """,
                    (
                        organization_id,
                        organization_name.strip(),
                        organization_slug,
                        plan,
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO users (
                        id, email, display_name, password_hash, status,
                        is_superuser, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'invited', 0, ?, ?)
                    """,
                    (
                        user_id,
                        email.strip().lower(),
                        display_name.strip(),
                        _password_hash(secrets.token_urlsafe(48)),
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO organization_memberships (
                        id, organization_id, user_id, role, created_at
                    ) VALUES (?, ?, ?, 'owner', ?)
                    """,
                    (
                        str(uuid4()),
                        organization_id,
                        user_id,
                        now.isoformat(),
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO account_activation_tokens (
                        id, user_id, token_hash, expires_at, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        user_id,
                        _token_hash(activation_token),
                        (now + timedelta(days=7)).isoformat(),
                        now.isoformat(),
                    ),
                )
                self._record_security_event(
                    connection,
                    event_type="paid_account_provisioned",
                    user_id=user_id,
                    email=email.strip().lower(),
                    success=True,
                    details=f"{plan} account awaiting activation.",
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "The paid customer account could not be provisioned."
            ) from exc
        return (
            self.get_user(user_id),
            self._organization_for_user(user_id, organization_id),
            activation_token,
        )

    def existing_customer_account(
        self,
        email: str,
    ) -> tuple[dict, dict] | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT users.id AS user_id, organizations.id AS organization_id
                FROM users
                JOIN organization_memberships
                  ON organization_memberships.user_id = users.id
                JOIN organizations
                  ON organizations.id =
                     organization_memberships.organization_id
                WHERE users.email = ?
                ORDER BY
                    CASE organization_memberships.role
                        WHEN 'owner' THEN 0 ELSE 1
                    END,
                    organization_memberships.created_at
                LIMIT 1
                """,
                (email.strip().lower(),),
            ).fetchone()
        if row is None:
            return None
        return (
            self.get_user(row["user_id"]),
            self._organization_for_user(
                row["user_id"],
                row["organization_id"],
            ),
        )

    def reactivate_customer_account(
        self,
        email: str,
        plan: str,
    ) -> tuple[dict, dict]:
        if plan not in {"starter", "professional", "enterprise"}:
            raise ValueError("A valid paid plan is required.")
        existing = self.existing_customer_account(email)
        if existing is None:
            raise KeyError("Customer account not found.")
        user, organization = existing
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE organizations
                SET plan = ?, status = 'active', updated_at = ?
                WHERE id = ?
                """,
                (plan, now, organization["id"]),
            )
            connection.execute(
                """
                UPDATE users
                SET status = 'active', updated_at = ?
                WHERE id = ?
                """,
                (now, user["id"]),
            )
            self._record_security_event(
                connection,
                event_type="customer_account_reactivated",
                user_id=user["id"],
                email=user["email"],
                success=True,
                details=f"Existing account approved for {plan}.",
            )
        return (
            self.get_user(user["id"]),
            self._organization_for_user(user["id"], organization["id"]),
        )

    def activate_account(
        self,
        token: str,
        password: str,
    ) -> tuple[dict, str]:
        now = datetime.now(timezone.utc)
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT account_activation_tokens.*, users.email
                FROM account_activation_tokens
                JOIN users ON users.id = account_activation_tokens.user_id
                WHERE account_activation_tokens.token_hash = ?
                  AND account_activation_tokens.used_at IS NULL
                  AND account_activation_tokens.expires_at > ?
                  AND users.status = 'invited'
                """,
                (_token_hash(token), now.isoformat()),
            ).fetchone()
            if row is None:
                raise ValueError(
                    "The account activation link is invalid or has expired."
                )
            connection.execute(
                """
                UPDATE users
                SET password_hash = ?, status = 'active', updated_at = ?
                WHERE id = ?
                """,
                (_password_hash(password), now.isoformat(), row["user_id"]),
            )
            connection.execute(
                """
                UPDATE account_activation_tokens
                SET used_at = ?
                WHERE user_id = ? AND used_at IS NULL
                """,
                (now.isoformat(), row["user_id"]),
            )
            self._record_security_event(
                connection,
                event_type="paid_account_activated",
                user_id=row["user_id"],
                email=row["email"],
                success=True,
            )
        session = self.create_session(row["user_id"])
        return self.get_user(row["user_id"]), session

    def get_user(self, user_id: str) -> dict:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            raise KeyError("User not found.")
        return self._public_user(row)

    def create_member(
        self,
        *,
        organization_id: str,
        display_name: str,
        email: str,
        password: str,
        role: str,
    ) -> dict:
        timestamp = _utc_now()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,),
            ).fetchone()
            if row:
                user_id = row["id"]
            else:
                user_id = str(uuid4())
                connection.execute(
                    """
                    INSERT INTO users (
                        id, email, display_name, password_hash, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'active', ?, ?)
                    """,
                    (
                        user_id,
                        email,
                        display_name.strip(),
                        _password_hash(password),
                        timestamp,
                        timestamp,
                    ),
                )
            try:
                connection.execute(
                    """
                    INSERT INTO organization_memberships (
                        id, organization_id, user_id, role, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        organization_id,
                        user_id,
                        role,
                        timestamp,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    "This user already belongs to the organization."
                ) from exc
        return {
            **self.get_user(user_id),
            "role": role,
            "organization_id": organization_id,
        }

    def add_membership(
        self,
        *,
        organization_id: str,
        user_id: str,
        role: str,
    ) -> dict:
        try:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO organization_memberships (
                        id, organization_id, user_id, role, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        organization_id,
                        user_id,
                        role,
                        _utc_now(),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "This user already belongs to the organization."
            ) from exc
        return self.require_role(user_id, organization_id, role)

    def list_members(self, organization_id: str) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT users.id, users.email, users.display_name,
                       users.status, organization_memberships.role,
                       organization_memberships.created_at
                FROM organization_memberships
                JOIN users ON users.id = organization_memberships.user_id
                WHERE organization_memberships.organization_id = ?
                ORDER BY users.display_name
                """,
                (organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def membership(self, user_id: str, organization_id: str) -> dict | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM organization_memberships
                WHERE user_id = ? AND organization_id = ?
                """,
                (user_id, organization_id),
            ).fetchone()
        return dict(row) if row else None

    def organizations_for_user(self, user_id: str) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT organizations.*, organization_memberships.role
                FROM organization_memberships
                JOIN organizations
                  ON organizations.id =
                     organization_memberships.organization_id
                WHERE organization_memberships.user_id = ?
                ORDER BY organizations.name
                """,
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def superuser_notification_targets(self) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT users.id AS user_id, users.email,
                       MIN(organization_memberships.organization_id)
                           AS organization_id
                FROM users
                JOIN organization_memberships
                  ON organization_memberships.user_id = users.id
                WHERE users.is_superuser = 1
                  AND users.status = 'active'
                GROUP BY users.id, users.email
                ORDER BY users.created_at
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def require_role(
        self,
        user_id: str,
        organization_id: str,
        minimum_role: str = "viewer",
    ) -> dict:
        membership = self.membership(user_id, organization_id)
        if membership is None:
            raise PermissionError(
                "You do not have access to this organization."
            )
        if ROLE_RANK[membership["role"]] < ROLE_RANK[minimum_role]:
            raise PermissionError(
                f'The "{minimum_role}" role or higher is required.'
            )
        return membership

    def _organization_for_user(
        self,
        user_id: str,
        organization_id: str,
    ) -> dict:
        return next(
            organization
            for organization in self.organizations_for_user(user_id)
            if organization["id"] == organization_id
        )

    @staticmethod
    def _public_user(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "email": row["email"],
            "display_name": row["display_name"],
            "status": row["status"],
            "is_superuser": bool(row["is_superuser"]),
            "created_at": row["created_at"],
        }


identity_store = IdentityStore()
identity_store.initialize()
