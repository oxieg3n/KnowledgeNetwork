"""Proposed recovery integration; not installed, exposed remotely or authorized live.

The explicit entry guard prevents accidental invocation; it is not evidence of
owner permission. A reviewed owner-side caller still needs approval, the native
host facts and a hard helper-process watchdog. Existing V2 files are never run.
"""
import ast
import base64
import ctypes as c
from contextlib import ExitStack
import hashlib
from itertools import islice
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import types

from . import collector_narrator_recovery_probe as probe


ROOT = Path('C:/ProgramData/KnowledgeNetworkCollector/HostExec')
LEGACY = Path('D:/projects/knowledgenetwork/collector-narrator-v9-004/narrator-control-update-tools-v1/Stop-EmptyNarratorController.ps1')
RECEIPTS = ROOT / 'broker-recovery-v1'
LEGACY_SHA256 = '3813b6d5655d7f9fe262a90266418b11a27032fa7cdf33a79fedac5dc5e0adfb'
CONFIG_SHA256 = '2b38f28bc5772c069cf8a15c54b4f9ef3ac53b585e10ed572cdbed03f778304d'
INTENT_SHA256 = 'e0b4d95234d48b784d53379af46b82582887f9b7256cedfda45f795a32f2a1d5'
DEPLOYMENT = LEGACY.parents[1]/'narrator-control-update-v1/narrator-control-deployment.json'
DEPLOYMENT_SHA256 = 'e957fdff5af63b9ae6cfad732635221478536cebc8b787d9e80ae2fd8f0c1d2d'
SOURCE_NAMES = frozenset(('__init__.py', 'collector_narrator_pipe.py',
    'collector_narrator_control.py', 'collector_narrator_host.py',
    'collector_narration_common.py', 'collector_credentials.py'))
SQL = frozenset(('BEGIN IMMEDIATE', 'PRAGMA journal_mode',
    "SELECT name FROM sqlite_master WHERE type='table'",
    "SELECT 1 FROM sqlite_master WHERE type IN ('trigger','view') LIMIT 1",
    'PRAGMA table_info(requests)', 'PRAGMA table_info(audit)',
    'SELECT count(*) FROM requests', 'SELECT count(*) FROM audit'))


class RecoveryBlocked(RuntimeError):
    pass


def _bytes(path, limit=262144):
    path = Path(path)
    for part in (path, *path.parents):
        info = part.lstat()
        if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise RecoveryBlocked('recovery_reparse_path')
    if not path.is_file() or path.stat().st_nlink != 1:
        raise RecoveryBlocked('recovery_file_type')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise RecoveryBlocked('recovery_file_bound')
    return raw


def _load_legacy():
    raw = _bytes(LEGACY, 131072)
    if hashlib.sha256(raw).hexdigest() != LEGACY_SHA256:
        raise RecoveryBlocked('legacy_source_changed')
    text = raw.decode('utf-8', errors='strict')
    if text.count("$pythonSource = @'\n") != 1:
        raise RecoveryBlocked('legacy_source_shape')
    program = text.split("$pythonSource = @'\n", 1)[1].split("\n'@", 1)[0]
    tree = ast.parse(program)
    main = [node for node in tree.body if isinstance(node, ast.If)]
    if len(main) != 1 or ast.unparse(main[0].test) != "__name__ == '__main__'":
        raise RecoveryBlocked('legacy_main_shape')
    tree.body.remove(main[0])
    if any(not isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign,
                                 ast.ClassDef, ast.FunctionDef)) for node in tree.body):
        raise RecoveryBlocked('legacy_definition_shape')
    sqlite_imports = 0
    for node in tree.body:
        if isinstance(node, ast.Import):
            sqlite_imports += sum(alias.name == 'sqlite3' for alias in node.names)
            node.names = [alias for alias in node.names if alias.name != 'sqlite3']
    if sqlite_imports != 1:
        raise RecoveryBlocked('legacy_sqlite_import_shape')
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == 'stop_empty']
    if len(functions) != 1:
        raise RecoveryBlocked('legacy_stop_shape')

    class ReceiptRoot(ast.NodeTransformer):
        changed = 0
        def visit_Attribute(self, node):
            if (isinstance(node.value, ast.Name) and node.value.id == 'INTENT'
                    and node.attr == 'parent'):
                self.changed += 1
                return ast.copy_location(ast.Name(id='RECEIPTS', ctx=ast.Load()), node)
            return self.generic_visit(node)
    rewrite = ReceiptRoot()
    rewrite.visit(functions[0])
    if rewrite.changed != 1:
        raise RecoveryBlocked('legacy_receipt_shape')
    ast.fix_missing_locations(tree)
    namespace = {'__name__': 'collector_recovery_definitions', 'RECEIPTS': RECEIPTS}
    exec(compile(tree, '<pinned-recovery-definitions>', 'exec'), namespace)
    return namespace, raw


