import time
import logging
import feedparser
import re
import requests
import defusedxml
try:
    from .transmission_client import TransmissionClient
    from .config_loader import ConfigLoader
except (ImportError, ValueError):
    from transmission_client import TransmissionClient
    from config_loader import ConfigLoader

# Configure feedparser to use defusedxml for safe XML parsing
feedparser.PREFERRED_XML_PARSERS = ['defusedxml']

class Aggregator:
    def __init__(self, config_path):
        self.config = ConfigLoader(config_path)
        self.client = self._init_client()
        self.logger = logging.getLogger('transmission_rss')
        self.update_interval = self.config.get_option('update_interval', 600)
        self.seen_file = self.config.get_option('seen_file', '.seen')
        self.seen = self._load_seen()
        self.global_add_paused = self.config.get_option('add_paused', False)

    def _load_seen(self):
        try:
            with open(self.seen_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            return []

    def _save_seen(self):
        # Filter out None values and limit to the most recent 100 items
        seen_list = [item for item in self.seen if item is not None]
        if len(seen_list) > 100:
            # Keep only the last 100 items (most recent)
            seen_list = seen_list[-100:]
            self.seen = seen_list
        with open(self.seen_file, 'w', encoding='utf-8') as f:
            for item in seen_list:
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

    def _add_torrent(self, torrent_url, title, unique_id, add_paused, download_path, delay_time):
        self.logger.info(f'Adding torrent ({torrent_url}) for ({title})')
        try:
            result = self.client.add_torrent(torrent_url, paused=add_paused, download_dir=download_path)
            # Check if the torrent was added successfully
            if result and 'result' in result:
                if result['result'] == 'success':
                    self.logger.info(f'Successfully added torrent: {title}')
                    if unique_id and unique_id not in self.seen:
                        self.seen.append(unique_id)
                    self._save_seen()
                    if delay_time:
                        time.sleep(float(delay_time))
                    return True
                else:
                    self.logger.error(f'Transmission returned error for {title}: {result.get("result", "unknown error")}')
            else:
                self.logger.error(f'Unexpected response format when adding torrent {title}: {result}')
        except Exception as e:
            self.logger.error(f'Unexpected error when adding torrent {title}: {e}')
        return False

    def run(self):
        while True:
            for feed in self.config.get_feeds():
                self.process_feed(feed)
            time.sleep(self.update_interval)

    def process_feed(self, feed):
        url = feed['url']
        link_field = feed.get('link_field', 'link')
        seen_by_guid = feed.get('seen_by_guid', False)
        add_paused = feed.get('add_paused', self.global_add_paused)
        delay_time = feed.get('delay_time', None)
        regexp = feed.get('regexp')
        self.logger.info(f'Fetching feed: {url}')
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Validate content type (warn but don't reject)
            content_type = response.headers.get('content-type', '').lower()
            valid_content_types = [
                'application/rss+xml',
                'application/xml',
                'text/xml'
            ]
            is_expected_type = (
                any(content_type.startswith(ct) for ct in valid_content_types) or
                'xml' in content_type
            )
            if content_type and not is_expected_type:
                self.logger.warning(f'Unexpected content type for {url}: {content_type}')

            # Limit response size to prevent billion laughs attacks
            max_size = 10 * 1024 * 1024  # 10MB limit
            if len(response.content) > max_size:
                self.logger.error(f'Feed content too large for {url}: {len(response.content)} bytes')
                return

            parsed = feedparser.parse(response.content)

            # Validate that we have a valid feed structure
            if not hasattr(parsed, 'entries'):
                self.logger.error(f'Invalid RSS feed structure from {url}')
                return

            # Only reject if parsing completely failed (bozo=True and no entries)
            if parsed.bozo and len(parsed.entries) == 0:
                self.logger.error(f'Malformed RSS feed from {url}')
                if hasattr(parsed, 'bozo_exception'):
                    self.logger.error(f'Parse error: {parsed.bozo_exception}')
                return

        except requests.exceptions.RequestException as e:
            self.logger.error(f'Failed to fetch RSS feed: {e}')
            return
        except Exception as e:
            self.logger.error(f'Failed to parse RSS feed: {e}')
            return

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
                if not torrent_url:
                    self.logger.warning(f'No torrent URL found in entry: {entry}')
                    continue
                unique_id = entry.get('guid') if seen_by_guid else torrent_url
                if not unique_id or unique_id in self.seen:
                    continue
                for matcher in matchers:
                    download_path = matcher['download_path']
                    if matcher['matcher'] and matcher['matcher'].search(title):
                        if matcher['exclude'] and matcher['exclude'].search(title):
                            continue
                        self._add_torrent(torrent_url, title, unique_id, add_paused, download_path, delay_time)
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
                if not torrent_url:
                    self.logger.warning(f'No torrent URL found in entry: {entry}')
                    continue
                unique_id = entry.get('guid') if seen_by_guid else torrent_url
                if not unique_id or unique_id in self.seen:
                    continue
                match = True
                if regexps:
                    match = any(r.search(title) for r in regexps)
                if excludes and any(e.search(title) for e in excludes):
                    match = False
                if torrent_url and match:
                    self._add_torrent(torrent_url, title, unique_id, add_paused, download_path, delay_time)

        if len(parsed.entries) > 0:
            self.logger.info(f'Last processed entry: {parsed.entries[0].get(link_field, "unknown")}')
