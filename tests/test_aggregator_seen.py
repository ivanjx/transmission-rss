import unittest
from unittest.mock import patch, MagicMock
import os
from src.aggregator import Aggregator

class TestAggregatorSeen(unittest.TestCase):
    @patch('feedparser.parse')
    @patch('src.aggregator.TransmissionClient')
    @patch('src.aggregator.ConfigLoader')
    def test_seen_file_logic(self, mock_config_loader, mock_transmission_client, mock_feedparser):
        # Prepare mock feedparser entries
        mock_feedparser.return_value = MagicMock(entries=[
            {'title': 'Test 1', 'link': 'url1', 'guid': 'guid1'},
            {'title': 'Test 2', 'link': 'url2', 'guid': 'guid2'},
            {'title': 'Test 3', 'link': 'url3', 'guid': 'guid3'},
        ])
        mock_client_instance = MagicMock()
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

if __name__ == '__main__':
    unittest.main()