def _expected(value):
    if (not isinstance(value, dict) or set(value) != {'owner_sid', 'python_sha256', 'task_xml_sha256'}
            or not isinstance(value['owner_sid'], str)
            or not re.fullmatch(r'S-1-5-21-(?:\d+-){3}\d+', value['owner_sid'])
            or any(not isinstance(value[key], str) or not re.fullmatch('[a-f0-9]{64}', value[key])
                   for key in ('python_sha256', 'task_xml_sha256'))):
        raise RecoveryBlocked('recovery_expected_identity')


TRUST_SCRIPT = r'''
$ErrorActionPreference='Stop'
function Assert-NoGenericWriters([object[]]$Rules,[string[]]$Trusted){
 foreach($ace in $Rules){
  if(($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0){continue}
  if($ace.AccessControlType -eq 'Allow' -and $ace.IdentityReference.Value -notin $Trusted -and (([long]$ace.FileSystemRights -band 0x50000000) -ne 0)){throw 'generic writer'}
 }
}
try {
 $r=[Console]::In.ReadToEnd()|ConvertFrom-Json
 $ExpectedOwnerSid=[string]$r.owner_sid
 $current=[Security.Principal.WindowsIdentity]::GetCurrent()
 if($current.User.Value -cne $ExpectedOwnerSid -or $ExpectedOwnerSid -eq 'S-1-5-18' -or -not ([Security.Principal.WindowsPrincipal]::new($current)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'owner'}
 $raw=[Convert]::FromBase64String($r.source)
 $sha=[Security.Cryptography.SHA256]::Create()
 try{$hash=([BitConverter]::ToString($sha.ComputeHash($raw))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
 if($hash -cne '3813b6d5655d7f9fe262a90266418b11a27032fa7cdf33a79fedac5dc5e0adfb'){throw 'source'}
 $t=$null;$e=$null;$tree=[Management.Automation.Language.Parser]::ParseInput([Text.UTF8Encoding]::new($false,$true).GetString($raw),[ref]$t,[ref]$e)
 $fn=@($tree.FindAll({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)|Where-Object Name -ceq 'Assert-StopTrustedPath')
 if($e.Count -or $fn.Count -ne 1){throw 'shape'}
 . ([ScriptBlock]::Create($fn[0].Extent.Text))
 foreach($path in $r.paths){Assert-StopTrustedPath ([string]$path)}
 $originalTrusted=@($ExpectedOwnerSid,'S-1-5-18','S-1-5-32-544','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
 foreach($path in $r.paths){
  $node=Get-Item -LiteralPath $path -Force;$depth=0
  while($null -ne $node){
   if($depth++ -ge 32){throw 'ancestor bound'}
   $a=Get-Acl -LiteralPath $node.FullName
   Assert-NoGenericWriters @($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) $originalTrusted
   $node=if($node -is [IO.DirectoryInfo]){$node.Parent}else{$node.Directory}
  }
 }
 $administrators=@('S-1-5-18','S-1-5-32-544','S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
 foreach($path in $r.code){
  $a=Get-Acl -LiteralPath $path
  if($a.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $administrators){throw 'code owner'}
  foreach($ace in $a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
   if(($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0){continue}
   if($ace.AccessControlType -eq 'Allow' -and $ace.IdentityReference.Value -notin $administrators -and (([long]$ace.FileSystemRights -band 0x500D0156) -ne 0)){throw 'code writer'}
  }
 }
 foreach($path in $r.private){
  $a=Get-Acl -LiteralPath $path
  foreach($ace in $a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){if($ace.AccessControlType -ne 'Allow' -or $ace.IdentityReference.Value -notin @($ExpectedOwnerSid,'S-1-5-18','S-1-5-32-544')){throw 'private'}}
 }
 [Console]::Out.Write('{"ok":true}')
}catch{[Console]::Out.Write('{"ok":false}');exit 1}
'''


