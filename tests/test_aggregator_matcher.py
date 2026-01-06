import unittest
from unittest.mock import patch, MagicMock
import os
from src.aggregator import Aggregator

class TestAggregatorMatcher(unittest.TestCase):
    @patch('src.aggregator.requests.get')
    @patch('feedparser.parse')
    @patch('src.aggregator.TransmissionClient')
    @patch('src.aggregator.ConfigLoader')
    def test_advanced_matcher(self, mock_config_loader, mock_transmission_client, mock_feedparser, mock_requests_get):
        # Mock requests.get to return a successful response
        mock_response = MagicMock()
        mock_response.content = b'mock content'
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response

        # Prepare mock feedparser entries
        mock_feedparser.return_value = MagicMock(entries=[
            {'title': '[ASW] Anne Shirley 1080p', 'link': 'url1'},
            {'title': '[ASW] Witch Watch 1080p', 'link': 'url2'},
            {'title': '[ASW] Anne Shirley 720p', 'link': 'url3'},
            {'title': '[TOONSHUB] Sakamoto Days English-Sub 1080p', 'link': 'url4'},
            {'title': '[TOONSHUB] Sakamoto Days English-Sub REPACK 1080p', 'link': 'url5'},
            {'title': '[TOONSHUB] Nyaight of the Living Cat Dual-Audio 1080p', 'link': 'url6'},
            {'title': '[TOONSHUB] Nyaight of the Living Cat 1080p', 'link': 'url7'},
        ])
        mock_client_instance = MagicMock()
        mock_client_instance.add_torrent.return_value = {'result': 'success'}
        mock_transmission_client.return_value = mock_client_instance

        # Use a temp seen file
        seen_file = 'test_seen_file_matcher.txt'
        if os.path.exists(seen_file):
            os.remove(seen_file)

        # Advanced matcher config
        matcher_config = [
            {'matcher': r'(?=.*asw)(?=.*anne)(?=.*shirley)(?=.*1080p).*', 'download_path': '/share/Movies/Anne Shirley'},
            {'matcher': r'(?=.*asw)(?=.*witch)(?=.*watch)(?=.*1080p).*', 'download_path': '/share/Movies/Witch Watch'},
            {'matcher': r'(?=.*toonshub)(?=.*sakamoto)(?=.*days)(?=.*sub)(?=.*1080p).*', 'exclude': 'REPACK', 'download_path': '/share/Movies/Sakamoto Days/Sakamoto Days S2'},
            {'matcher': r'(?=.*toonshub)(?=.*nyaight)(?=.*cat)(?=.*1080p).*', 'exclude': 'Dual-Audio', 'download_path': '/share/Movies/Nyaight of the Living Cat'},
        ]
        mock_config = MagicMock()
        mock_config.get_feeds.return_value = [{
            'url': 'http://example.com/feed',
            'regexp': matcher_config
        }]
        mock_config.get_option.side_effect = lambda k, d=None: seen_file if k == 'seen_file' else d
        mock_config_loader.return_value = mock_config

        agg = Aggregator('dummy_path')
        agg.process_feed({'url': 'http://example.com/feed', 'regexp': matcher_config})

        # Should call add_torrent for matching entries, with correct download_path
        calls = [call[0][0] for call in mock_client_instance.add_torrent.call_args_list]
        paths = [call[1].get('download_dir') for call in mock_client_instance.add_torrent.call_args_list]
        self.assertIn('url1', calls)
        self.assertIn('url2', calls)
        self.assertIn('url4', calls)
        self.assertIn('url7', calls)
        self.assertNotIn('url3', calls)  # 720p should not match
        self.assertNotIn('url5', calls)  # REPACK should be excluded
        self.assertNotIn('url6', calls)  # Dual-Audio should be excluded
        self.assertIn('/share/Movies/Anne Shirley', paths)
        self.assertIn('/share/Movies/Witch Watch', paths)
        self.assertIn('/share/Movies/Sakamoto Days/Sakamoto Days S2', paths)
        self.assertIn('/share/Movies/Nyaight of the Living Cat', paths)

        # Cleanup
        if os.path.exists(seen_file):
            os.remove(seen_file)

if __name__ == '__main__':
    unittest.main()
