"""Data aggregation regressions use local fixtures and never call providers."""
import time
import unittest
from unittest.mock import patch

import free_data


def result(source, status='PUBLISHED'):
    return {
        'data': [], 'source': source, 'source_url': 'https://example.test',
        'status': status, 'checked_at': '2026-09-13T00:00:00+00:00',
        'retrieved_at': None, 'message': None, 'error_code': None,
    }


class ProviderConcurrency(unittest.TestCase):
    def slow(self, source):
        time.sleep(0.1)
        return result(source)

    def test_news_sources_do_not_delay_each_other(self):
        started = time.monotonic()
        with patch('free_data.rss', side_effect=lambda topic: self.slow(topic)), \
             patch('free_data.events', side_effect=lambda: self.slow('events')), \
             patch('free_data.world_news', side_effect=lambda: self.slow('world')):
            response = free_data.news()
        self.assertEqual(len(response['sources']), 4)
        self.assertLess(time.monotonic() - started, 0.3)

    def test_market_groups_do_not_delay_each_other(self):
        started = time.monotonic()
        with patch('free_data.crypto', side_effect=lambda: (time.sleep(0.1) or {**result('crypto', 'SNAPSHOT'), 'sources': []})), \
             patch('free_data.forex', side_effect=lambda: self.slow('forex')):
            # Give both branches the same delay so sequential execution is detectable.
            with patch('free_data.parallel', wraps=free_data.parallel):
                response = free_data.market()
        self.assertIn('sources', response)
        self.assertLess(time.monotonic() - started, 0.18)


if __name__ == '__main__':
    unittest.main()
