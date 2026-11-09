"""Durable documents and property catalogue; local files remain the offline backend."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile

import database


def initialize():
    if not database.is_cloud():
        return
    with database.connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS app_documents (
            name TEXT PRIMARY KEY, payload JSONB NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now())''')
        db.execute('''CREATE TABLE IF NOT EXISTS property_catalogue (
            property_key TEXT PRIMARY KEY, payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now())''')


def read_json(path, default):
    if database.is_cloud():
        with database.connect() as db:
            row = db.execute('SELECT payload FROM app_documents WHERE name=?', (Path(path).name,)).fetchone()
        return row['payload'] if row else default
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path, value):
    if database.is_cloud():
        with database.connect() as db:
            db.execute('''INSERT INTO app_documents(name,payload) VALUES (?,?::jsonb)
                ON CONFLICT(name) DO UPDATE SET payload=excluded.payload,updated_at=now()''',
                (Path(path).name, json.dumps(value, ensure_ascii=False)))
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def update_json(path, default, mutate):
    """Serialize read/modify/write operations for shared favourites and history."""
    if not database.is_cloud():
        value = mutate(read_json(path, default))
        write_json(path, value)
        return value
    name = Path(path).name
    with database.connect() as db:
        db.execute('INSERT INTO app_documents(name,payload) VALUES (?,?::jsonb) ON CONFLICT DO NOTHING',
                   (name, json.dumps(default)))
        row = db.execute('SELECT payload FROM app_documents WHERE name=? FOR UPDATE', (name,)).fetchone()
        value = mutate(row['payload'])
        db.execute('UPDATE app_documents SET payload=?::jsonb,updated_at=now() WHERE name=?',
                   (json.dumps(value, ensure_ascii=False), name))
    return value


def read_catalogue(path='geral.json'):
    if not database.is_cloud():
        return read_json(path, [])
    with database.connect() as db:
        rows = db.execute('SELECT payload FROM property_catalogue ORDER BY created_at,property_key').fetchall()
    return [row['payload'] for row in rows]


def save_catalogue(records, path='geral.json'):
    if not database.is_cloud():
        write_json(path, records)
        return
    # Batch in a transaction; preserve properties added by another collector.
    payloads = []
    for record in records:
        key = str(record.get('link') or record.get('id') or '')
        if not key:
            raise ValueError('Anúncio sem identificador ou link.')
        payloads.append((hashlib.sha256(key.encode()).hexdigest(), json.dumps(record, ensure_ascii=False)))
    if payloads:
        with database.connect() as db:
            db.executemany('''INSERT INTO property_catalogue(property_key,payload) VALUES (?,?::jsonb)
                ON CONFLICT(property_key) DO UPDATE SET
                payload=property_catalogue.payload || excluded.payload,updated_at=now()''', payloads)


@contextmanager
def collection_lock():
    """Cross-session/process lock; advisory locks release even if a worker dies."""
    if not database.is_cloud():
        yield True
        return
    import psycopg
    # A direct connection is required for session-scoped advisory locks.
    direct = os.environ.get('DATABASE_DIRECT_URL') or database.database_url().replace('-pooler.', '.')
    with psycopg.connect(direct, autocommit=True, connect_timeout=15) as db:
        locked = db.execute('SELECT pg_try_advisory_lock(726453821)').fetchone()[0]
        try:
            yield locked
        finally:
            if locked:
                db.execute('SELECT pg_advisory_unlock(726453821)')