def _trust(legacy, source, expected, dll, inventory):
    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.GetSystemDirectoryW.argtypes = [c.c_wchar_p, c.c_uint32]
    output = c.create_unicode_buffer(32768)
    if not 0 < kernel.GetSystemDirectoryW(output, len(output)) < len(output):
        raise RecoveryBlocked('system_powershell_unverified')
    powershell = Path(output.value) / 'WindowsPowerShell/v1.0/powershell.exe'
    root = legacy['ROOT']
    paths = [root, root/'runtime', root/'runtime/youtube_ops', dll.parent, dll, legacy['PYTHON'], legacy['LAUNCHER'],
        root/'runtime-files.private.json', root/'narrator-broker.json', legacy['INTENT'],
        legacy['SPOOL'], legacy['SPOOL']/'narrator-control.sqlite', legacy['RECEIPTS']]
    paths += [root/'runtime/youtube_ops'/name for name in sorted(SOURCE_NAMES)]
    paths += [root/'runtime/python'/item['name'] for item in inventory]
    code = [path for path in paths if path not in (legacy['INTENT'], legacy['SPOOL'],
            legacy['SPOOL']/'narrator-control.sqlite', legacy['RECEIPTS'])]
    payload = {'owner_sid': expected['owner_sid'], 'source': base64.b64encode(source).decode('ascii'),
        'paths': [str(path) for path in paths],
        'code': [str(path) for path in code],
        'private': [str(legacy['SPOOL']), str(legacy['SPOOL']/'narrator-control.sqlite'), str(legacy['RECEIPTS'])]}
    try:
        result = subprocess.run([str(powershell), '-NoLogo', '-NoProfile', '-NonInteractive',
            '-Command', TRUST_SCRIPT], input=json.dumps(payload).encode('ascii'), stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=10, check=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired):
        raise RecoveryBlocked('strict_native_trust_unverified') from None
    if result.returncode or result.stdout != b'{"ok":true}':
        raise RecoveryBlocked('strict_native_trust_unverified')


def _inventory(legacy):
    raw = _bytes(legacy['INTENT'])
    if hashlib.sha256(raw).hexdigest() != INTENT_SHA256:
        raise RecoveryBlocked('prepared_intent_changed')
    intent = legacy['decode'](raw)
    records = legacy['decode'](_bytes(legacy['ROOT']/'runtime-files.private.json', 65536))
    if not isinstance(records, list) or len(records) != 37 or records != intent.get('runtime_records'):
        raise RecoveryBlocked('runtime_inventory_changed')
    seen = set()
    for item in records:
        if (not isinstance(item, dict) or set(item) != {'name', 'bytes', 'sha256'}
                or not isinstance(item['name'], str) or not re.fullmatch('[A-Za-z0-9_.-]+', item['name'])
                or item['name'].casefold() in seen or type(item['bytes']) is not int
                or item['bytes'] < 0 or not isinstance(item['sha256'], str)
                or not re.fullmatch('[a-f0-9]{64}', item['sha256'])):
            raise RecoveryBlocked('runtime_inventory_changed')
        seen.add(item['name'].casefold())
    return records


