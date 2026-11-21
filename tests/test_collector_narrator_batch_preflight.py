"""Pinned read-only preflight and PS5 startup capture; no live host execution."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from tests.fixture_retention import FixtureDirectory

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/collector/host-tools/Inspect-KnowledgeNetworkNarratorBatchPreflight.ps1'
UPDATE=ROOT/'docs/collector/host-tools/Update-KnowledgeNetworkNarratorBatch.ps1'


def diagnostic():
    text=SOURCE.read_text(encoding='utf-8')
    source=text.split("$diagnostic=@'\n",1)[1].split("\n'@",1)[0]
    tree=ast.parse(source)
    definitions=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef))]
    ns={'__name__':'owned_preflight_fixture'}
    exec(compile(ast.Module(body=definitions,type_ignores=[]),'owned-preflight-fixture','exec'),ns)
    return ns,source


class ReadOnlyPreflightTests(unittest.TestCase):
    def test_exact_hash_and_unique_main_boundary_precede_any_execution(self):
        ns,_=diagnostic()
        raw=b"events=[]\ndef main():\n    events.append('MUTATED')\nmain()\n"
        prefix=ns['checked_prefix'](raw,hashlib.sha256(raw).hexdigest())
        result={};exec(prefix,result)
        self.assertEqual(result['events'],[]);self.assertNotIn('main',result)
        with self.assertRaisesRegex(ValueError,'hash_changed'):ns['checked_prefix'](raw,'0'*64)
        for changed in (b'events=[]\n',raw+b'def main():\n    pass\n'):
            with self.assertRaisesRegex(ValueError,'main_boundary_changed'):ns['checked_prefix'](changed,hashlib.sha256(changed).hexdigest())

    def test_only_existing_readonly_verifiers_run_and_all_mutation_openers_are_denied(self):
        _,source=diagnostic();tree=ast.parse(source)
        run=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='run_diagnostic')
        calls=[node.func for node in ast.walk(run) if isinstance(node,ast.Call)]
        invoked=[fn.slice.value for fn in calls if isinstance(fn,ast.Subscript) and isinstance(fn.value,ast.Name) and fn.value.id=='namespace' and isinstance(fn.slice,ast.Constant)]
        self.assertEqual(set(invoked),{'sha','verify_bundle','task_proof'})
        self.assertIn("namespace['ps']=diagnostic_ps",source)
        self.assertIn("namespace['sqlite3']=None",source)
        for name in ('Sqlite','prepare_fence','clear_own_fence','task_operation','parity_task','write','raw_write','retain_ps_failure','backup_locked'):
            self.assertIn(repr(name),source)
        self.assertIn("report['runtime']=",source);self.assertIn("report['identity']=identity",source)
        self.assertIn("error=str(error),winerror=getattr(error,'winerror',None)",source)
        self.assertIn("report['startup_pid_binding']={'actual_pid':task['pid'],'recorded_pid':old_ready['pid']}",source)
        self.assertIn("if task['pid']!=old_ready['pid']:raise ValueError('old_startup_pid_changed')",source)

    def test_fixed_source_capture_and_owner_guard_before_start_no_host_mutators(self):
        text=SOURCE.read_text()
        self.assertIn("$helperPin='1ec820f1123aab4d12d8719efc0a462f89e9db18e80d52b09523743542129ca6'",text)
        self.assertLess(text.index('if((Hash-Bytes $helper)'),text.index('$process.Start()'))
        self.assertLess(text.index('Recorded diagnostic owner mismatch'),text.index('$process.Start()'))
        self.assertIn("$start.Arguments='-I -S -B -'",text)
        for forbidden in ('Set-Acl','Stop-ScheduledTask','Start-ScheduledTask','Register-ScheduledTask','Start-Service','tailscale','Remove-Item','Set-ExecutionPolicy'):
            self.assertNotIn(forbidden,text)


@unittest.skipUnless(os.name=='nt' and os.environ.get('COLLECTOR_NATIVE_BATCH_PREFLIGHT')=='1','Opt-in isolated PS5 capture fixture, never host/main/database')
class NativeStartupCaptureTests(unittest.TestCase):
    def test_native_parser(self):
        code="$e=$null;$t=$null;$null=[Management.Automation.Language.Parser]::ParseFile([Console]::In.ReadToEnd(),[ref]$t,[ref]$e);if($e.Count){$e|Out-String;exit 1};'PARSE_PASS'"
        result=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',code],input=str(SOURCE),capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_real_dotnet_stdin_and_future_updater_startprocess_preserve_stderr(self):
        with FixtureDirectory(prefix='kn-preflight-capture-',trusted_execution=True) as folder:
            folder=Path(folder);helper=folder/'update-helper.py'
            helper.write_text('raise RuntimeError(chr(88)*13)\n',encoding='utf-8')
            text=SOURCE.read_text()
            block=text.split('# BEGIN CAPTURED PROCESS:',1)[1].split('# END CAPTURED PROCESS',1)[0]
            block=block[block.index('\n'):]
            write_fn=text[text.index('function Write-New'):text.index("if($env:COMPUTERNAME")]
            future=next(line for line in UPDATE.read_text().splitlines() if line.startswith('$helperProcess=Start-Process'))
            # The same reviewed process code runs only an owned synthetic raise.
            script="""$ErrorActionPreference='Stop';$r=[Console]::In.ReadToEnd()|ConvertFrom-Json
$python=$r.python;$runtime=Split-Path -Parent $python;$work=$r.folder;$stem='owned';$helperPin='synthetic';$utf8=[Text.UTF8Encoding]::new($false,$true)
$diagnostic='raise RuntimeError(chr(88)*13)'
"""+write_fn+block+'\n'+future+"\n@{future_exit=$helperProcess.ExitCode}|ConvertTo-Json -Compress"
            result=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',script],
                input=json.dumps({'python':getattr(sys,'_base_executable',sys.executable),'folder':str(folder)}),capture_output=True,text=True,timeout=20)
            (folder/'parent.stdout.private.log').write_text(result.stdout);(folder/'parent.stderr.private.log').write_text(result.stderr)
            self.assertEqual(result.returncode,0,'Captured-process fixture failed; retained private parent output')
            self.assertEqual(json.loads(result.stdout)['future_exit'],1)
            for path in (folder/'owned.stderr.private.log',folder/'owner-update.stderr.private.log'):
                self.assertIn(b'X'*13,path.read_bytes())


if __name__=='__main__':unittest.main()
