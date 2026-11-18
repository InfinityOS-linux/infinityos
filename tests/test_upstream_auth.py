import importlib.machinery
import importlib.util
import os
from pathlib import Path
from urllib.request import HTTPRedirectHandler
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('upstream_auth', str(ROOT / 'scripts/resolve-infinity-upstream'))
spec = importlib.util.spec_from_loader(loader.name, loader)
upstream = importlib.util.module_from_spec(spec)
loader.exec_module(upstream)


class UpstreamAuthTests(unittest.TestCase):
    def request_for(self, url, token='build-token'):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{}'
        with patch.dict(os.environ, {'GH_TOKEN': token, 'GITHUB_TOKEN': ''}), patch.object(upstream, 'urlopen', return_value=response) as fetch:
            self.assertEqual(upstream.fetch(url), b'{}')
            return fetch.call_args.args[0]

    def test_api_uses_build_token_without_forwarding_it_on_redirects(self):
        request = self.request_for('https://api.github.com/repos/owner/project/releases/latest')
        self.assertEqual(request.get_header('Authorization'), 'Bearer build-token')
        for target in ('https://api.github.com/repos/new/name/releases/latest', 'https://example.com/asset'):
            redirected = HTTPRedirectHandler().redirect_request(request, None, 302, 'Found', {}, target)
            self.assertIsNone(redirected.get_header('Authorization'))

    def test_other_origins_and_plain_http_never_receive_the_token(self):
        for url in ('https://raw.githubusercontent.com/owner/project/main/LICENSE',
                    'https://addons.mozilla.org/api/v5/addons/addon/example/',
                    'http://api.github.com/repos/owner/project/releases/latest',
                    'https://api.github.com.example.com/releases/latest'):
            with self.subTest(url=url):
                self.assertIsNone(self.request_for(url).get_header('Authorization'))

    def test_local_build_without_token_still_works(self):
        self.assertIsNone(self.request_for('https://api.github.com/repos/owner/project/releases/latest', '').get_header('Authorization'))
