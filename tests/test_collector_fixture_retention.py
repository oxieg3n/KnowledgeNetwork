"""Owner policy: fixture teardown preserves bytes instead of deleting them."""
from tests.fixture_retention import FixtureDirectory, retain_fixture_entry
import hashlib
import json
from pathlib import Path
import unittest



class FixtureRetentionTests(unittest.TestCase):
    def test_closed_fixture_is_retained_with_private_inventory(self):
        fixture = FixtureDirectory(prefix='kn-retention-test-')
        source = Path(fixture.name) / 'owned-result.txt'
        self.assertIn('KnowledgeNetwork-Private', source.parts)
        source.write_bytes(b'owned fixture result')
        fixture.cleanup()
        self.assertEqual(source.read_bytes(), b'owned fixture result')
        receipt = json.loads(fixture.receipt.read_text(encoding='utf-8'))
        self.assertFalse(receipt['deletion_performed'])
        self.assertFalse(receipt['archive_performed'])
        self.assertEqual(receipt['files'][0]['sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
        first = fixture.receipt
        fixture.cleanup()
        self.assertEqual(fixture.receipt, first)

    def test_changed_identity_leaves_original_in_place(self):
        fixture = FixtureDirectory(prefix='kn-retention-test-')
        source = Path(fixture.name) / 'must-remain.txt'
        source.write_bytes(b'keep')
        fixture._identity = (-1, -1)
        fixture.cleanup()
        self.assertEqual(source.read_bytes(), b'keep')
        receipt = json.loads(fixture.receipt.read_text(encoding='utf-8'))
        self.assertEqual(receipt['status'], 'RETAINED_INSPECTION_INCOMPLETE')
        self.assertFalse(receipt['deletion_performed'])

    def test_absence_fault_retains_exact_owned_entry_and_rejects_unowned_path(self):
        with FixtureDirectory() as folder:
            original = Path(folder) / 'source.bin'
            original.write_bytes(b'fault control retained')
            identity = original.stat().st_dev, original.stat().st_ino
            retained = retain_fixture_entry(original)
            self.assertFalse(original.exists())
            self.assertEqual(retained.read_bytes(), b'fault control retained')
            self.assertEqual((retained.stat().st_dev, retained.stat().st_ino), identity)
            self.assertTrue((retained.parent / 'retention.private.json').is_file())
        with self.assertRaisesRegex(ValueError, 'freshly owned fixture'):
            retain_fixture_entry(Path(__file__))
