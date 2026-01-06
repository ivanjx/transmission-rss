import unittest
from unittest.mock import patch, MagicMock
import os
from src.aggregator import Aggregator

class TestAggregatorSeen(unittest.TestCase):
    @patch('src.aggregator.requests.get')
    @patch('feedparser.parse')
    @patch('src.aggregator.TransmissionClient')
    @patch('src.aggregator.ConfigLoader')
    def test_seen_file_logic(self, mock_config_loader, mock_transmission_client, mock_feedparser, mock_requests_get):
        # Mock requests.get to return a successful response
        mock_response = MagicMock()
        mock_response.content = b'mock content'
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        # Prepare mock feedparser entries
        mock_feedparser.return_value = MagicMock(entries=[
            {'title': 'Test 1', 'link': 'url1', 'guid': 'guid1'},
            {'title': 'Test 2', 'link': 'url2', 'guid': 'guid2'},
            {'title': 'Test 3', 'link': 'url3', 'guid': 'guid3'},
        ])
        mock_client_instance = MagicMock()
        mock_client_instance.add_torrent.return_value = {'result': 'success'}
        mock_transmission_client.return_value = mock_client_instance

        # Use a temp seen file
        seen_file = 'test_seen_file.txt'
        if os.path.exists(seen_file):
            os.remove(seen_file)

        # Config with seen_by_guid enabled
        mock_config = MagicMock()
        mock_config.get_feeds.return_value = [{
            'url': 'http://example.com/feed',
            'seen_by_guid': True
        }]
        mock_config.get_option.side_effect = lambda k, d=None: seen_file if k == 'seen_file' else d
        mock_config_loader.return_value = mock_config

        agg = Aggregator('dummy_path')
        agg.logger = MagicMock()  # Mock logger to avoid logging issues
        agg.process_feed({'url': 'http://example.com/feed', 'seen_by_guid': True})

        # Should call add_torrent for all entries
        self.assertEqual(mock_client_instance.add_torrent.call_count, 3)
        # Seen file should contain all GUIDs
        with open(seen_file, 'r', encoding='utf-8') as f:
            seen_guids = set(line.strip() for line in f)
        self.assertEqual(seen_guids, {'guid1', 'guid2', 'guid3'})

        # Second run: should not call add_torrent again
        mock_client_instance.add_torrent.reset_mock()
        agg.seen = agg._load_seen()  # reload seen from file
        agg.process_feed({'url': 'http://example.com/feed', 'seen_by_guid': True})
        self.assertEqual(mock_client_instance.add_torrent.call_count, 0)

        # Cleanup
        os.remove(seen_file)

    @patch('src.aggregator.requests.get')
    @patch('feedparser.parse')
    @patch('src.aggregator.TransmissionClient')
    @patch('src.aggregator.ConfigLoader')
    def test_seen_file_limit_100(self, mock_config_loader, mock_transmission_client, mock_feedparser, mock_requests_get):
        # Mock requests.get to return a successful response
        mock_response = MagicMock()
        mock_response.content = b'mock content'
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        # Prepare mock feedparser entries with 105 items
        entries = [{'title': f'Test {i}', 'link': f'url{i}', 'guid': f'guid{i}'} for i in range(105)]
        mock_feedparser.return_value = MagicMock(entries=entries)
        mock_client_instance = MagicMock()
        mock_client_instance.add_torrent.return_value = {'result': 'success'}
        mock_transmission_client.return_value = mock_client_instance

        # Use a temp seen file
        seen_file = 'test_seen_file_limit.txt'
        if os.path.exists(seen_file):
            os.remove(seen_file)

        # Config with seen_by_guid enabled
        mock_config = MagicMock()
        mock_config.get_feeds.return_value = [{
            'url': 'http://example.com/feed',
            'seen_by_guid': True
        }]
        mock_config.get_option.side_effect = lambda k, d=None: seen_file if k == 'seen_file' else d
        mock_config_loader.return_value = mock_config

        agg = Aggregator('dummy_path')
        agg.logger = MagicMock()  # Mock logger to avoid logging issues
        agg.process_feed({'url': 'http://example.com/feed', 'seen_by_guid': True})

        # Should call add_torrent for all 105 entries
        self.assertEqual(mock_client_instance.add_torrent.call_count, 105)
        # Seen file should contain only the last 100 GUIDs (most recent)
        with open(seen_file, 'r', encoding='utf-8') as f:
            seen_lines = [line.strip() for line in f if line.strip()]
        self.assertEqual(len(seen_lines), 100)
        # The first line should be guid5 (since 0-4 are trimmed, 5-104 kept, but wait: added 0 to 104, last 100 are 5 to 104
        # Wait, range(105) is 0 to 104, so last 100 are 5 to 104
        self.assertEqual(seen_lines[0], 'guid5')
        self.assertEqual(seen_lines[-1], 'guid104')

        # Cleanup
        os.remove(seen_file)

if __name__ == '__main__':
    unittest.main()