def _provenance(legacy, expected, records):
    root = legacy['ROOT']
    members = list(islice((root/'runtime/python').iterdir(), 38))
    if len(members) != 37 or {path.name for path in members} != {item['name'] for item in records}:
        raise RecoveryBlocked('runtime_directory_changed')
    raw = _bytes(root/'narrator-broker.json', 65536)
    if hashlib.sha256(raw).hexdigest() != CONFIG_SHA256:
        raise RecoveryBlocked('broker_configuration_changed')
    config = legacy['decode'](raw)
    if (config.get('owner_sid') != expected['owner_sid']
            or config.get('server_python_sha256') != expected['python_sha256']
            or not isinstance(config.get('files'), dict) or set(config['files']) != SOURCE_NAMES):
        raise RecoveryBlocked('broker_provenance_changed')
    for name, pin in config['files'].items():
        if hashlib.sha256(_bytes(root/'runtime/youtube_ops'/name)).hexdigest() != pin:
            raise RecoveryBlocked('controller_code_changed')
    if hashlib.sha256(_bytes(legacy['PYTHON'], 33554432)).hexdigest() != expected['python_sha256']:
        raise RecoveryBlocked('protected_python_changed')
    manifest = _bytes(DEPLOYMENT, 65536)
    if hashlib.sha256(manifest).hexdigest() != DEPLOYMENT_SHA256:
        raise RecoveryBlocked('deployment_manifest_changed')
    deployment = legacy['decode'](manifest)
    pin = deployment.get('launcher_sha256')
    if not isinstance(pin, str) or not re.fullmatch('[a-f0-9]{64}', pin):
        raise RecoveryBlocked('launcher_pin_missing')
    if hashlib.sha256(_bytes(legacy['LAUNCHER'])).hexdigest() != pin:
        raise RecoveryBlocked('controller_launcher_changed')
    for item in records:
        raw = _bytes(root/'runtime/python'/item['name'], 33554432)
        if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise RecoveryBlocked('runtime_file_changed')
    matches = [item for item in records if item['name'] == 'sqlite3.dll']
    if len(matches) != 1:
        raise RecoveryBlocked('sqlite_runtime_pin_missing')
    return matches[0]['sha256']


def _self_image(expected):
    if os.name != 'nt' or c.sizeof(c.c_void_p) != 8:
        raise RecoveryBlocked('native_64bit_windows_required')
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise RecoveryBlocked('protected_helper_flags_required')
    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.GetModuleFileNameW.argtypes = [c.c_void_p, c.c_wchar_p, probe.U32]
    kernel.GetModuleFileNameW.restype = probe.U32
    image = c.create_unicode_buffer(32768)
    size = kernel.GetModuleFileNameW(None, image, len(image))
    python = ROOT/'runtime/python/python.exe'
    if (not 0 < size < len(image) or Path(image.value).resolve() != python.resolve()
            or hashlib.sha256(_bytes(python, 33554432)).hexdigest() != expected['python_sha256']):
        raise RecoveryBlocked('protected_helper_python_required')


def _write_new(path, value):
    raw = json.dumps(value, separators=(',', ':')).encode('ascii')
    if len(raw) > 65536:
        raise RecoveryBlocked('recovery_receipt_bound')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _journal_header(guard):
    guard.verify()
    raw = _bytes(guard.path, 1048576)
    if len(raw) < 100 or raw[:16] != b'SQLite format 3\0' or raw[18:20] != b'\x01\x01':
        raise RecoveryBlocked('control_database_format_or_journal_uncertain')
    guard.verify()


def _sidecars(path):
    for suffix in ('-journal', '-wal', '-shm'):
        try:
            Path(str(path)+suffix).lstat()
        except FileNotFoundError:
            continue
        except OSError:
            raise RecoveryBlocked('control_database_sidecar_inspection_unverified') from None
        raise RecoveryBlocked('control_database_journal_uncertain')


class _Rows:
    def __init__(self, values):
        self.values = values
    def fetchone(self):
        return self.values[0] if self.values else None
    def fetchall(self):
        return self.values
    def __iter__(self):
        return iter(self.values)


