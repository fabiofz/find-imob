import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import dashboard_runtime as runtime


class DashboardRuntimeTests(unittest.TestCase):
    def test_each_route_uses_fresh_execution_despite_existing_app_module(self):
        # Reproduce the mismatched module identity that makes reload() fail.
        foreign_app = types.ModuleType('__main__')
        with patch.dict(sys.modules, {'app': foreign_app}), \
             patch.dict(os.environ, {'DATABASE_URL': '', 'FINDIMOB_CLOUD': ''}), \
             patch.object(runtime.st, 'secrets', {}), \
             patch.object(runtime.runpy, 'run_path') as execute:
            runtime.run_dashboard()
            runtime.run_dashboard()
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(execute.call_args.kwargs['run_name'], '_findimob_dashboard')

    def test_direct_cloud_route_loads_settings_before_execution(self):
        with patch.dict(os.environ, {'DATABASE_URL': '', 'FINDIMOB_CLOUD': ''}), \
             patch.object(runtime.st, 'secrets', {'DATABASE_URL': 'postgresql://example.invalid/test'}), \
             patch.object(runtime, 'initialize_cloud') as initialize, \
             patch.object(runtime.runpy, 'run_path') as execute:
            runtime.run_dashboard()
            self.assertEqual(runtime.home_page(), 'cloud_app.py')
            initialize.assert_called_once()
            execute.assert_called_once()

    def test_all_routes_use_runner(self):
        for route in (Path(__file__).resolve().parents[1] / 'pages').glob('*.py'):
            with self.subTest(route=route.name):
                source = route.read_text()
                self.assertNotIn('importlib.reload', source)
                self.assertIn('run_dashboard()', source)
