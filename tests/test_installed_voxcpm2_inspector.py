"""Synthetic filesystem tests; no installed host model is inspected."""
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

    def test_file_count_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for number in range(257):
                (repo / str(number)).touch()
            with self.assertRaisesRegex(ValueError, 'model_inventory_limit'):
                probe.catalog(repo, repo)


if __name__ == '__main__':
    unittest.main()
