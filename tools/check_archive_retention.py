"""Read-only CI scope checks; never delete, archive or execute legacy fixtures."""
import argparse
import ast
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
FOCUSED = (
    'tests.test_collector_fixture_retention',
    'tests.test_collector_narrator_recovery_integration',
    'tests.test_collector_voxcpm2_retention',
    'tests.test_collector_editor_short',
    'tests.test_collector_archive_policy',
    'tests.test_collector_controller_data_plan',
    'tests.test_collector_narrator_recovery_probe.ProbeContractTests',
    'tests.test_collector_narrator_recovery_ancestors.RecoveryInspectorBytesTests',
)
# These exact source objects passed build/dashboard +190 checks in run43763988119.
WORKER_SCOPE = {
    'collector/windows/Collector': 'a6c8be021c2c221cc12dd3209062be6cefaaf5f6',
    'collector/windows/Dashboard': '495cab94dd974e3d8e88e82108dbb3d861918dd0',
    'global.json': '1c89f53a19ec8346f9c91d409debb99bea5ff3e3',
}


def destructive_sites(source):
    """Conservative source preflight, not a claim that arbitrary imports are safe."""
    tree = ast.parse(source)
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = ast.unparse(node.func)
        if (name in {'tempfile.TemporaryDirectory', 'TemporaryDirectory',
                     'tempfile.TemporaryFile', 'TemporaryFile',
                     'tempfile.NamedTemporaryFile', 'NamedTemporaryFile',
                     'shutil.rmtree', 'os.remove', 'os.rmdir'}
                or name.endswith('.unlink')):
            findings.append({'line': node.lineno, 'operation': name})
    for number, line in enumerate(source.splitlines(), 1):
        if (re.match(r'^\s*Remove-Item\b', line, re.I)
                or re.match(r'^\s*\[(?:System\.)?IO\.(?:File|Directory)\]::Delete\s*\(', line)):
            findings.append({'line': number, 'operation': 'PowerShell artifact deletion'})
    return findings


def selected_source(source, class_name=None):
    if class_name is None:
        return source
    tree = ast.parse(source)
    matches = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name]
    if len(matches) != 1:
        raise ValueError('Selected test class is missing or ambiguous')
    return ast.get_source_segment(source, matches[0])


def test_scope(focused):
    entries = []
    if focused:
        for selector in FOCUSED:
            parts = selector.split('.')
            entries.append((ROOT / parts[0] / (parts[1] + '.py'), parts[2] if len(parts) == 3 else None))
        entries.append((ROOT / 'tests/fixture_retention.py', None))
    else:
        entries = [(path, None) for path in sorted((ROOT / 'tests').glob('test_*.py'))]
    findings = []
    for path, class_name in entries:
        relative = path.relative_to(ROOT).as_posix()
        try:
            if path.is_symlink() or path.stat().st_size > 1048576:
                raise ValueError('Unreviewed source path')
            source = selected_source(path.read_text(encoding='utf-8-sig'), class_name)
            findings.extend({'file': relative, **item} for item in destructive_sites(source))
        except (OSError, ValueError, SyntaxError):
            findings.append({'file': relative, 'operation': 'source inspection unavailable'})
    return {
        'status': ('BLOCKED_RETENTION_PREFLIGHT' if findings else 'PASS_READ_ONLY_SOURCE_PREFLIGHT'),
        'scope': 'focused-retention-safe' if focused else 'legacy-full-regression',
        'source_count': len(entries), 'findings': findings,
        'tests_executed': False, 'archive_performed': False, 'deletion_performed': False,
        'limitation': 'Static preflight; independent review must cover imported fixture helpers.',
    }


def worker_scope():
    paths = list(WORKER_SCOPE)
    try:
        changed = subprocess.run(['git', 'status', '--porcelain=v1', '--', *paths], cwd=ROOT,
                                 check=True, capture_output=True, text=True, timeout=10).stdout
        observed = {}
        for path in paths:
            result = subprocess.run(['git', 'ls-tree', 'HEAD', '--', path], cwd=ROOT,
                                    check=True, capture_output=True, text=True, timeout=10).stdout.split()
            if (len(result) != 4 or result[1] not in ('tree', 'blob') or result[3] != path
                    or not re.fullmatch('[a-f0-9]{40}', result[2])):
                raise ValueError('Worker source object unavailable')
            observed[path] = result[2]
    except (OSError, ValueError, subprocess.SubprocessError):
        return {'status': 'BLOCKED_WORKER_PROVENANCE_UNAVAILABLE', 'new_checks_run': False}
    matched = not changed and observed == WORKER_SCOPE
    return {
        'status': 'REUSED_WORKER_EVIDENCE_ONLY' if matched else 'BLOCKED_WORKER_CHANGED_REQUIRES_FRESH_VALIDATION',
        'observed_source_objects': observed, 'accepted_source_objects': WORKER_SCOPE,
        'evidence_run': 43763988119, 'previous_checks': 190, 'new_checks_run': False,
        'reason': 'Unchanged worker sources reuse accepted evidence; changed sources require new build/self-tests.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', required=True, choices=('legacy-tests', 'focused', 'worker'))
    args = parser.parse_args()
    result = worker_scope() if args.scope == 'worker' else test_scope(args.scope == 'focused')
    print(json.dumps(result, sort_keys=True))
    return 1 if result['status'].startswith('BLOCKED') else 0


if __name__ == '__main__':
    raise SystemExit(main())
