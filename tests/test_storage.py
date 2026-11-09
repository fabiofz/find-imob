import json
import os
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

import auth_store
import cloud_store
import database
import review_store


class StorageContract:
    def test_account_approval_login_session_profile_and_duplicates(self):
        email = uuid.uuid4().hex + '@example.com'
        self.assertTrue(auth_store.create_user('Teste', 'Teste', email, '12999999999', 'ValidPass123!', b'avatar'))
        self.assertFalse(auth_store.create_user('Teste', 'Teste', email.upper(), '', 'ValidPass123!', None))
        self.assertEqual(auth_store.authenticate(email, 'ValidPass123!')[1], 'pending')
        user = next(u for u in auth_store.pending_users() if u['email'] == email)
        self.addCleanup(self.remove_user, user['id'])
        auth_store.set_user_active(user['id'], True)
        logged, status = auth_store.authenticate(email.upper(), 'ValidPass123!')
        self.assertEqual(status, 'ok')
        self.assertEqual(bytes(logged['avatar']), b'avatar')
        token = auth_store.create_auth_session(user['id'], 1800)
        self.assertEqual(auth_store.restore_auth_session(token, 1800)['id'], user['id'])
        auth_store.revoke_auth_session(token)
        self.assertIsNone(auth_store.restore_auth_session(token, 1800))
        self.assertTrue(auth_store.update_profile(user['id'], 'Atualizado', 'Nome', email, '', password='NewPass123!'))
        self.assertEqual(auth_store.authenticate(email, 'NewPass123!')[1], 'ok')

    def remove_user(self, user_id):
        with auth_store._connect() as db:
            db.execute('DELETE FROM users WHERE id=?', (user_id,))

    def test_review_moderation(self):
        key = uuid.uuid4().hex
        self.assertTrue(review_store.submit(key, 'Casa', 999, 'Autor', 4, True, 'Perto do centro', ''))
        self.assertEqual(review_store.list_approved(key), [])
        review = next(r for r in review_store.pending() if r['property_key'] == key)
        review_store.moderate(review['id'], 'approved', 1)
        self.assertEqual(review_store.list_approved(key)[0]['stars'], 4)
        self.assertTrue(review_store.submit(key, 'Casa', 999, 'Autor', 3, True, 'Atualizado', ''))
        self.assertEqual(review_store.get_user_review(key, 999)['status'], 'pending')
        with review_store._connect() as db:
            db.execute('DELETE FROM reviews WHERE property_key=?', (key,))

    def test_documents_survive_reopen(self):
        path = self.directory / (uuid.uuid4().hex + '.json')
        cloud_store.write_json(path, {'favoritos': ['a']})
        cloud_store.update_json(path, {}, lambda doc: {'favoritos': doc['favoritos'] + ['b']})
        self.assertEqual(cloud_store.read_json(path, {}), {'favoritos': ['a', 'b']})


class LocalStorageTests(StorageContract, unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'DATABASE_URL': ''})
        self.env.start()
        self.addCleanup(self.env.stop)
        for module, filename in ((auth_store, 'users.sqlite3'), (review_store, 'reviews.sqlite3')):
            patcher = patch.object(module, 'DB_PATH', self.directory / filename)
            patcher.start()
            self.addCleanup(patcher.stop)
        auth_store.initialize()

    def test_local_catalogue_roundtrip(self):
        path = self.directory / 'geral.json'
        cloud_store.save_catalogue([{'id': 'one', 'titulo': 'Casa'}], path)
        self.assertEqual(cloud_store.read_catalogue(path)[0]['id'], 'one')


@unittest.skipUnless(os.environ.get('TEST_DATABASE_URL'), 'Banco isolado não configurado')
class CloudStorageTests(StorageContract, unittest.TestCase):
    def setUp(self):
        self.directory = Path('/tmp')
        self.env = patch.dict(os.environ, {
            'DATABASE_URL': os.environ['TEST_DATABASE_URL'],
            'DATABASE_DIRECT_URL': os.environ['TEST_DATABASE_URL'],
            'FINDIMOB_ADMIN_PASSWORD': 'ValidationOnly123!',
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        cloud_store.initialize()
        auth_store.initialize()

    def test_catalogue_merge_preserves_other_collectors(self):
        key = uuid.uuid4().hex
        first = {'id': key + '1', 'link': 'https://example.com/' + key + '/1', 'titulo': 'Casa'}
        second = {'id': key + '2', 'link': 'https://example.com/' + key + '/2', 'titulo': 'Outra casa'}
        cloud_store.save_catalogue([first])
        cloud_store.save_catalogue([second])
        cloud_store.save_catalogue([{**first, 'descricao': 'Foto e descrição'}])
        records = {r['id']: r for r in cloud_store.read_catalogue()}
        self.assertIn(second['id'], records)
        self.assertEqual(records[first['id']]['descricao'], 'Foto e descrição')

    def test_only_one_collection_can_run(self):
        with cloud_store.collection_lock() as first:
            self.assertTrue(first)
            with cloud_store.collection_lock() as second:
                self.assertFalse(second)
        with cloud_store.collection_lock() as released:
            self.assertTrue(released)
