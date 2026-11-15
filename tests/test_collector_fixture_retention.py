"""Owner policy: fixture teardown preserves bytes instead of deleting them."""
import hashlib
import json
from pathlib import Path
import unittest

from tests.fixture_retention import FixtureDirectory


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
