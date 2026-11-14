"""MOCK inference over real FORGE loopback HTTP; not host, TLS or speech proof."""
import http.client
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
import wave

from youtube_ops.collector_narration_common import inspect_wav
from youtube_ops.collector_narrator_host import NarratorHTTPServer, NarratorStore
from youtube_ops.collector_voxcpm2 import RemoteVoxCPM2Provider


class SimulatedNarrator:
    provenance = dict(script_sha256='a' * 64, config_sha256='b' * 64,
                      model_revision='MOCK-contract-test', license_evidence_sha256='c' * 64)

    def verify(self):
        pass


class NarratorContractTests(unittest.TestCase):
    def test_two_measured_segments_cross_actual_http_contract(self):
        def synthetic_executor(text, output, cancel):
            with wave.open(str(output), 'wb') as audio:
                audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                audio.writeframes(b'\x01\x00' * (1600 if text == 'First.' else 3200))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            host, forge = root / 'host', root / 'forge'
            host.mkdir(); forge.mkdir()
            store = NarratorStore(host, SimulatedNarrator(), synthetic_executor)
            server = NarratorHTTPServer(('127.0.0.1', 0), store, 'x' * 32)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start(); store.start()
            url = 'https://contract-test.invalid'
            route = dict(schema_version=1, base_url=url, host_identity='BLACKHAT-BASE',
                         transport='https', auth_mode='scoped_bearer',
                         pinned_addresses=['100.64.0.1'], verified_by='MOCK fixture',
                         verified_at='2026-11-14', transport_evidence_sha256='d' * 64,
                         expected_provenance=SimulatedNarrator.provenance)
            provider = RemoteVoxCPM2Provider(url, route, forge)

            def loopback_connection(timeout, register):
                connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=timeout)
                connection.connect(); register(connection.sock)
                return connection

            try:
                with patch.object(provider, '_connect', side_effect=loopback_connection), \
                        patch('youtube_ops.collector_voxcpm2.read_credential', return_value=('x' * 32, 1)):
                    result = provider.generate('e' * 32, 'First. Second.', segments=['First.', 'Second.'])
                    self.assertEqual(provider.status()['status'], 'PASS')
                    repeated = provider.generate('e' * 32, 'First. Second.', segments=['First.', 'Second.'])
                self.assertEqual(result, repeated)
                self.assertEqual(result['audio'], inspect_wav(forge / ('e' * 32) / 'narration.wav'))
                self.assertEqual(result['audio']['frames'], 4800)
                self.assertEqual([(cue['start_sample'], cue['end_sample']) for cue in result['cues']],
                                 [(0, 1600), (1600, 4800)])
                self.assertFalse(result['publication_eligible'])
                self.assertEqual(store.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 2)
            finally:
                server.shutdown(); thread.join(timeout=5); server.server_close(); store.close()
