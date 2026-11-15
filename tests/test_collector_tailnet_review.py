import contextlib
import io
import hashlib
import json
from pathlib import Path
import ssl
import tempfile
import time
import unittest
from unittest.mock import patch

from youtube_ops import collector_tailnet_review as review


TOKEN = 'not-a-real-token-for-unit-tests-only'


class TailnetReviewTests(unittest.TestCase):
    def test_api_credential_validation_before_store(self):
        for secret in ['', 'short', 'a' * 2049, 'a' * 16 + ' ', 'é' * 20,
                       'tskey-client-' + 'a' * 32, 'tskey-auth-' + 'a' * 32]:
            with patch.object(review.sys.stdin, 'isatty', return_value=True), \
                    patch.object(review.getpass, 'getpass', return_value=secret), \
                    patch.object(review.credentials, 'write_secret') as save, \
                    contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(review.main(['credential-save']), 1)
                save.assert_not_called()
                value = json.loads(stdout.getvalue())
                self.assertIn(value['error'], ['invalid_api_access_token', 'wrong_api_credential_type'])
                self.assertNotIn('VOICE', stdout.getvalue())
                if secret:
                    self.assertNotIn(secret, stdout.getvalue())
        for secret in ['tskey-api-' + 'a' * 32, 'tskey-' + 'a' * 32]:
            self.assertEqual(review.validate_token(secret), secret)

    def test_devices_closed_shape_and_identity(self):
        good = {'devices': [{'id': 'node-1', 'addresses': ['100.64.0.1', 'fd7a:115c:a1e0::1']}]}
        self.assertEqual(len(review.devices(json.dumps(good).encode())), 1)
        for value in [dict(good, nextPageToken='next'), {'devices': None},
                      {'devices': good['devices'] * 2},
                      {'devices': [{'id': '../escape', 'addresses': ['100.64.0.1']}]},
                      {'devices': [{'id': 'x', 'addresses': ['bad']}]}]:
            with self.assertRaises(review.Blocked):
                review.devices(json.dumps(value).encode())
        with self.assertRaises(review.Blocked):
            review.devices(b'{"devices":[],"devices":[]}')
        with patch.object(review, 'MAX_DEVICES', 0), self.assertRaises(review.Blocked):
            review.devices(json.dumps(good).encode())

    def test_routes_require_present_arrays_not_default_empty(self):
        self.assertEqual(review.routes(b'{"advertisedRoutes":[],"enabledRoutes":[]}'),
                         {'advertisedRoutes': [], 'enabledRoutes': []})
        for value in [{}, {'advertisedRoutes': []}, {'advertisedRoutes': None, 'enabledRoutes': []},
                      {'advertisedRoutes': ['bad'], 'enabledRoutes': []},
                      {'advertisedRoutes': [], 'enabledRoutes': [], 'nextPageToken': 'x'}]:
            with self.assertRaises(review.Blocked):
                review.routes(json.dumps(value).encode())
        self.assertEqual(review.routes(b'{"advertisedRoutes":[],"enabledRoutes":["10.0.0.0/8"]}')['enabledRoutes'], ['10.0.0.0/8'])

    def test_missing_credential_has_no_files_or_api(self):
        with patch.object(review.credentials, 'read_secret', side_effect=ValueError('private')) as read, \
                patch.object(review, 'private_directory') as directory, patch.object(review, 'get') as api:
            with self.assertRaisesRegex(review.Blocked, '^dedicated_credential_unavailable$'):
                review.capture('unused')
            read.assert_called_once_with(review.TARGET)
            directory.assert_not_called()
            api.assert_not_called()

    def capture_fixture(self, route_response):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        output = Path(folder.name)
        def api(path, secret, deadline):
            self.assertEqual(secret, TOKEN)
            self.assertLessEqual(deadline - time.monotonic(), 90)
            if path == review.DEVICES:
                return b'{"devices":[{"id":"node-1","addresses":["100.64.0.1"]}]}'
            if path == review.POLICY:
                return b'// Legal leading comment\n{\n// HuJSON\n"grants":[]\n}'
            self.assertEqual(path, '/api/v2/device/node-1/routes')
            if isinstance(route_response, Exception):
                raise route_response
            return route_response
        with patch.object(review.credentials, 'read_secret', return_value=(TOKEN, 1)), \
                patch.object(review, 'private_directory', return_value=output), \
                patch.object(review, 'get', side_effect=api):
            result = review.capture(output)
        receipt = json.loads((output / 'capture.private.json').read_text())
        self.assertNotIn(TOKEN, ''.join(p.read_text() for p in output.iterdir()))
        return result, receipt

    def test_complete_capture_only_not_policy_approval(self):
        result, receipt = self.capture_fixture(b'{"advertisedRoutes":["0.0.0.0/0","::/0"],"enabledRoutes":["::/0"]}')
        self.assertEqual(result['status'], 'PASS_CAPTURE_ONLY')
        self.assertTrue(receipt['routes'][0]['exit_node_advertised'])
        self.assertTrue(receipt['routes'][0]['exit_node_enabled'])
        self.assertFalse(receipt['policy_applied'])
        self.assertEqual(receipt['official_policy_evaluation'], 'NOT_TESTED')
        self.assertEqual(len(receipt['files']), 3)

    def test_unauthorized_route_and_absent_fields_stay_blocked(self):
        for response in [review.Blocked('api_http_403'), b'{}']:
            result, receipt = self.capture_fixture(response)
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertEqual(result['route_failures'], 1)
            self.assertNotIn('enabled_count', receipt['routes'][0])
            self.assertTrue(any(x['file'] == 'policy.private.hujson' for x in receipt['files']))

    def test_exclusive_files_preserve_prior_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            review.write(output, 'receipt.json', b'original')
            with self.assertRaises(FileExistsError):
                review.write(output, 'receipt.json', b'replacement')
            self.assertEqual((output / 'receipt.json').read_bytes(), b'original')

    def test_get_fixed_tls_get_no_redirect(self):
        class Response:
            status = 200
            def getheader(self, name): return None
            def read(self, size):
                value = getattr(self, 'data', b'{}')
                self.data = b''
                return value
        class Connection:
            sock = object()
            def __init__(self, host, **kwargs):
                self.host, self.kwargs, self.calls = host, kwargs, []
            def connect(self): pass
            def request(self, *args, **kwargs): self.calls.append((args, kwargs))
            def getresponse(self): return Response()
            def close(self): pass
        made = []
        def factory(*args, **kwargs):
            made.append(Connection(*args, **kwargs)); return made[-1]
        @contextlib.contextmanager
        def deadline(*args): yield (lambda _: None, lambda: None)
        with patch.object(review.http.client, 'HTTPSConnection', side_effect=factory), \
                patch.object(review, 'socket_deadline', deadline):
            self.assertEqual(review.get(review.DEVICES, TOKEN, time.monotonic() + 90), b'{}')
            self.assertEqual(made[0].host, 'api.tailscale.com')
            self.assertTrue(made[0].kwargs['context'].check_hostname)
            self.assertEqual(made[0].kwargs['context'].verify_mode, ssl.CERT_REQUIRED)
            self.assertEqual(made[0].calls[0][0], ('GET', review.DEVICES))
            for method, path in [('POST', review.POLICY), ('DELETE', review.DEVICES),
                                 ('PUT', review.VALIDATE), ('POST', '/api/v2/tailnet/-/keys')]:
                with self.assertRaisesRegex(review.Blocked, 'endpoint_denied'):
                    review.request(method, path, TOKEN, time.monotonic() + 90, b'{}')
            review.request('POST', review.VALIDATE, TOKEN, time.monotonic() + 90, b'{}')
            self.assertEqual(made[-1].calls[0][0], ('POST', review.VALIDATE))
            self.assertEqual(made[-1].calls[0][1]['body'], b'{}')
            for path in ['https://evil.test/', '/api/v2/tailnet/-/keys', '/api/v2/device/../routes']:
                with self.assertRaisesRegex(review.Blocked, 'endpoint_denied'):
                    review.get(path, TOKEN, time.monotonic() + 90)
            Response.status = 302
            with self.assertRaisesRegex(review.Blocked, '^api_http_302$'):
                review.get(review.POLICY, TOKEN, time.monotonic() + 90)
            Response.status = 200
            with patch.object(review, 'MAX_RESPONSE', 1), self.assertRaisesRegex(review.Blocked, 'response_limit'):
                review.get(review.POLICY, TOKEN, time.monotonic() + 90)
        with self.assertRaisesRegex(review.Blocked, 'capture_deadline'):
            review.get(review.DEVICES, TOKEN, time.monotonic() - 1)

    def test_credential_save_hidden_only_and_redacted_failure(self):
        with patch.object(review.sys.stdin, 'isatty', return_value=True), \
                patch.object(review.getpass, 'getpass', return_value=TOKEN), \
                patch.object(review.credentials, 'write_secret') as save, contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(review.main(['credential-save']), 0)
            save.assert_called_once_with(review.TARGET, TOKEN)
            self.assertEqual(json.loads(stdout.getvalue()), {'status': 'SAVED'})
        with patch.object(review.sys.stdin, 'isatty', return_value=False), \
                patch.object(review.getpass, 'getpass') as hidden, contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(review.main(['credential-save']), 1)
            hidden.assert_not_called()
            self.assertNotIn(TOKEN, stdout.getvalue())

    def test_pinned_validation_and_preview_never_apply(self):
        for body, expected in [(b'{}', 'PASS_OFFICIAL_VALIDATION_ONLY'),
                               (b'{"message":"test(s) failed"}', 'BLOCKED'),
                               (b'{"data":[{"errors":["private test failure"]}]}', 'BLOCKED')]:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                policy = root / 'policy.json'
                raw = b'{"tests":[{"src":"100.64.0.1","accept":["100.64.0.2:9443"]}]}'
                policy.write_bytes(raw)
                digest = hashlib.sha256(raw).hexdigest()
                output = root / 'output'; output.mkdir()
                calls = []
                def api(method, path, secret, deadline, payload):
                    self.assertEqual((method, payload, secret), ('POST', raw, TOKEN))
                    calls.append(path)
                    if path == review.VALIDATE:
                        return body
                    self.assertTrue(path.startswith(review.PREVIEW + '?'))
                    return b'{"type":"ipport","previewFor":"100.64.0.2:9443","matches":[]}'
                with patch.object(review, 'private_path', return_value=policy), \
                        patch.object(review, 'private_directory', return_value=output), \
                        patch.object(review.credentials, 'read_secret', return_value=(TOKEN, 1)), \
                        patch.object(review, 'request', side_effect=api) as request:
                    with self.assertRaisesRegex(review.Blocked, 'policy_digest_mismatch'):
                        review.validate_policy(policy, '0' * 64, output)
                    request.assert_not_called()
                    result = review.validate_policy(policy, digest, output)
                self.assertEqual(result['status'], expected)
                self.assertFalse(result['policy_applied'])
                self.assertNotIn(review.POLICY, calls)
                receipt = json.loads((output / 'validation-receipt.private.json').read_text())
                self.assertIn('started_at', receipt)
                self.assertIn('finished_at', receipt)
                if expected.startswith('PASS'):
                    self.assertEqual(receipt['preview_status'], 'CAPTURED_REQUIRES_RULE_REVIEW')
                    self.assertEqual(len(calls), 2)
                else:
                    self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
