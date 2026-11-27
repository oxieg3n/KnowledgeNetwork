"""Owner-run read-only installed VoxCPM2 inventory; never imports inference code."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from youtube_ops.collector_narrator_host import _system_powershell, verify_spool_acl

SITE_PACKAGES = Path(r'D:\tools\audio\voicestudio\data\engines\voxcpm2\voxcpm2\.venv\Lib\site-packages')
MAX_MODEL_BYTES = 32 * 1024 ** 3
STAGE = 'startup'

PRIVATE_ACL = r'''
$ErrorActionPreference = 'Stop'
try {
 $p = ([Console]::In.ReadToEnd() | ConvertFrom-Json).path
 $user = [Security.Principal.WindowsIdentity]::GetCurrent().User
 $acl = Get-Acl -LiteralPath $p
 $acl.SetAccessRuleProtection($true, $false)
 foreach ($rule in @($acl.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier]))) {
  $acl.RemoveAccessRuleSpecific($rule)
 }
 foreach ($sid in @($user.Value,'S-1-5-18','S-1-5-32-544')) {
  $rule = [Security.AccessControl.FileSystemAccessRule]::new(
   [Security.Principal.SecurityIdentifier]::new($sid), 'FullControl',
   'ContainerInherit,ObjectInherit', 'None', 'Allow')
  $acl.AddAccessRule($rule)
 }
 Set-Acl -LiteralPath $p -AclObject $acl
 exit 0
} catch { exit 1 }
'''


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class ModelPathError(ValueError):
    def __init__(self, path, info):
        super().__init__('unexpected_model_link')
        self.details = {'component': str(path)[:32768], 'mode': info.st_mode,
                        'file_attributes': getattr(info, 'st_file_attributes', 0),
                        'reparse_tag': getattr(info, 'st_reparse_tag', 0)}
        try:
            self.details['link_target'] = os.readlink(path)[:32768]
        except OSError:
            self.details['link_target'] = None


def plain_path(path, root):
    """Reject redirected components below the canonical cache trust root."""
    item = root
    for part in ('.', *path.relative_to(root).parts):
        item = item / part
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ModelPathError(item, info)


def file_identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def file_link_target(logical):
    info = logical.lstat()
    if stat.S_ISLNK(info.st_mode):
        if getattr(info, 'st_reparse_tag', 0xA000000C) != 0xA000000C:
            raise ModelPathError(logical, info)
        link = os.readlink(logical)
        # Windows readlink returns extended drive names; do not accept device/UNC aliases.
        if link.startswith('\\\\?\\'):
            if not re.match(r'^[A-Za-z]:\\', link[4:]):
                raise ValueError('model_file_escape')
            link = link[4:]
        if link.startswith(('\\\\', '//')):
            raise ValueError('model_file_escape')
        target = Path(os.path.abspath(logical.parent / link))
        return target, ((str(logical), file_identity(info), link),)
    else:
        if getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ModelPathError(logical, info)
        return logical, ()


def model_target(logical, repository, cache):
    target, links = file_link_target(logical)
    shared = cache / 'blobs'
    if not (target.is_relative_to(repository) or target.is_relative_to(shared)):
        raise ValueError('model_file_escape')
    # HF also links snapshot -> repository blob -> shared blob. No other chain is allowed.
    if (links and target.parent == repository / 'blobs' and
            re.fullmatch('[a-f0-9]{64}', target.name)):
        plain_path(target.parent, cache)
        if target.is_symlink():
            target, second_link = file_link_target(target)
            links += second_link
            if not target.is_relative_to(shared):
                raise ValueError('model_file_escape')
    if not target.is_relative_to(repository):
        if not target.is_relative_to(shared):
            raise ValueError('model_file_escape')
        parts = target.relative_to(shared).parts
        if (len(parts) != 2 or not re.fullmatch('[a-f0-9]{2}', parts[0]) or
                not re.fullmatch('[a-f0-9]{64}', parts[1]) or parts[0] != parts[1][:2]):
            raise ValueError('invalid_shared_blob_path')
    plain_path(target, cache)
    if (target.resolve(strict=True) != target or logical.resolve(strict=True) != target or
            not stat.S_ISREG(target.stat().st_mode)):
        raise ValueError('model_file_escape')
    return target, links


def catalog(snapshot, repository):
    """Bound read-only inventory of repository files and canonical HF shared blobs."""
    cache = repository.parent.resolve(strict=True)
    repository = cache / repository.name
    snapshot = Path(os.path.abspath(snapshot))
    if not snapshot.is_relative_to(repository):
        raise ValueError('snapshot_escape')
    plain_path(snapshot, cache)
    files, visited, total_bytes = [], 0, 0
    def walk_error(error):
        raise error
    for directory, dirs, names in os.walk(snapshot, followlinks=False, onerror=walk_error):
        visited += len(dirs) + len(names)
        if visited > 256:
            raise ValueError('model_inventory_limit')
        for name in dirs:
            item = Path(directory) / name
            if item.is_symlink() or getattr(item.lstat(), 'st_file_attributes', 0) & 0x400:
                raise ValueError('linked_directory_denied')
        for name in sorted(names):
            logical = Path(directory) / name
            link_before = file_identity(logical.lstat())
            target, links = model_target(logical, repository, cache)
            before = target.stat()
            total_bytes += before.st_size
            if before.st_size > MAX_MODEL_BYTES or total_bytes > MAX_MODEL_BYTES:
                raise ValueError('model_byte_limit')
            checksum = sha(target)
            after = target.stat()
            if (file_identity(before) != file_identity(after) or
                    link_before != file_identity(logical.lstat()) or
                    model_target(logical, repository, cache) != (target, links)):
                raise ValueError('model_changed_during_inspection')
            files.append({'logical_path': str(logical), 'resolved_path': str(target),
                          'bytes': after.st_size, 'sha256': checksum})
    if not files:
        raise ValueError('empty_snapshot')
    return files


def inspect():
    global STAGE
    STAGE = 'package_discovery'
    from huggingface_hub.constants import HF_HUB_CACHE
    dist = importlib.metadata.distribution('voxcpm')
    STAGE = 'model_reference'
    repository = Path(HF_HUB_CACHE) / 'models--openbmb--VoxCPM2'
    ref = repository / 'refs/main'
    if not ref.resolve(strict=True).is_relative_to(repository.resolve(strict=True)):
        raise ValueError('revision_ref_escape')
    if ref.stat().st_size > 128:
        raise ValueError('invalid_revision')
    revision = ref.read_text(encoding='ascii').strip()
    if not re.fullmatch('[a-f0-9]{40}', revision):
        raise ValueError('invalid_revision')
    snapshot = repository / 'snapshots' / revision
    STAGE = 'snapshot_catalog'
    files = catalog(snapshot, repository)
    if ref.read_text(encoding='ascii').strip() != revision:
        raise ValueError('revision_changed_during_inspection')
    STAGE = 'package_catalog'
    package = []
    for item in dist.files or []:
        name = str(item).replace('\\', '/')
        if (name.startswith('voxcpm/') and name.endswith('.py')) or (
                '.dist-info/' in name and name.rsplit('/', 1)[-1] in
                {'METADATA', 'LICENSE', 'entry_points.txt', 'WHEEL', 'INSTALLER'}):
            if len(package) >= 256:
                raise ValueError('package_inventory_limit')
            path = Path(dist.locate_file(item)).resolve(strict=True)
            if not path.is_relative_to(SITE_PACKAGES.resolve(strict=True)):
                raise ValueError('package_file_escape')
            if path.stat().st_size > 4 * 1024 * 1024:
                raise ValueError('package_source_byte_limit')
            package.append({'logical_path': name, 'resolved_path': str(path),
                            'bytes': path.stat().st_size, 'sha256': sha(path)})
    return {'schema_version': 1, 'status': 'inventory_only_owner_review_required',
            'model_loaded': False, 'network_requested': False, 'rights_verified': False,
            'python_version': sys.version.split()[0], 'python_executable': sys.executable,
            'voxcpm_version': dist.version,
            'entry_points': [{'name': e.name, 'value': e.value, 'group': e.group}
                             for e in dist.entry_points],
            'hf_hub_cache': str(HF_HUB_CACHE),
            'cache_environment': {key: os.environ.get(key) for key in
                ('HF_HOME', 'XDG_CACHE_HOME', 'HUGGINGFACE_HUB_CACHE', 'HF_HUB_CACHE')},
            'offline_flag': os.environ.get('HF_HUB_OFFLINE'),
            'revision_ref': str(ref),
            'revision': revision, 'revision_ref_sha256': sha(ref),
            'snapshot': str(snapshot), 'model_files': files, 'package_files': package,
            'cli_defaults_from_prior_source_review': {'hf_model_id': 'openbmb/VoxCPM2',
                'revision_argument': None, 'device': 'auto', 'seed': 'not_set',
                'normalize': False, 'denoise': False},
            'runtime_device': 'not_probed', 'voice_consent': 'owner_review_required'}


def failure_context(error=None):
    """Private allowlisted diagnostics; never dump environment or import inference."""
    context = {'python_executable': sys.executable[:32768],
               'python_version': sys.version.split()[0][:256]}
    constants = sys.modules.get('huggingface_hub.constants')
    cache = getattr(constants, 'HF_HUB_CACHE', None)
    if isinstance(cache, (str, os.PathLike)):
        context['hf_hub_cache'] = str(cache)[:32768]
    try:
        context['voxcpm_version'] = importlib.metadata.version('voxcpm')[:256]
    except Exception:
        context['voxcpm_version'] = 'unavailable'
    if isinstance(error, ModelPathError):
        context['rejected_model_path'] = error.details
    return context


def main():
    global STAGE
    print('Creating a NEW private report folder beside this inspector; applying its DACL only. '
          'Reading and hashing installed cached model files sequentially; no inference or downloads.')
    if len(sys.argv) != 1 or os.name != 'nt':
        print('BLOCKED: Windows owner-run inspector accepts no arguments.')
        return 1
    folder = Path(__file__).resolve().parent / ('private-inventory-' + uuid.uuid4().hex)
    acl_verified = False
    try:
        STAGE = 'private_folder_create'
        folder.mkdir(exist_ok=False)
        STAGE = 'private_folder_acl_apply'
        result = subprocess.run([str(_system_powershell()), '-NoLogo', '-NoProfile',
            '-NonInteractive', '-Command', PRIVATE_ACL], input=json.dumps({'path': str(folder)}),
            text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
            shell=False, check=False)
        if result.returncode:
            raise ValueError('private_folder_acl_failed')
        STAGE = 'private_folder_acl_verify'
        verify_spool_acl(folder)
        acl_verified = True
        STAGE = 'inspection'
        report = inspect()
        STAGE = 'report_write'
        with (folder / 'inventory.partial').open('x', encoding='utf-8') as out:
            json.dump(report, out, indent=2, ensure_ascii=True)
            out.flush()
            os.fsync(out.fileno())
        (folder / 'inventory.partial').rename(folder / 'inventory.json')
        print('PASS inventory only: ' + folder.name + '/inventory.json')
        return 0
    except Exception as exc:
        error_type = type(exc).__name__
        if not re.fullmatch('[A-Za-z_]{1,64}', error_type):
            error_type = 'Exception'
        print('BLOCKED: ' + STAGE + ' (' + error_type + '); no model changes made.')
        if acl_verified:
            try:
                failure = {'schema_version': 1, 'status': 'BLOCKED', 'stage': STAGE,
                    'exception_type': error_type, 'private_context': failure_context(exc),
                    'frames': [{'file': frame.filename, 'line': frame.lineno, 'function': frame.name}
                               for frame in traceback.extract_tb(exc.__traceback__)[-16:]]}
                with (folder / 'failure.json').open('x', encoding='utf-8') as out:
                    json.dump(failure, out, indent=2, ensure_ascii=True)
                    out.flush()
                    os.fsync(out.fileno())
                print('Private diagnostics: ' + folder.name + '/failure.json')
            except Exception:
                print('Private diagnostics unavailable.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