class _SqliteLibrary:
    """Internal only: the owner/ACL/runtime preflight must precede construction."""
    def __init__(self, path, pin):
        self.guard = probe.NamespaceGuard(path)
        try:
            self.recheck(pin)
            self.dll = c.CDLL(str(path))
            signatures = {
                'sqlite3_open_v2': ([c.c_char_p, c.POINTER(c.c_void_p), c.c_int, c.c_char_p], c.c_int),
                'sqlite3_file_control': ([c.c_void_p, c.c_char_p, c.c_int, c.c_void_p], c.c_int),
                'sqlite3_db_readonly': ([c.c_void_p, c.c_char_p], c.c_int),
                'sqlite3_close_v2': ([c.c_void_p], c.c_int),
                'sqlite3_prepare_v2': ([c.c_void_p, c.c_char_p, c.c_int, c.POINTER(c.c_void_p), c.c_void_p], c.c_int),
                'sqlite3_step': ([c.c_void_p], c.c_int),
                'sqlite3_finalize': ([c.c_void_p], c.c_int),
                'sqlite3_column_count': ([c.c_void_p], c.c_int),
                'sqlite3_column_type': ([c.c_void_p, c.c_int], c.c_int),
                'sqlite3_column_int64': ([c.c_void_p, c.c_int], c.c_int64),
                'sqlite3_column_text': ([c.c_void_p, c.c_int], c.c_void_p),
                'sqlite3_column_bytes': ([c.c_void_p, c.c_int], c.c_int),
                'sqlite3_busy_timeout': ([c.c_void_p, c.c_int], c.c_int),
                'sqlite3_progress_handler': ([c.c_void_p, c.c_int, c.c_void_p, c.c_void_p], None),
                'sqlite3_get_autocommit': ([c.c_void_p], c.c_int),
                'sqlite3_limit': ([c.c_void_p, c.c_int, c.c_int], c.c_int),
            }
            for name, (arguments, result) in signatures.items():
                function = getattr(self.dll, name)
                function.argtypes, function.restype = arguments, result
            kernel = self.guard.native.k
            kernel.GetModuleFileNameW.argtypes = [c.c_void_p, c.c_wchar_p, probe.U32]
            kernel.GetModuleFileNameW.restype = probe.U32
            loaded = c.create_unicode_buffer(32768)
            size = kernel.GetModuleFileNameW(self.dll._handle, loaded, len(loaded))
            if not 0 < size < len(loaded) or Path(loaded.value).resolve() != Path(path).resolve():
                raise RecoveryBlocked('sqlite_loaded_library_changed')
            self.recheck(pin)
        except BaseException:
            self.close()
            raise
    def recheck(self, pin):
        self.guard.verify()
        if hashlib.sha256(_bytes(self.guard.path, 33554432)).hexdigest() != pin:
            raise RecoveryBlocked('sqlite_library_changed')
    def close(self):
        self.guard.close()


