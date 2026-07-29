import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from backend.services.tenant_store import DATABASE_PATH, _slugify, _utc_now


SESSION_HOURS = 12
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
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE email = ? AND status = 'active'",
                (email,),
            ).fetchone()
        if row is None or not _password_matches(
            password,
            row["password_hash"],
        ):
            raise ValueError("Invalid email or password.")
        token = self.create_session(
            row["id"],
            session_hours=session_hours,
        )
        return self.get_user(row["id"]), token

    def register_trial(
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
        organization_slug = (
            f"{_slugify(organization_name)}-{secrets.token_hex(3)}"
        )
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
                "The trial account could not be created."
            ) from exc

        token = self.create_session(user_id)
        return (
            self.get_user(user_id),
            self._organization_for_user(user_id, organization_id),
            token,
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
            connection.execute(
                "DELETE FROM user_sessions WHERE token_hash = ?",
                (_token_hash(token),),
            )

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
