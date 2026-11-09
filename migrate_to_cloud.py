"""One-time import of this installation's data into an EMPTY hosted database.

Run with DATABASE_URL configured. Never put credentials in this file.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import sqlite3

import auth_store
import cloud_store
import database
import review_store


def migrate(source):
    if not database.is_cloud():
        raise RuntimeError('Configure DATABASE_URL antes de migrar.')
    cloud_store.initialize()
    if cloud_store.read_json('migration-v1', None):
        print('Migração já realizada; os dados online foram preservados.')
        return
    # Never merge this installation into a database already in use.
    with database.connect() as db:
        existing = db.execute("SELECT to_regclass('public.users') AS name").fetchone()['name']
        if existing and db.execute('SELECT count(*) AS count FROM users').fetchone()['count']:
            raise RuntimeError('O banco de destino já contém contas. Migração cancelada.')
    os.environ.setdefault('FINDIMOB_ADMIN_PASSWORD', secrets.token_urlsafe(32) + 'aA1!')
    auth_store.initialize()
    with review_store._connect():
        pass
    counts = {}
    with database.connect() as target:
        for filename, tables in (('.users.sqlite3', ('users',)), ('.reviews.sqlite3', ('reviews',))):
            path = source / filename
            if not path.exists():
                continue
            with sqlite3.connect(f'file:{path}?mode=ro', uri=True) as local:
                local.row_factory = sqlite3.Row
                for table in tables:
                    rows = local.execute(f'SELECT * FROM {table}').fetchall()
                    for row in rows:
                        values = dict(row)
                        if table == 'users' and values['username'] == 'admin':
                            if auth_store._verify_password('admin', values['password_hash']):
                                raise RuntimeError('Troque a senha admin padrão no app local antes de publicar.')
                        columns = list(values)
                        parameters = ','.join('?' for _ in columns)
                        updates = ','.join(f'{column}=excluded.{column}' for column in columns if column != 'id')
                        target.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({parameters}) "
                                       f"ON CONFLICT(id) DO UPDATE SET {updates}", list(values.values()))
                    target.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                                   f"COALESCE((SELECT max(id) FROM {table}), 1), "
                                   f"EXISTS(SELECT 1 FROM {table}))")
                    counts[table] = len(rows)
    cloud_store.save_catalogue(json.loads((source / 'geral.json').read_text()))
    counts['anuncios'] = len(cloud_store.read_catalogue())
    for name in ('.execucoes.json', '.anuncios_estado.json', '.parametros_busca.json',
                 '.tema.json', '.resultados_notificacao.json'):
        path = source / name
        if path.exists():
            value = json.loads(path.read_text())
            if name == '.execucoes.json':
                value = [{key: item for key, item in execution.items() if key != 'log'}
                         for execution in value]
            cloud_store.write_json(name, value)
    cloud_store.write_json('migration-v1', {'complete': True, 'counts': counts})
    print('Migração concluída:', counts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parent)
    arguments = parser.parse_args()
    migrate(arguments.source)

