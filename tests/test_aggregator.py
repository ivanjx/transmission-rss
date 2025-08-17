import unittest
from unittest.mock import patch, MagicMock
import feedparser
from src.aggregator import Aggregator
from src.transmission_client import TransmissionClient
from src.config_loader import ConfigLoader

NYAA_RSS = '''<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:atom="http://www.w3.org/2005/Atom" xmlns:nyaa="https://nyaa.si/xmlns/nyaa" version="2.0">
<channel>
<title>Nyaa - Home - Torrent File RSS</title>
<description>RSS Feed for Home</description>
<link>https://nyaa.si/</link>
<atom:link href="https://nyaa.si/?page=rss" rel="self" type="application/rss+xml"/>
<item>
<title>One Piece S01E1140 VOSTFR 1080p WEB x264 AAC -Tsundere-Raws (ADN)</title>
<link>https://nyaa.si/download/2007666.torrent</link>
<guid isPermaLink="true">https://nyaa.si/view/2007666</guid>
<pubDate>Sun, 17 Aug 2025 18:00:37 -0000</pubDate>
<nyaa:seeders>12</nyaa:seeders>
<nyaa:leechers>13</nyaa:leechers>
<nyaa:downloads>14</nyaa:downloads>
<nyaa:infoHash>957448e40d163af61b57cf05fa25ec92bc55ea7c</nyaa:infoHash>
<nyaa:categoryId>1_3</nyaa:categoryId>
<nyaa:category>Anime - Non-English-translated</nyaa:category>
<nyaa:size>564.0 MiB</nyaa:size>
<nyaa:comments>0</nyaa:comments>
<nyaa:trusted>No</nyaa:trusted>
<nyaa:remake>No</nyaa:remake>
<description>
<![CDATA[ <a href="https://nyaa.si/view/2007666">#2007666 | One Piece S01E1140 VOSTFR 1080p WEB x264 AAC -Tsundere-Raws (ADN)</a> | 564.0 MiB | Anime - Non-English-translated | 957448E40D163AF61B57CF05FA25EC92BC55EA7C ]]>
</description>
</item>
<item>
<title>One Piece S01E1140 VOSTFR 720p WEB x264 AAC -Tsundere-Raws (ADN)</title>
<link>https://nyaa.si/download/2007665.torrent</link>
<guid isPermaLink="true">https://nyaa.si/view/2007665</guid>
<pubDate>Sun, 17 Aug 2025 18:00:29 -0000</pubDate>
<nyaa:seeders>4</nyaa:seeders>
<nyaa:leechers>2</nyaa:leechers>
<nyaa:downloads>2</nyaa:downloads>
<nyaa:infoHash>5616f794088be7437993ce01139e3f5afc4fd32d</nyaa:infoHash>
<nyaa:categoryId>1_3</nyaa:categoryId>
<nyaa:category>Anime - Non-English-translated</nyaa:category>
<nyaa:size>290.8 MiB</nyaa:size>
<nyaa:comments>0</nyaa:comments>
<nyaa:trusted>No</nyaa:trusted>
<nyaa:remake>No</nyaa:remake>
<description>
<![CDATA[ <a href="https://nyaa.si/view/2007665">#2007665 | One Piece S01E1140 VOSTFR 720p WEB x264 AAC -Tsundere-Raws (ADN)</a> | 290.8 MiB | Anime - Non-English-translated | 5616F794088BE7437993CE01139E3F5AFC4FD32D ]]>
</description>
</item>
</channel>
</rss>'''

class TestAggregator(unittest.TestCase):
    @patch('feedparser.parse')
    @patch('src.aggregator.TransmissionClient')
    @patch('src.aggregator.ConfigLoader')
    def test_link_field_option(self, mock_config_loader, mock_transmission_client, mock_feedparser):
        # Prepare a mock for feedparser.parse with infoHash field
        mock_feedparser.return_value = MagicMock(entries=[
            {'nyaa_infohash': '957448e40d163af61b57cf05fa25ec92bc55ea7c'},
            {'nyaa_infohash': '5616f794088be7437993ce01139e3f5afc4fd32d'}
        ])
        mock_client_instance = MagicMock()
        mock_client_instance.add_torrent.return_value = {'result': 'success'}
        mock_transmission_client.return_value = mock_client_instance

        # Mock config loader to return feeds with link_field set to infoHash
        mock_config = MagicMock()
        mock_config.get_feeds.return_value = [{'url': 'https://nyaa.si/?page=rss', 'link_field': 'nyaa_infohash'}]
        mock_config.get_option.side_effect = lambda k, d=None: d
        mock_config_loader.return_value = mock_config

        agg = Aggregator('dummy_path')
        agg.process_feed({'url': 'https://nyaa.si/?page=rss', 'link_field': 'nyaa_infohash'})

        # Should call add_torrent for each item using infoHash
        self.assertEqual(mock_client_instance.add_torrent.call_count, 2)
        calls = [call[0][0] for call in mock_client_instance.add_torrent.call_args_list]
        self.assertIn('957448e40d163af61b57cf05fa25ec92bc55ea7c', calls)
        self.assertIn('5616f794088be7437993ce01139e3f5afc4fd32d', calls)

    @patch('feedparser.parse')
    @patch('src.aggregator.TransmissionClient')
    @patch('src.aggregator.ConfigLoader')
    def test_nyaa_feed_and_transmission(self, mock_config_loader, mock_transmission_client, mock_feedparser):
        # Prepare a mock for feedparser.parse with link field
        mock_feedparser.return_value = MagicMock(entries=[
            {'link': 'https://nyaa.si/download/2007666.torrent'},
            {'link': 'https://nyaa.si/download/2007665.torrent'}
        ])
        mock_client_instance = MagicMock()
        mock_client_instance.add_torrent.return_value = {'result': 'success'}
        mock_transmission_client.return_value = mock_client_instance

        # Mock config loader to return feeds
        mock_config = MagicMock()
        mock_config.get_feeds.return_value = [{'url': 'https://nyaa.si/?page=rss'}]
        mock_config.get_option.side_effect = lambda k, d=None: d
        mock_config_loader.return_value = mock_config

        agg = Aggregator('dummy_path')
        agg.process_feed({'url': 'https://nyaa.si/?page=rss'})

        # Should call add_torrent for each item in the feed
        self.assertEqual(mock_client_instance.add_torrent.call_count, 2)
        calls = [call[0][0] for call in mock_client_instance.add_torrent.call_args_list]
        self.assertIn('https://nyaa.si/download/2007666.torrent', calls)
        self.assertIn('https://nyaa.si/download/2007665.torrent', calls)

if __name__ == '__main__':
    unittest.main()