class _Connection:
    def __init__(self, library, guard, controller, deadline):
        self.library, self.guard, self.controller = library, guard, controller
        self.deadline, self.db = deadline, c.c_void_p()
        def progress(_):
            try:
                return int(time.monotonic() >= self.deadline)
            except BaseException:
                return 1
        self.callback = c.CFUNCTYPE(c.c_int, c.c_void_p)(progress)
        guard.verify()
        _sidecars(guard.path)
        _journal_header(guard)
        status = library.dll.sqlite3_open_v2(str(guard.path).encode('utf-8'), c.byref(self.db), 2, None)
        if status:
            self.close()
            raise RecoveryBlocked('helper_sqlite_open_failed')
        try:
            if library.dll.sqlite3_db_readonly(self.db, b'main') != 0:
                raise RecoveryBlocked('helper_sqlite_readonly')
            library.dll.sqlite3_limit(self.db, 0, 1048576)
            library.dll.sqlite3_limit(self.db, 1, 4096)
            library.dll.sqlite3_progress_handler(self.db, 1000, self.callback, None)
            if library.dll.sqlite3_busy_timeout(self.db, 2000):
                raise RecoveryBlocked('helper_sqlite_timeout_failed')
            self.verify()
        except BaseException:
            self.close()
            raise
    def verify(self):
        if not self.db:
            raise RecoveryBlocked('helper_sqlite_closed')
        self.guard.verify()
        handle = probe.HANDLE()
        if self.library.dll.sqlite3_file_control(self.db, b'main', 29, c.byref(handle)) or not handle.value:
            raise RecoveryBlocked('helper_sqlite_handle_unverified')
        actual = self.guard.native.metadata(handle)
        if (actual['attributes'] & 16 or actual['links'] != 1
                or probe.identity(actual) != probe.identity(self.guard.ledger)
                or probe.identity(actual) != probe.identity(self.controller.candidate['identity'])):
            raise RecoveryBlocked('helper_controller_ledger_mismatch')
        # Borrowed HANDLE belongs to SQLite; never CloseHandle it.
        self.controller.recheck()
    def execute(self, sql):
        if sql not in SQL:
            raise RecoveryBlocked('recovery_sql_denied')
        if time.monotonic() >= self.deadline:
            raise RecoveryBlocked('recovery_deadline')
        self.verify()
        if sql == 'BEGIN IMMEDIATE':
            _sidecars(self.guard.path)
            _journal_header(self.guard)
        values = self._query(sql)
        self.verify()
        return _Rows(values)
    def _query(self, sql):
        statement = c.c_void_p()
        raw = sql.encode('ascii')
        if self.library.dll.sqlite3_prepare_v2(self.db, raw, len(raw), c.byref(statement), None):
            if statement:
                self.library.dll.sqlite3_finalize(statement)
            raise RecoveryBlocked('recovery_sql_prepare_failed')
        values, failed = [], False
        try:
            columns = self.library.dll.sqlite3_column_count(statement)
            if not 0 <= columns <= 8:
                raise RecoveryBlocked('recovery_sql_bound')
            while True:
                status = self.library.dll.sqlite3_step(statement)
                if status == 101:
                    return values
                if status != 100:
                    raise RecoveryBlocked('recovery_sql_busy_or_failed')
                if len(values) >= 64:
                    raise RecoveryBlocked('recovery_sql_bound')
                row = []
                for index in range(columns):
                    kind = self.library.dll.sqlite3_column_type(statement, index)
                    if kind == 1:
                        row.append(self.library.dll.sqlite3_column_int64(statement, index))
                    elif kind == 5:
                        row.append(None)
                    elif kind == 3:
                        pointer = self.library.dll.sqlite3_column_text(statement, index)
                        size = self.library.dll.sqlite3_column_bytes(statement, index)
                        if not 0 <= size <= 4096 or (size and not pointer):
                            raise RecoveryBlocked('recovery_sql_bound')
                        row.append(c.string_at(pointer, size).decode('utf-8', errors='strict'))
                    else:
                        raise RecoveryBlocked('recovery_sql_type')
                values.append(tuple(row))
        except BaseException:
            failed = True
            raise
        finally:
            status = self.library.dll.sqlite3_finalize(statement)
            if status and not failed:
                raise RecoveryBlocked('recovery_sql_finalize_failed')
    def rollback(self):
        if self.db and not self.library.dll.sqlite3_get_autocommit(self.db):
            self.library.dll.sqlite3_progress_handler(self.db, 0, None, None)
            self.library.dll.sqlite3_busy_timeout(self.db, 0)
            self._query('ROLLBACK')
    def close(self):
        if self.db:
            try:
                self.rollback()
            finally:
                result = self.library.dll.sqlite3_close_v2(self.db)
                if result:
                    raise RecoveryBlocked('helper_sqlite_close_unverified')
                self.db = c.c_void_p()


