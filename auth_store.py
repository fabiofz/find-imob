"""Armazenamento local de credenciais e perfis do Find Imob."""
import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / ".users.sqlite3"
SCRYPT_N = 1 << 15
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 64 * 1024 * 1024
LOCK_SECONDS = 15 * 60
MAX_FAILURES = 5


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=15000")
    return connection


def _secure_file():
    if os.name == "posix" and DB_PATH.exists():
        os.chmod(DB_PATH, 0o600)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(DB_PATH) + suffix)
            if sidecar.exists():
                os.chmod(sidecar, 0o600)


def _hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R,
        p=SCRYPT_P, dklen=32, maxmem=SCRYPT_MAXMEM,
    )
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii")
    return "$".join(("scrypt", str(SCRYPT_N), str(SCRYPT_R), str(SCRYPT_P),
                     salt_text, digest_text))


def _verify_password(password, encoded):
    try:
        algorithm, n, r, p, salt_text, digest_text = encoded.split("$")
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p),
            dklen=len(expected), maxmem=SCRYPT_MAXMEM,
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


def initialize():
    with _connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                full_name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                phone TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('admin','user')),
                active INTEGER NOT NULL DEFAULT 0,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                avatar BLOB,
                google_sub TEXT UNIQUE,
                created_at INTEGER NOT NULL
            )
        """)
        columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
        if "google_sub" not in columns:
            db.execute("ALTER TABLE users ADD COLUMN google_sub TEXT")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub ON users(google_sub)")
        db.execute("""
            CREATE TABLE IF NOT EXISTS login_limits (
                identifier TEXT PRIMARY KEY,
                failures INTEGER NOT NULL DEFAULT 0,
                locked_until INTEGER NOT NULL DEFAULT 0
            )
        """)
        admin = db.execute(
            "SELECT id FROM users WHERE username = ?", ("admin",)
        ).fetchone()
        if admin is None:
            db.execute(
                """INSERT INTO users
                   (username,full_name,display_name,email,phone,password_hash,
                    role,active,must_change_password,created_at)
                   VALUES (?,?,?,?,?,?, 'admin',1,1,?)""",
                ("admin", "Administrador", "Admin", "admin@localhost", "",
                 _hash_password("admin"), int(time.time())),
            )
    _secure_file()


def _login_limit(identifier):
    key = identifier.strip().casefold()[:254]
    with _connect() as db:
        row = db.execute(
            "SELECT failures, locked_until FROM login_limits WHERE identifier=?",
            (key,),
        ).fetchone()
    if row and row["locked_until"] > int(time.time()):
        return key, row["locked_until"]
    return key, 0


def _record_failure(key):
    now = int(time.time())
    with _connect() as db:
        row = db.execute(
            "SELECT failures FROM login_limits WHERE identifier=?", (key,)
        ).fetchone()
        failures = (row["failures"] if row else 0) + 1
        locked_until = now + LOCK_SECONDS if failures >= MAX_FAILURES else 0
        db.execute(
            """INSERT INTO login_limits(identifier,failures,locked_until)
               VALUES(?,?,?) ON CONFLICT(identifier) DO UPDATE SET
               failures=excluded.failures,locked_until=excluded.locked_until""",
            (key, failures, locked_until),
        )
    return locked_until


def authenticate(identifier, password):
    if len(identifier) > 254 or len(password) > 128:
        return None, "invalid"
    key, locked_until = _login_limit(identifier)
    if locked_until:
        return None, "locked"
    lookup = identifier.strip().casefold()
    with _connect() as db:
        user = db.execute(
            "SELECT * FROM users WHERE username=? OR email=?", (lookup, lookup)
        ).fetchone()
    if user is None:
        _hash_password(password or "")
        _record_failure(key)
        return None, "invalid"
    if not _verify_password(password or "", user["password_hash"]):
        _record_failure(key)
        return None, "invalid"
    if not user["active"]:
        return None, "pending"
    with _connect() as db:
        db.execute("DELETE FROM login_limits WHERE identifier=?", (key,))
    _secure_file()
    return dict(user), "ok"


def create_user(full_name, display_name, email, phone, password, avatar):
    email = email.strip().casefold()
    username = email
    try:
        with _connect() as db:
            db.execute(
                """INSERT INTO users
                   (username,full_name,display_name,email,phone,password_hash,
                    role,active,must_change_password,avatar,created_at)
                   VALUES (?,?,?,?,?,?,'user',0,0,?,?)""",
                (username, full_name.strip(), display_name.strip(), email,
                 phone.strip(), _hash_password(password), avatar, int(time.time())),
            )
    except sqlite3.IntegrityError:
        return False
    _secure_file()
    return True



def authenticate_google(subject, email, full_name, email_verified):
    """Map a verified Google OIDC identity to a local, approval-gated account."""
    subject = str(subject or "").strip()
    email = str(email or "").strip().casefold()
    full_name = str(full_name or "").strip()[:120]
    if not subject or not valid_email(email) or not email_verified:
        return None, "unverified"
    with _connect() as db:
        user = db.execute("SELECT * FROM users WHERE google_sub=?", (subject,)).fetchone()
        if user is None:
            user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if user is not None:
                db.execute("UPDATE users SET google_sub=? WHERE id=?", (subject, user["id"]))
            else:
                name = full_name or email.split("@")[0]
                try:
                    db.execute(
                        """INSERT INTO users
                           (username,full_name,display_name,email,phone,password_hash,
                            role,active,must_change_password,google_sub,created_at)
                           VALUES (?,?,?,?,?,'google','user',0,0,?,?)""",
                        (email, name, name[:80], email, "", subject, int(time.time())),
                    )
                    user = db.execute("SELECT * FROM users WHERE google_sub=?", (subject,)).fetchone()
                except sqlite3.IntegrityError:
                    return None, "conflict"
        if user is None:
            user = db.execute("SELECT * FROM users WHERE google_sub=?", (subject,)).fetchone()
    if not user:
        return None, "invalid"
    if not user["active"]:
        return None, "pending"
    _secure_file()
    return dict(user), "ok"


def get_user(user_id):
    with _connect() as db:
        row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(row) if row else None


def update_profile(user_id, full_name, display_name, email, phone, avatar=None,
                   password=None):
    values = [full_name.strip(), display_name.strip(), email.strip().casefold(),
              phone.strip()]
    fields = "full_name=?,display_name=?,email=?,phone=?"
    fields += ",username=CASE WHEN role='user' THEN ? ELSE username END"
    values.append(email.strip().casefold())
    if avatar is not None:
        fields += ",avatar=?"
        values.append(avatar)
    if password is not None:
        fields += ",password_hash=?,must_change_password=0"
        values.append(_hash_password(password))
    values.append(user_id)
    try:
        with _connect() as db:
            db.execute(f"UPDATE users SET {fields} WHERE id=?", values)
    except sqlite3.IntegrityError:
        return False
    _secure_file()
    return True


def pending_users():
    with _connect() as db:
        rows = db.execute(
            """SELECT id,full_name,display_name,email,phone,avatar,created_at
               FROM users WHERE active=0 ORDER BY created_at"""
        ).fetchall()
    return [dict(row) for row in rows]


def set_user_active(user_id, active):
    with _connect() as db:
        db.execute(
            "UPDATE users SET active=? WHERE id=? AND role='user'",
            (int(active), user_id),
        )


def delete_pending_user(user_id):
    with _connect() as db:
        db.execute("DELETE FROM users WHERE id=? AND active=0", (user_id,))


def valid_password(password):
    return (
        len(password) >= 8
        and len(password) <= 128
        and any(ch.islower() for ch in password)
        and any(ch.isupper() for ch in password)
        and any(ch.isdigit() for ch in password)
        and any(not ch.isalnum() for ch in password)
    )


def valid_email(email):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()))
