from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cloud_store
from advertisement_actions import exclude_advertisements


class AdvertisementActionsTests(unittest.TestCase):
    def test_bulk_delete_preserves_favorites_other_agencies_and_metadata(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {'DATABASE_URL': ''}):
            path = Path(folder) / 'state.json'
            initial = {'favoritos': ['a-favorite', 'b-favorite'], 'excluidos': ['old'],
                       'novos': ['a-one', 'a-two', 'b-one'], 'coletado_em': {'a-one': 'date'}, 'extra': 3}
            cloud_store.write_json(path, initial)
            count = exclude_advertisements(path, ['a-one', 'a-two', 'a-favorite', 'old', 'a-one'], preserve_favorites=True)
            state = cloud_store.read_json(path, {})
            self.assertEqual(count, 2)
            self.assertEqual(state['excluidos'], ['a-one', 'a-two', 'old'])
            self.assertEqual(state['favoritos'], initial['favoritos'])
            self.assertEqual(state['novos'], ['b-one'])
            self.assertEqual(state['coletado_em'], initial['coletado_em'])
            self.assertEqual(state['extra'], 3)
            self.assertEqual(exclude_advertisements(path, ['a-one', 'a-two'], preserve_favorites=True), 0)

    def test_single_delete_keeps_existing_behavior_for_favorites(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {'DATABASE_URL': ''}):
            path = Path(folder) / 'state.json'
            cloud_store.write_json(path, {'favoritos': ['a'], 'novos': ['a']})
            self.assertEqual(exclude_advertisements(path, ['a']), 1)
            state = cloud_store.read_json(path, {})
            self.assertEqual(state['favoritos'], [])
            self.assertEqual(state['novos'], [])
            self.assertEqual(state['excluidos'], ['a'])

    def test_favorite_added_after_selection_is_protected_in_atomic_update(self):
        current = {'favoritos': ['a'], 'excluidos': [], 'novos': ['a', 'b']}
        def update(path, default, mutate):
            nonlocal current
            current = mutate(current)
        with patch.object(cloud_store, 'update_json', side_effect=update) as write:
            self.assertEqual(exclude_advertisements('state.json', ['a', 'b'], preserve_favorites=True), 1)
        write.assert_called_once()
        self.assertEqual(current['excluidos'], ['b'])
        self.assertEqual(current['favoritos'], ['a'])

    def test_empty_selection_does_not_write(self):
        with patch.object(cloud_store, 'update_json') as write:
            self.assertEqual(exclude_advertisements('state.json', [None, '']), 0)
            write.assert_not_called()