def _snapshot_process(legacy, expected):
    snapshot = legacy['task_call']('query', expected)
    if (not isinstance(snapshot, dict) or set(snapshot) != {'state', 'instance_id', 'engine_pid', 'processes', 'listener_pids'}
            or snapshot['state'] != 4 or type(snapshot['state']) is not int
            or type(snapshot['engine_pid']) is not int or snapshot['engine_pid'] <= 0
            or not isinstance(snapshot['instance_id'], str) or not isinstance(snapshot['processes'], list)
            or not 1 <= len(snapshot['processes']) <= 8 or not isinstance(snapshot['listener_pids'], list)
            or any(type(item) is not int or item <= 0 for item in snapshot['listener_pids'])):
        raise RecoveryBlocked('recovery_task_unverified')
    try:
        legacy['uuid'].UUID(snapshot['instance_id'].strip('{}'))
    except ValueError:
        raise RecoveryBlocked('recovery_task_unverified') from None
    candidates = []
    for item in snapshot['processes']:
        words = legacy['argv'](item['command_line'])
        if (len(words) == 5 and Path(words[0]) == legacy['PYTHON']
                and words[1:4] == ['-I', '-S', '-B'] and Path(words[4]) == legacy['LAUNCHER']):
            candidates.append(item)
    if (len(candidates) != 1 or candidates[0].get('owner_sid') != expected['owner_sid']
            or candidates[0]['pid'] in snapshot['listener_pids']):
        raise RecoveryBlocked('recovery_controller_unverified')
    return snapshot, candidates[0]


def _run(legacy, expected, dll, dll_pin):
    """Internal composition; production caller must complete native trust first."""
    _expected(expected)
    receipts = Path(legacy['RECEIPTS'])
    if not receipts.is_dir() or any(receipts.iterdir()):
        raise RecoveryBlocked('recovery_receipts_not_empty')
    markers = ('empty-stop-intent.private.json', 'empty-stop-result.private.json',
               'empty-stop.private.json', 'start-intent.private.json', 'update-completed.private.json')
    if any((legacy['INTENT'].parent/name).exists() for name in markers):
        raise RecoveryBlocked('previous_recovery_outcome_requires_reconciliation')
    dbpath = legacy['SPOOL']/'narrator-control.sqlite'
    _sidecars(dbpath)
    # Validate the retained prepared intent before even querying the fixed task.
    intent = legacy['decode'](legacy['read'](legacy['INTENT']))
    if (intent.get('schema_version') != 1 or type(intent.get('schema_version')) is not int
            or intent.get('status') != 'FULL_REPAIR_PREPARED' or intent.get('task_state') != 'Running'
            or intent.get('owner_sid') != expected['owner_sid'] or intent.get('publication_paused') is not True
            or not isinstance(intent.get('task_xml'), str)
            or legacy['sha'](intent['task_xml'].encode()) != expected['task_xml_sha256']):
        raise RecoveryBlocked('prepared_update_intent_unverified')
    _write_new(receipts/'recovery-claim.private.json', {'status': 'RECOVERY_CLAIMED',
        'intent_sha256': legacy['sha'](legacy['read'](legacy['INTENT'])), 'stop_attempts_maximum': 1,
        'publication_paused': True})
    try:
        result = _compose(legacy, expected, dll, dll_pin)
    except BaseException as error:
        try:
            code = str(error) if isinstance(error, (RecoveryBlocked, probe.ProbeBlocked, legacy['Blocked'])) else ''
            if not re.fullmatch('[a-z_]{1,80}', code):
                code = 'recovery_outcome_unverified'
            _write_new(receipts/'recovery-result.private.json', {'status': 'BLOCKED',
                'stage': legacy['STAGE'], 'error': code, 'error_class': type(error).__name__,
                'stop_intent_present': (receipts/'empty-stop-intent.private.json').exists(),
                'publication_paused': True})
        except Exception:
            raise RecoveryBlocked('recovery_result_unavailable') from error
        raise
    _write_new(receipts/'recovery-result.private.json', result)
    return result


