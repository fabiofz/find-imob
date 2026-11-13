from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import unittest
from unittest.mock import Mock, patch

import requests
from scripts import catalog_collectors as collectors


def response(status, headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = b'<h1>OK</h1>'
    result.headers.update(headers or {})
    return result


class RequestRecoveryTests(unittest.TestCase):
    def test_503_waits_longer_and_survives_two_failures(self):
        session = Mock()
        session.get.side_effect = [response(503), response(503), response(200)]
        with patch.object(collectors.time, 'sleep') as sleep:
            self.assertEqual(collectors.buscar(session, 'https://example.com').h1.text, 'OK')
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [2, 4])
        self.assertEqual(session.get.call_count, 3)

    def test_429_respects_retry_after(self):
        session = Mock()
        session.get.side_effect = [response(429, {'Retry-After':'7'}), response(200)]
        with patch.object(collectors.time, 'sleep') as sleep:
            collectors.buscar(session, 'https://example.com')
        sleep.assert_called_once_with(7)

    def test_long_retry_after_does_not_retry_too_soon(self):
        session = Mock()
        session.get.return_value = response(429, {'Retry-After':'120'})
        with patch.object(collectors.time, 'sleep') as sleep:
            with self.assertRaises(requests.HTTPError):
                collectors.buscar(session, 'https://example.com')
        sleep.assert_not_called()
        session.get.assert_called_once()

    def test_retry_after_http_date_is_understood(self):
        later = datetime.now(timezone.utc) + timedelta(seconds=15)
        wait = collectors._espera_retentativa(response(503, {'Retry-After':format_datetime(later)}), 0)
        self.assertGreater(wait, 13)
        self.assertLessEqual(wait, 15)

    def test_repeated_requests_to_same_host_are_paced(self):
        with requests.Session() as session:
            session.__dict__['_findimob_consultas'] = {'example.com':100}
            with patch.object(collectors.time, 'monotonic', return_value=100.25), patch.object(collectors.time, 'sleep') as sleep:
                collectors._aguardar_consulta(session, 'https://example.com/page2')
                collectors._aguardar_consulta(session, 'https://other.com/')
            sleep.assert_called_once_with(.5)
