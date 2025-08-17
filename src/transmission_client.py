import requests

class TransmissionClient:
    def __init__(self, host='localhost', port=9091, rpc_path='/transmission/rpc', username=None, password=None, timeout=5):
        self.url = f'http://{host}:{port}{rpc_path}'
        self.session = requests.Session()
        if username and password:
            self.session.auth = (username, password)
        self.timeout = timeout
        self.session_id = None

    def _get_session_id(self):
        resp = self.session.get(self.url, timeout=self.timeout)
        self.session_id = resp.headers.get('X-Transmission-Session-Id')

    def add_torrent(self, torrent_url, paused=False, download_dir=None):
        if not self.session_id:
            self._get_session_id()
        headers = {'X-Transmission-Session-Id': self.session_id}
        data = {
            'method': 'torrent-add',
            'arguments': {
                'filename': torrent_url,
                'paused': paused
            }
        }
        if download_dir:
            data['arguments']['download-dir'] = download_dir
        resp = self.session.post(self.url, json=data, headers=headers, timeout=self.timeout)
        if resp.status_code == 409:
            self.session_id = resp.headers.get('X-Transmission-Session-Id')
            headers['X-Transmission-Session-Id'] = self.session_id
            resp = self.session.post(self.url, json=data, headers=headers, timeout=self.timeout)
        return resp.json()
