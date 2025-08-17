import time
import logging
import feedparser
from transmission_client import TransmissionClient
from config_loader import ConfigLoader

class Aggregator:
    def __init__(self, config_path):
        self.config = ConfigLoader(config_path)
        self.client = self._init_client()
        self.logger = logging.getLogger('transmission_rss')
        self.update_interval = self.config.get_option('update_interval', 600)
        self.seen_file = self.config.get_option('seen_file', '.seen')
        self.seen = self._load_seen()

    def _load_seen(self):
        try:
            with open(self.seen_file, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f if line.strip())
        except FileNotFoundError:
            return set()

    def _save_seen(self):
        with open(self.seen_file, 'w', encoding='utf-8') as f:
            for item in sorted(self.seen):
                f.write(item + '\n')

    def _init_client(self):
        server = self.config.get_option('server', {})
        login = self.config.get_option('login', {})
        client_opts = self.config.get_option('client', {})
        return TransmissionClient(
            host=server.get('host', 'localhost'),
            port=server.get('port', 9091),
            rpc_path=server.get('rpc_path', '/transmission/rpc'),
            username=login.get('username'),
            password=login.get('password'),
            timeout=client_opts.get('timeout', 5)
        )

    def run(self):
        while True:
            self.logger.info('Checking feeds...')
            for feed in self.config.get_feeds():
                self.process_feed(feed)
            time.sleep(self.update_interval)

    def process_feed(self, feed):
        import re
        url = feed['url']
        self.logger.info(f'Fetching feed: {url}')
        parsed = feedparser.parse(url)
        link_field = feed.get('link_field', 'link')
        seen_by_guid = feed.get('seen_by_guid', False)

        regexp = feed.get('regexp')
        # If regexp is a list of matcher objects, handle advanced matching
        if isinstance(regexp, list) and regexp and isinstance(regexp[0], dict):
            matchers = []
            for matcher_obj in regexp:
                matcher_pat = matcher_obj.get('matcher')
                exclude_pat = matcher_obj.get('exclude')
                download_path = matcher_obj.get('download_path')
                matcher = re.compile(matcher_pat, re.IGNORECASE) if matcher_pat else None
                exclude = re.compile(exclude_pat, re.IGNORECASE) if exclude_pat else None
                matchers.append({'matcher': matcher, 'exclude': exclude, 'download_path': download_path})

            for entry in parsed.entries:
                title = entry.get('title', '')
                torrent_url = entry.get(link_field)
                # Determine unique ID for seen tracking
                unique_id = entry.get('guid') if seen_by_guid else torrent_url
                if unique_id in self.seen:
                    continue
                for m in matchers:
                    if m['matcher'] and m['matcher'].search(title):
                        if m['exclude'] and m['exclude'].search(title):
                            continue
                        self.client.add_torrent(torrent_url, download_dir=m['download_path'])
                        self.logger.info(f'Added torrent: {torrent_url} to {m['download_path']}')
                        self.seen.add(unique_id)
                        self._save_seen()
                        break
        else:
            # Fallback to legacy regexp/exclude logic
            exclude = feed.get('exclude')
            download_path = feed.get('download_path')
            if isinstance(regexp, list):
                regexps = [re.compile(r, re.IGNORECASE) for r in regexp]
            elif regexp:
                regexps = [re.compile(regexp, re.IGNORECASE)]
            else:
                regexps = []

            if isinstance(exclude, list):
                excludes = [re.compile(e, re.IGNORECASE) for e in exclude]
            elif exclude:
                excludes = [re.compile(exclude, re.IGNORECASE)]
            else:
                excludes = []

            for entry in parsed.entries:
                title = entry.get('title', '')
                torrent_url = entry.get(link_field)
                unique_id = entry.get('guid') if seen_by_guid else torrent_url
                if unique_id in self.seen:
                    continue
                match = True
                if regexps:
                    match = any(r.search(title) for r in regexps)
                if excludes and any(e.search(title) for e in excludes):
                    match = False
                if torrent_url and match:
                    self.client.add_torrent(torrent_url, download_dir=download_path)
                    if download_path:
                        self.logger.info(f'Added torrent: {torrent_url} to {download_path}')
                    else:
                        self.logger.info(f'Added torrent: {torrent_url}')
                    self.seen.add(unique_id)
                    self._save_seen()
