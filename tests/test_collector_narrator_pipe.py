import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from youtube_ops import collector_narrator_pipe as pipe


class NarratorPipeTests(unittest.TestCase):
    def test_closed_json_request(self):
        value = {'schema_version': 1, 'request_id': 'a' * 32, 'operation': 'narrator-health'}
        self.assertEqual(pipe.validate_request(pipe.decode(json.dumps(value).encode())), value)
        for extra in ({'path': 'C:/anything'}, {'text': 'anything'}, {'bearer': 'private'}, {'command': 'whoami'}):
            with self.assertRaises(pipe.BrokerError):
                pipe.validate_request({**value, **extra})
        for key, replacement in [('schema_version', True), ('request_id', '../invalid'),
                                 ('operation', 'narrator-start now'), ('operation', [])]:
            with self.assertRaises(pipe.BrokerError):
                pipe.validate_request({**value, key: replacement})
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'[]', b'x' * 65537, b'\xff'):
            with self.assertRaises(pipe.BrokerError): pipe.decode(raw)

    def make_config(self, root):
        files = {}
        for name in pipe.FILES:
            f = root / 'runtime/youtube_ops' / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(name.encode()); files[name] = hashlib.sha256(f.read_bytes()).hexdigest()
        python = root / 'runtime/python/python.exe'
        python.parent.mkdir(parents=True); python.write_bytes(b'fixture-runtime')
        config = {'schema_version': 1, 'owner_sid': 'S-1-5-21-1-2-3-1001',
            'bridge_sid': 'S-1-5-21-1-2-3-1002', 'files': files,
            'server_python_sha256': hashlib.sha256(python.read_bytes()).hexdigest(), 'manifest_sha256': 'a' * 64}
        (root / 'narrator-broker.json').write_text(json.dumps(config))
        return config

    def test_config_pins_and_replacements(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(pipe, 'ROOT', Path(folder)):
            root = Path(folder); expected = self.make_config(root)
            self.assertEqual(pipe.load_config(), expected)
            (root / 'runtime/youtube_ops/collector_narrator_control.py').write_bytes(b'replaced')
            with self.assertRaisesRegex(pipe.BrokerError, 'broker_source_changed'): pipe.load_config()

    def test_config_types_and_extra_fields(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(pipe, 'ROOT', Path(folder)):
            root = Path(folder); good = self.make_config(root)
            for edit in ({'schema_version': True}, {'files': {}}, {'owner_sid': good['bridge_sid']},
                         {'path': 'C:/anywhere'}, {'server_python_sha256': ['a' * 64]}):
                (root / 'narrator-broker.json').write_text(json.dumps({**good, **edit}))
                with self.assertRaises(pipe.BrokerError): pipe.load_config()

    def test_hardlink_denied(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / 'first', Path(folder) / 'second'
            first.write_bytes(b'x'); os.link(first, second)
            with self.assertRaises(pipe.BrokerError): pipe.local_file(first)

    @unittest.skipUnless(os.name == 'nt', 'Windows security APIs')
    def test_inspection_acl_rejects_wrong_owner_and_elevation_before_mutation(self):
        config = {'owner_sid': 'S-1-5-21-1-2-3-1001', 'bridge_sid': 'S-1-5-21-1-2-3-1002'}
        for identity in ((config['bridge_sid'], False), (config['owner_sid'], True)):
            with patch.object(pipe, 'windows_identity', return_value=identity):
                with self.assertRaisesRegex(pipe.BrokerError, 'broker_owner_context_required'):
                    pipe.allow_bridge_inspection(config)

    @unittest.skipUnless(os.name == 'nt', 'Windows security APIs')
    def test_native_client_sid_is_checked_after_message(self):
        import _winapi
        name = r'\\.\pipe\KnowledgeNetworkCollectorTest-' + uuid.uuid4().hex
        server = _winapi.CreateNamedPipe(name, 3 | 0x40000000 | 0x80000, 4 | 2 | 8, 1, 65536, 65536, 0, 0)
        client = None
        try:
            ov = _winapi.ConnectNamedPipe(server, overlapped=True)
            client = _winapi.CreateFile(name, 0xC0000000, 0, 0, 3, 0x40000000 | 0x110000, 0)
            pipe._wait(ov, time.monotonic() + 2, threading.Event())
            pipe.send(client, {'probe': True}, time.monotonic() + 2, threading.Event())
            pipe.receive(server, time.monotonic() + 2, threading.Event())
            original = pipe.windows_identity()
            with self.assertRaisesRegex(pipe.BrokerError, 'broker_client_denied'):
                pipe.verify_client(server, {'bridge_sid': 'S-1-5-21-1-2-3-1002'})
            # Native impersonation returned a token and reverted even on the denial.
            self.assertEqual(pipe.windows_identity(), original)
        finally:
            if client is not None: _winapi.CloseHandle(client)
            _winapi.CloseHandle(server)

    @unittest.skipUnless(os.name == 'nt', 'Windows pipe APIs')
    def test_native_message_bounds_and_timeout(self):
        import _winapi
        name = r'\\.\pipe\KnowledgeNetworkCollectorTest-' + uuid.uuid4().hex
        server = _winapi.CreateNamedPipe(name, 3 | 0x40000000 | 0x80000, 4 | 2 | 8, 1, 65536, 65536, 0, 0)
        client = None
        try:
            ov = _winapi.ConnectNamedPipe(server, overlapped=True)
            client = _winapi.CreateFile(name, 0xC0000000, 0, 0, 3, 0x40000000 | 0x110000, 0)
            _winapi.SetNamedPipeHandleState(client, 2, None, None)
            pipe._wait(ov, time.monotonic() + 2, threading.Event())
            pipe.send(client, {'status': 'fixture'}, time.monotonic() + 2, threading.Event())
            self.assertEqual(pipe.receive(server, time.monotonic() + 2, threading.Event()), {'status': 'fixture'})
            with self.assertRaisesRegex(pipe.BrokerError, 'broker_outcome_unknown'):
                pipe.receive(server, time.monotonic() + .1, threading.Event())
            with self.assertRaisesRegex(pipe.BrokerError, 'broker_message_invalid'):
                pipe.send(client, {'x': 'a' * 65536}, time.monotonic() + 2, threading.Event())
            cancelled = threading.Event(); cancelled.set()
            with self.assertRaises(pipe.BrokerError):
                pipe.receive(server, time.monotonic() + 2, cancelled)
        finally:
            if client is not None: _winapi.CloseHandle(client)
            _winapi.CloseHandle(server)

    @unittest.skipUnless(os.name == 'nt', 'Windows pipe APIs')
    def test_native_pipe_owner_wrong_runtime_and_first_instance(self):
        import _winapi
        sid, _ = pipe.windows_identity()
        name = r'\\.\pipe\KnowledgeNetworkCollectorTest-' + uuid.uuid4().hex
        config = {'owner_sid': sid, 'bridge_sid': sid}
        stop, seen = threading.Event(), []
        def handler(request):
            seen.append(request)
            return {'status': 'fixture'}
        # Identity is checked separately below; this tests the production DACL and framing.
        with patch.object(pipe, 'PIPE', name), patch.object(pipe, 'verify_client'):
            failures = []
            def run():
                try: pipe.serve(config, handler, stop)
                except Exception as exc: failures.append(exc)
            thread = threading.Thread(target=run); thread.start()
            client = None
            try:
                deadline = time.monotonic() + 3
                while client is None and time.monotonic() < deadline:
                    try:
                        client = _winapi.CreateFile(name, 0x120103, 0, 0, 3, 0x40000000 | 0x110000, 0)
                    except OSError: time.sleep(.02)
                self.assertIsNotNone(client, str(failures))
                with self.assertRaises(OSError):
                    _winapi.CreateNamedPipe(name, 3 | 0x40000000 | 0x80000, 4 | 2 | 8, 1, 65536, 65536, 0, 0)
                _winapi.SetNamedPipeHandleState(client, 2, None, None)
                with self.assertRaisesRegex(pipe.BrokerError, 'broker_server_process_unverified'):
                    pipe.verify_server(client, config)
                self.assertEqual(seen, [])  # No request bytes before failed identity verification.
                request = {'schema_version': 1, 'request_id': 'a' * 32, 'operation': 'narrator-health'}
                pipe.send(client, request, time.monotonic() + 2, threading.Event())
                self.assertEqual(pipe.receive(client, time.monotonic() + 2, threading.Event()), {'status': 'fixture'})
                self.assertEqual(seen, [request])
            finally:
                stop.set()
                if client is not None: _winapi.CloseHandle(client)
                thread.join(timeout=3)
                self.assertFalse(thread.is_alive())
            self.assertEqual(failures, [])


if __name__ == '__main__':
    unittest.main()
