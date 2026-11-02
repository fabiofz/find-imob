import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / ".reviews.sqlite3"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT, property_key TEXT NOT NULL,
        property_title TEXT NOT NULL, user_id INTEGER NOT NULL,
        author_name TEXT NOT NULL, stars INTEGER NOT NULL CHECK(stars BETWEEN 0 AND 5),
        lived_here INTEGER NOT NULL DEFAULT 0, pros TEXT NOT NULL DEFAULT '',
        cons TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending','approved','rejected')), created_at INTEGER NOT NULL,
        reviewed_at INTEGER, reviewed_by INTEGER, UNIQUE(property_key, user_id)
    )""")
    db.commit()
    return db


def _secure_file():
    if os.name == "posix" and DB_PATH.exists():
        os.chmod(DB_PATH, 0o600)


def submit(property_key, property_title, user_id, author_name, stars, lived_here, pros, cons):
    property_key = str(property_key or "")[:128]
    property_title = str(property_title or "Imovel")[:300]
    author_name = str(author_name or "Usuario")[:120]
    pros, cons = str(pros or "").strip()[:2000], str(cons or "").strip()[:2000]
    stars = int(stars)
    if not property_key or not 0 <= stars <= 5 or (not pros and not cons):
        return False
    now = int(time.time())
    with _connect() as db:
        db.execute("""INSERT INTO reviews
            (property_key,property_title,user_id,author_name,stars,lived_here,pros,cons,status,created_at)
            VALUES (?,?,?,?,?,?,?,?,'pending',?)
            ON CONFLICT(property_key,user_id) DO UPDATE SET
            property_title=excluded.property_title,author_name=excluded.author_name,
            stars=excluded.stars,lived_here=excluded.lived_here,pros=excluded.pros,
            cons=excluded.cons,status='pending',created_at=excluded.created_at,
            reviewed_at=NULL,reviewed_by=NULL""",
            (property_key, property_title, int(user_id), author_name, stars,
             int(bool(lived_here)), pros, cons, now))
    _secure_file()
    return True


def list_approved(property_key):
    with _connect() as db:
        rows = db.execute("""SELECT stars,lived_here,pros,cons,author_name,created_at
            FROM reviews WHERE property_key=? AND status='approved' ORDER BY reviewed_at DESC,id DESC""",
            (str(property_key),)).fetchall()
    return [dict(row) for row in rows]


def get_user_review(property_key, user_id):
    with _connect() as db:
        row = db.execute("SELECT status FROM reviews WHERE property_key=? AND user_id=?",
                         (str(property_key), int(user_id))).fetchone()
    return dict(row) if row else None


def pending():
    with _connect() as db:
        rows = db.execute("SELECT * FROM reviews WHERE status='pending' ORDER BY created_at").fetchall()
    return [dict(row) for row in rows]


def moderate(review_id, status, admin_id):
    if status not in {"approved", "rejected"}:
        return
    with _connect() as db:
        db.execute("UPDATE reviews SET status=?,reviewed_at=?,reviewed_by=? WHERE id=? AND status='pending'",
                   (status, int(time.time()), int(admin_id), int(review_id)))
