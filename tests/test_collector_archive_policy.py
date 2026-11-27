"""Read-only archive policy and CI checks; no temporary file teardown."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools import check_archive_retention as check


class ArchivePolicyTests(unittest.TestCase):
    def test_readonly_source_preflight_rejects_destructive_fixture_teardown(self):
        for source in (
            'with tempfile.TemporaryDirectory() as folder:\n    pass',
            "Path('owned-result').unlink()",
            "shutil.rmtree('owned-fixture')",
            "script = '''\nRemove-Item -LiteralPath $folder -Recurse -Force\n'''",
            "script = '''\n[IO.File]::Delete($target)\n'''",
        ):
            with self.subTest(source=source):
                self.assertTrue(check.destructive_sites(source))
        self.assertEqual(check.destructive_sites('fixture = FixtureDirectory()\nfixture.cleanup()'), [])

    def test_selected_contract_class_does_not_execute_destructive_neighbor(self):
        source = "class Safe:\n    def test_read(self): pass\nclass Legacy:\n    def test_old(self): Path('x').unlink()\n"
        self.assertEqual(check.destructive_sites(check.selected_source(source, 'Safe')), [])
        self.assertTrue(check.destructive_sites(source))
        with self.assertRaises(ValueError):
            check.selected_source(source, 'Missing')

    def test_owner_archive_policy_and_root_ignore_are_present(self):
        root = Path(__file__).resolve().parents[1]
        policy = (root / 'AGENTS.md').read_text(encoding='utf-8-sig')
        for expected in ('Project Archive and Retention Policy',
                         'C:/Admin/Projects/KnowledgeNetwork/old/',
                         'C:/Admin/Projects/KnowledgeNetwork-Private/old/',
                         'D:/projects/knowledgenetwork/old/',
                         'A previously rejected deletion does not authorize an equivalent move'):
            self.assertIn(expected, policy)
        self.assertIn('/old/', (root / '.gitignore').read_text().splitlines())

    def test_installer_fresh_output_guard_precedes_any_build(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'collector/windows/Build-Installer.ps1').read_text(encoding='utf-8-sig')
        guard = source.index('if (Test-Path -LiteralPath $installer)')
        error = source.index("throw 'Installer output already exists.", guard)
        build = source.index("& (Join-Path $PSScriptRoot 'Build-Release.ps1')")
        self.assertLess(guard, error)
        self.assertLess(error, build)
        self.assertNotIn('Remove-Item', source)

    def test_changed_or_dirty_worker_cannot_reuse_prior_190_checks(self):
        for dirty, changed in ((False, False), (True, False), (False, True)):
            with self.subTest(dirty=dirty, changed=changed):
                replies = [SimpleNamespace(stdout=' M worker.cs' if dirty else '')]
                for index, (path, pin) in enumerate(check.WORKER_SCOPE.items()):
                    observed = 'f' * 40 if changed and index == 0 else pin
                    kind = 'blob' if path == 'global.json' else 'tree'
                    replies.append(SimpleNamespace(stdout=f'040000 {kind} {observed}\t{path}\n'))
                with patch.object(check.subprocess, 'run', side_effect=replies):
                    report = check.worker_scope()
                self.assertFalse(report['new_checks_run'])
                self.assertEqual(report['status'] == 'REUSED_WORKER_EVIDENCE_ONLY', not dirty and not changed)
        with patch.object(check.subprocess, 'run', side_effect=OSError()):
            self.assertEqual(check.worker_scope()['status'], 'BLOCKED_WORKER_PROVENANCE_UNAVAILABLE')

    def test_full_ci_stays_gated_and_preserves_meaningful_build_and_evidence(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / '.github/workflows/ci.yml').read_text(encoding='utf-8-sig')
        self.assertLess(workflow.index('--scope legacy-tests'), workflow.index("'unittest','discover','-s','tests'"))
        self.assertIn('Full retention-safe regression', workflow)
        self.assertIn('dotnet run --project collector/windows/Collector/Collector.csproj', workflow)
        self.assertIn('retention-days: 90', workflow)
        self.assertIn('fixture-retention/*.private.json', workflow)
        self.assertIn('runner fixture bytes are ephemeral, not permanently archived', workflow)
        self.assertNotIn('continue-on-error: true', workflow)


if __name__ == '__main__':
    unittest.main()
