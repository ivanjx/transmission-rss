import unittest
from unittest.mock import patch, MagicMock
from src.transmission_client import TransmissionClient

class TestTransmissionClient(unittest.TestCase):
    @patch('src.transmission_client.requests.Session')
    def test_get_session_id_sets_session_id(self, mock_session_class):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.headers = {'X-Transmission-Session-Id': 'abc123'}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = TransmissionClient()
        client._get_session_id()
        self.assertEqual(client.session_id, 'abc123')
        mock_session.get.assert_called_once_with(client.url, timeout=client.timeout)

    @patch('src.transmission_client.requests.Session')
    def test_add_torrent_success(self, mock_session_class):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': 'success'}
        mock_response.headers = {'X-Transmission-Session-Id': 'abc123'}
        mock_session.get.return_value = mock_response
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = TransmissionClient()
        result = client.add_torrent('http://example.com/torrent')
        self.assertEqual(result, {'result': 'success'})
        self.assertEqual(client.session_id, 'abc123')
        mock_session.get.assert_called_once()
        mock_session.post.assert_called_once()

    @patch('src.transmission_client.requests.Session')
    def test_add_torrent_session_id_conflict(self, mock_session_class):
        mock_session = MagicMock()
        # First post returns 409, second returns 200
        mock_response_409 = MagicMock()
        mock_response_409.status_code = 409
        mock_response_409.headers = {'X-Transmission-Session-Id': 'newid'}
        mock_response_409.json.return_value = {'result': 'conflict'}
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.headers = {'X-Transmission-Session-Id': 'newid'}
        mock_response_200.json.return_value = {'result': 'success'}
        mock_session.get.return_value = mock_response_409
        mock_session.post.side_effect = [mock_response_409, mock_response_200]
        mock_session_class.return_value = mock_session

        client = TransmissionClient()
        result = client.add_torrent('http://example.com/torrent')
        self.assertEqual(result, {'result': 'success'})
        self.assertEqual(client.session_id, 'newid')
        self.assertEqual(mock_session.post.call_count, 2)

if __name__ == '__main__':
    unittest.main()
