"""Synthetic filesystem tests; no installed host model is inspected."""
import contextlib
import io
import json
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('installed_probe', Path(__file__).resolve().parents[1] /
    'docs/collector/host-tools/inspect_installed_voxcpm2.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class InventoryBoundsTests(unittest.TestCase):
    def test_real_fixture_files_hash_and_empty_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            snapshot = repo / 'snapshots' / ('a' * 40)
            snapshot.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, 'empty_snapshot'):
                probe.catalog(snapshot, repo)
            (snapshot / 'config.json').write_text('{}')
            # Python 3.11 lacks is_junction; inventory must not call it.
            with patch.object(Path, 'is_junction', side_effect=AssertionError('3.12 API'), create=True):
                result = probe.catalog(snapshot, repo)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['sha256'], probe.sha(snapshot / 'config.json'))

    def test_snapshot_outside_repository_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'repo'
            repo.mkdir()
            with self.assertRaisesRegex(ValueError, 'snapshot_escape'):
                probe.catalog(Path(tmp), repo)

    def test_total_bytes_denied_before_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / 'weight').write_bytes(b'12345')
            with patch.object(probe, 'MAX_MODEL_BYTES', 4), patch.object(probe, 'sha') as hashed:
                with self.assertRaisesRegex(ValueError, 'model_byte_limit'):
                    probe.catalog(repo, repo)
                hashed.assert_not_called()

    def test_main_redacts_failure_and_writes_only_after_acl_verified(self):
        for acl_ok in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                fake_script = Path(tmp) / 'inspector.py'
                output = io.StringIO()
                with patch.object(probe, '__file__', str(fake_script)), patch.object(probe.sys, 'argv', ['probe']), \
                     patch.object(probe, '_system_powershell', return_value='trusted-powershell'), \
                     patch.object(probe.subprocess, 'run', return_value=type('Result', (), {'returncode': 0})()), \
                     patch.object(probe, 'verify_spool_acl', side_effect=None if acl_ok else RuntimeError('PRIVATE_SECRET')), \
                     patch.object(probe, 'inspect', side_effect=RuntimeError('PRIVATE_SECRET')), \
                     contextlib.redirect_stdout(output):
                    self.assertEqual(probe.main(), 1)
                self.assertNotIn('PRIVATE_SECRET', output.getvalue())
                self.assertNotIn(tmp, output.getvalue())
                reports = list(Path(tmp).glob('*/failure.json'))
                self.assertEqual(len(reports), int(acl_ok))
                if reports:
                    report = json.loads(reports[0].read_text())
                    self.assertEqual(report['stage'], 'inspection')
                    self.assertEqual(report['exception_type'], 'RuntimeError')
                    self.assertNotIn('PRIVATE_SECRET', reports[0].read_text())

    def test_file_count_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for number in range(257):
                (repo / str(number)).touch()
            with self.assertRaisesRegex(ValueError, 'model_inventory_limit'):
                probe.catalog(repo, repo)


if __name__ == '__main__':
    unittest.main()