def _compose(legacy, expected, dll, dll_pin):
    dbpath = legacy['SPOOL']/'narrator-control.sqlite'
    with ExitStack() as stack:
        legacy['STAGE'] = 'namespace_guard'
        guard = stack.enter_context(probe.NamespaceGuard(dbpath))
        legacy['STAGE'] = 'controller_preflight'
        snapshot, process = _snapshot_process(legacy, expected)
        original_held, original_call = legacy['HeldProcess'], legacy['task_call']
        held = original_held(process, expected)
        stack.callback(held.close)
        legacy['associate'](held, process, snapshot)
        native = guard.native
        legacy['STAGE'] = 'controller_ledger_binding'
        native.k.OpenProcess.argtypes = [probe.U32, c.c_int, probe.U32]
        native.k.OpenProcess.restype = probe.HANDLE
        process_handle = native.k.OpenProcess(0x100440, False, held.pid)
        if not process_handle:
            raise RecoveryBlocked('controller_snapshot_access_unverified')
        stack.callback(native.k.CloseHandle, process_handle)
        controller = stack.enter_context(probe.LedgerBinding(process_handle, held.created, guard))
        legacy['STAGE'] = 'sqlite_library_binding'
        library = _SqliteLibrary(dll, dll_pin)
        stack.callback(library.close)
        connection = None

        def connect(database, **kwargs):
            nonlocal connection
            # Legacy spelling is checked before opening the fixed already-guarded path.
            if (database != dbpath.as_uri()+'?mode=rw' or kwargs != {'uri': True, 'timeout': 2}
                    or connection is not None):
                raise RecoveryBlocked('recovery_sql_open_contract')
            legacy['STAGE'] = 'helper_connection_binding'
            connection = _Connection(library, guard, controller, time.monotonic()+20)
            return connection

        class SameController(original_held):
            def __init__(self, item, target):
                super().__init__(item, target)
                if self.pid != held.pid or self.created != held.created:
                    self.close()
                    raise RecoveryBlocked('controller_instance_changed')

        def checked_call(action, *args, **kwargs):
            if connection is None:
                raise RecoveryBlocked('recovery_connection_not_bound')
            if action in ('query', 'stop'):
                if time.monotonic() >= connection.deadline:
                    raise RecoveryBlocked('recovery_deadline')
                connection.verify()
                controller.recheck()
            if action == 'stop':
                library.recheck(dll_pin)
                if kwargs.get('instance') != snapshot['instance_id'] or kwargs.get('engine') != snapshot['engine_pid']:
                    raise RecoveryBlocked('task_instance_changed')
            value = original_call(action, *args, **kwargs)
            if action == 'query' and (value.get('instance_id') != snapshot['instance_id']
                                      or value.get('engine_pid') != snapshot['engine_pid']):
                raise RecoveryBlocked('task_instance_changed')
            return value

        legacy.update(sqlite3=types.SimpleNamespace(connect=connect), HeldProcess=SameController,
                      task_call=checked_call)
        try:
            result = legacy['stop_empty'](expected)
            return {**result, 'ledger_identity': probe.identity(guard.ledger),
                'controller_pid': held.pid, 'controller_creation_filetime': held.created,
                'task_instance': snapshot['instance_id'],
                'partial_handle_coverage': bool(controller.candidate['unsupported_handles']
                    or controller.candidate['unknown_file_handles']),
                'helper_connection_native_identity_verified': True, 'publication_paused': True}
        finally:
            legacy.update(HeldProcess=original_held, task_call=original_call)
            if connection is not None:
                connection.close()


def recover_empty_controller(expected, *, operator_approved=False):
    """Intentionally undeployable; a Boolean is not permission or code provenance."""
    if operator_approved is not True:
        raise RecoveryBlocked('live_recovery_not_authorized')
    # shortcut: remain disabled until an independently pinned protected caller,
    # recovery/probe module manifest and hard watchdog are reviewed and installed.
    raise RecoveryBlocked('reviewed_recovery_deployment_unavailable')


def _verified_caller_recovery(expected):
    """Proposed private body; not reachable from the deliberately held live entry."""
    _expected(expected)
    _self_image(expected)
    legacy, source = _load_legacy()
    dll = legacy['ROOT']/'runtime/python/sqlite3.dll'
    inventory = _inventory(legacy)
    _trust(legacy, source, expected, dll, inventory)
    pin = _provenance(legacy, expected, inventory)
    return _run(legacy, expected, dll, pin)
