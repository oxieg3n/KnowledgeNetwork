"""Synthetic filesystem tests; no installed host model is inspected."""
import contextlib
import io
import hashlib
import json
import importlib.util
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('installed_probe', Path(__file__).resolve().parents[1] /
    'docs/collector/host-tools/inspect_installed_voxcpm2.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class InventoryBoundsTests(unittest.TestCase):
    def shared_fixture(self, root, content=b'installed synthetic weights'):
        repo = root / 'models--openbmb--VoxCPM2'
        snapshot = repo / 'snapshots' / '7936080b41163874f38610f46f438e2c0757f9fd'
        snapshot.mkdir(parents=True)
        checksum = hashlib.sha256(content).hexdigest()
        blob = root / 'blobs' / checksum[:2] / checksum
        blob.parent.mkdir(parents=True)
        blob.write_bytes(content)
        return repo, snapshot, blob, checksum

    def test_shared_blobs_record_logical_and_resolved_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, snapshot, blob, checksum = self.shared_fixture(Path(tmp))
            (snapshot / 'model.safetensors').symlink_to(blob)
            if os.name == 'nt':
                self.assertTrue(os.readlink(snapshot / 'model.safetensors').startswith('\\\\?\\'))
            (snapshot / 'audiovae.pth').symlink_to(Path('../../../blobs') / checksum[:2] / checksum)
            rows = probe.catalog(snapshot, repo)
            self.assertEqual({Path(row['logical_path']).name for row in rows},
                             {'model.safetensors', 'audiovae.pth'})
            for row in rows:
                self.assertEqual(row['resolved_path'], str(blob))
                self.assertEqual(row['sha256'], checksum)
                self.assertEqual(row['bytes'], blob.stat().st_size)

    def test_existing_repository_blob_link_still_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'repo'
            snapshot = repo / 'snapshots' / ('a' * 40)
            snapshot.mkdir(parents=True)
            blob = repo / 'blobs' / 'existing-weight'
            blob.parent.mkdir()
            blob.write_bytes(b'old repository layout')
            (snapshot / 'weight').symlink_to(blob)
            self.assertEqual(probe.catalog(snapshot, repo)[0]['sha256'], probe.sha(blob))

    def test_external_and_shared_lookalike_paths_denied_before_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, snapshot, blob, checksum = self.shared_fixture(root)
            for target in (root / 'outside' / checksum[:2] / checksum,
                           root / 'blobs-extra' / checksum[:2] / checksum,
                           root / 'other-hub' / 'blobs' / checksum[:2] / checksum):
                with self.subTest(target=target):
                    target.parent.mkdir(parents=True)
                    target.write_bytes(b'secret')
                    link = snapshot / 'weight'
                    link.symlink_to(target)
                    with patch.object(probe, 'sha') as hashed:
                        with self.assertRaisesRegex(ValueError, 'model_file_escape'):
                            probe.catalog(snapshot, repo)
                        hashed.assert_not_called()
                    link.unlink()

    def test_shared_blob_name_and_prefix_must_match_exact_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, snapshot, blob, checksum = self.shared_fixture(Path(tmp))
            for parts in [('00' if checksum[:2] != '00' else 'ff', checksum),
                          (checksum[:2], checksum + '.bin'), (checksum[:2], checksum[:-1]),
                          ('xyz', checksum), (checksum[:2].upper(), checksum.upper()),
                          (checksum[:2], 'nested', checksum), (checksum,)]:
                with self.subTest(parts=parts):
                    link = snapshot / 'weight'
                    link.symlink_to(Path(tmp).joinpath('blobs', *parts))
                    with patch.object(probe, 'sha') as hashed:
                        with self.assertRaisesRegex(ValueError, 'invalid_shared_blob_path'):
                            probe.catalog(snapshot, repo)
                        hashed.assert_not_called()
                    link.unlink()

    def test_cache_object_id_is_not_assumed_to_be_content_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, snapshot, blob, _ = self.shared_fixture(Path(tmp))
            (snapshot / 'weight').symlink_to(blob)
            blob.write_bytes(b'cache object IDs can use a different digest')
            result = probe.catalog(snapshot, repo)
            self.assertEqual(result[0]['sha256'], hashlib.sha256(blob.read_bytes()).hexdigest())
            self.assertNotEqual(result[0]['sha256'], blob.name)

    def test_exact_hf_repository_to_shared_blob_chain_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, snapshot, blob, checksum = self.shared_fixture(Path(tmp))
            intermediate = repo / 'blobs' / ('9' * 64)
            intermediate.parent.mkdir()
            intermediate.symlink_to(Path('../../blobs') / checksum[:2] / checksum)
            (snapshot / 'model.safetensors').symlink_to(Path('../../blobs') / intermediate.name)
            row = probe.catalog(snapshot, repo)[0]
            self.assertEqual(row['resolved_path'], str(blob))
            self.assertEqual(row['sha256'], checksum)

    def test_repository_chain_cannot_redirect_to_arbitrary_or_extra_links(self):
        for destination in ('external', 'repository', 'extra-shared-link'):
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo, snapshot, blob, _ = self.shared_fixture(root)
                other = root / 'external' if destination == 'external' else repo / 'other'
                other.write_bytes(b'arbitrary data')
                if destination == 'extra-shared-link':
                    blob.unlink()
                    blob.symlink_to(other)
                    other = blob
                intermediate = repo / 'blobs' / ('9' * 64)
                intermediate.parent.mkdir()
                intermediate.symlink_to(other)
                (snapshot / 'weight').symlink_to(intermediate)
                with patch.object(probe, 'sha') as hashed:
                    with self.assertRaises(ValueError):
                        probe.catalog(snapshot, repo)
                    hashed.assert_not_called()

    def test_repository_blob_link_change_during_hash_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, snapshot, blob, _ = self.shared_fixture(Path(tmp))
            intermediate = repo / 'blobs' / ('9' * 64)
            intermediate.parent.mkdir()
            intermediate.symlink_to(blob)
            (snapshot / 'weight').symlink_to(intermediate)
            original_sha = probe.sha
            def checksum(path):
                result = original_sha(path)
                intermediate.unlink()
                intermediate.symlink_to(blob)
                return result
            with patch.object(probe, 'sha', side_effect=checksum):
                with self.assertRaisesRegex(ValueError, 'model_changed_during_inspection'):
                    probe.catalog(snapshot, repo)

    def test_broken_shared_blob_and_redirected_blob_file_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, snapshot, blob, _ = self.shared_fixture(Path(tmp))
            (snapshot / 'weight').symlink_to(blob)
            blob.unlink()
            with self.assertRaises(FileNotFoundError):
                probe.catalog(snapshot, repo)
            other = repo / 'other-weight'
            other.write_bytes(b'arbitrary data')
            blob.symlink_to(other)
            with patch.object(probe, 'sha') as hashed:
                with self.assertRaisesRegex(ValueError, 'unexpected_model_link'):
                    probe.catalog(snapshot, repo)
                hashed.assert_not_called()

    def test_device_and_unc_link_targets_denied_without_target_io(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, snapshot, blob, _ = self.shared_fixture(Path(tmp))
            link = snapshot / 'weight'
            link.symlink_to(blob)
            for target in (r'\\\\?\\UNC\server\share\blob', r'\\\\.\C:\blob',
                           r'\\server\share\blob', str(blob.parent / '..' / '..' / 'arbitrary')):
                with self.subTest(target=target), patch.object(probe.os, 'readlink', return_value=target), \
                     patch.object(probe, 'sha') as hashed:
                    with self.assertRaisesRegex(ValueError, 'model_file_escape|invalid_shared_blob_path'):
                        probe.catalog(snapshot, repo)
                    hashed.assert_not_called()

    def test_broken_reference_and_file_link_chain_denied_before_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, snapshot, blob, _ = self.shared_fixture(Path(tmp))
            for target in (repo / 'missing', repo / 'indirect'):
                with self.subTest(target=target):
                    if target.name == 'indirect':
                        target.symlink_to(blob)
                    link = snapshot / 'weight'
                    link.symlink_to(target)
                    with patch.object(probe, 'sha') as hashed:
                        with self.assertRaises((FileNotFoundError, ValueError)):
                            probe.catalog(snapshot, repo)
                        hashed.assert_not_called()
                    link.unlink()

    def test_linked_shared_directory_and_snapshot_directory_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, snapshot, blob, checksum = self.shared_fixture(root)
            (snapshot / 'weight').symlink_to(blob)
            shard = blob.parent
            actual = root / 'actual-shard'
            shard.rename(actual)
            shard.symlink_to(actual, target_is_directory=True)
            with patch.object(probe, 'sha') as hashed:
                with self.assertRaisesRegex(ValueError, 'unexpected_model_link'):
                    probe.catalog(snapshot, repo)
                hashed.assert_not_called()
            (snapshot / 'weight').unlink()
            (snapshot / 'nested').symlink_to(actual, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'linked_directory_denied'):
                probe.catalog(snapshot, repo)

    def test_shared_store_root_link_and_snapshot_root_link_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, snapshot, blob, _ = self.shared_fixture(root)
            (snapshot / 'weight').symlink_to(blob)
            shared = root / 'blobs'
            actual = root / 'actual-store'
            shared.rename(actual)
            shared.symlink_to(actual, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'unexpected_model_link'):
                probe.catalog(snapshot, repo)
            alias = repo / 'snapshot-alias'
            alias.symlink_to(snapshot, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'unexpected_model_link'):
                probe.catalog(alias, repo)

    def test_changing_contents_or_reference_denied(self):
        for change in ('contents', 'reference', 'replacement'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                repo, snapshot, blob, _ = self.shared_fixture(Path(tmp))
                link = snapshot / 'weight'
                link.symlink_to(blob)
                original_sha = probe.sha
                def mutate(path):
                    checksum = original_sha(path)
                    if change == 'contents':
                        path.write_bytes(b'changed during hash')
                    elif change == 'reference':
                        other = repo / 'other-weight'
                        other.write_bytes(b'other')
                        link.unlink()
                        link.symlink_to(other)
                    else:
                        replacement = path.with_suffix('.replacement')
                        replacement.write_bytes(path.read_bytes())
                        replacement.replace(path)
                    return checksum
                with patch.object(probe, 'sha', side_effect=mutate):
                    with self.assertRaisesRegex(ValueError, 'model_changed_during_inspection'):
                        probe.catalog(snapshot, repo)

    def test_shared_blobs_preserve_byte_limit_before_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, snapshot, blob, _ = self.shared_fixture(Path(tmp))
            (snapshot / 'weight').symlink_to(blob)
            with patch.object(probe, 'MAX_MODEL_BYTES', 1), patch.object(probe, 'sha') as hashed:
                with self.assertRaisesRegex(ValueError, 'model_byte_limit'):
                    probe.catalog(snapshot, repo)
                hashed.assert_not_called()

    def test_unreadable_directory_cannot_produce_partial_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, snapshot, _, _ = self.shared_fixture(Path(tmp))
            (snapshot / 'config.json').write_text('{}')
            denied = snapshot / 'unreadable'
            denied.mkdir()
            original_scandir = probe.os.scandir
            def scandir(path):
                if Path(path) == denied:
                    raise PermissionError('synthetic unreadable model directory')
                return original_scandir(path)
            with patch.object(probe.os, 'scandir', side_effect=scandir):
                with self.assertRaises(PermissionError):
                    probe.catalog(snapshot, repo)

    def test_inspect_retains_exact_revision_and_detects_ref_changes(self):
        for changed in (False, True):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                repo, snapshot, blob, _ = self.shared_fixture(root)
                (snapshot / 'model.safetensors').symlink_to(blob)
                ref = repo / 'refs/main'
                ref.parent.mkdir()
                ref.write_text(snapshot.name, encoding='ascii')
                original_sha = probe.sha
                def checksum(path):
                    result = original_sha(path)
                    if changed and path == blob:
                        ref.write_text('f' * 40, encoding='ascii')
                    return result
                distribution = types.SimpleNamespace(files=[], version='2.0.3', entry_points=[])
                with patch.dict(probe.sys.modules, {'huggingface_hub.constants':
                        types.SimpleNamespace(HF_HUB_CACHE=str(root))}), \
                     patch.object(probe.importlib.metadata, 'distribution', return_value=distribution), \
                     patch.object(probe, 'sha', side_effect=checksum):
                    if changed:
                        with self.assertRaisesRegex(ValueError, 'revision_changed_during_inspection'):
                            probe.inspect()
                    else:
                        result = probe.inspect()
                        self.assertEqual(result['revision'], snapshot.name)
                        self.assertEqual(result['snapshot'], str(snapshot))
                        self.assertEqual(result['model_files'][0]['resolved_path'], str(blob))
                        self.assertFalse(result['rights_verified'])
                        self.assertFalse(result['model_loaded'])

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

    @unittest.skipUnless(os.name == 'nt', 'Windows-only report ACL orchestration')
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
                     patch.dict(probe.sys.modules, {'huggingface_hub.constants': types.SimpleNamespace(HF_HUB_CACHE='PRIVATE_CACHE_PATH')}), \
                     patch.object(probe.importlib.metadata, 'version', return_value='2.0.3-private-test'), \
                     contextlib.redirect_stdout(output):
                    self.assertEqual(probe.main(), 1)
                self.assertNotIn('PRIVATE_SECRET', output.getvalue())
                self.assertNotIn('PRIVATE_CACHE_PATH', output.getvalue())
                self.assertNotIn('2.0.3-private-test', output.getvalue())
                self.assertNotIn(tmp, output.getvalue())
                reports = list(Path(tmp).glob('*/failure.json'))
                self.assertEqual(len(reports), int(acl_ok))
                if reports:
                    report = json.loads(reports[0].read_text())
                    self.assertEqual(report['stage'], 'inspection')
                    self.assertEqual(report['exception_type'], 'RuntimeError')
                    self.assertEqual(report['private_context']['hf_hub_cache'], 'PRIVATE_CACHE_PATH')
                    self.assertEqual(report['private_context']['voxcpm_version'], '2.0.3-private-test')
                    self.assertIn('python_executable', report['private_context'])
                    self.assertNotIn('PRIVATE_SECRET', reports[0].read_text())

    def test_private_folder_changes_only_dacl_and_preserves_owner(self):
        self.assertIn('Get-Acl -LiteralPath $p', probe.PRIVATE_ACL)
        self.assertIn('RemoveAccessRuleSpecific', probe.PRIVATE_ACL)
        self.assertIn('SetAccessRuleProtection($true, $false)', probe.PRIVATE_ACL)
        self.assertNotIn('SetOwner', probe.PRIVATE_ACL)

    def test_rejected_component_diagnostics_are_allowlisted_private_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'private-target'
            target.mkdir()
            link = root / 'private-link'
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(probe.ModelPathError) as raised:
                probe.plain_path(link, root)
            details = probe.failure_context(raised.exception)['rejected_model_path']
            self.assertEqual(details['component'], str(link))
            self.assertIn('private-target', details['link_target'])
            self.assertEqual(set(details), {'component', 'mode', 'file_attributes', 'reparse_tag', 'link_target'})

    def test_file_count_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for number in range(257):
                (repo / str(number)).touch()
            with self.assertRaisesRegex(ValueError, 'model_inventory_limit'):
                probe.catalog(repo, repo)


if __name__ == '__main__':
    unittest.main()
