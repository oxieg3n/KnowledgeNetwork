"""Execute four leased native-editor operations; no queue, rendering, or session launch."""
import hashlib
import json
import os
from pathlib import Path
import re

from .collector_editor import OpenShot, EditorError
from .collector_narration_common import VoiceError, local_spool
from .collector_narrator_host import verify_spool_acl

EXECUTABLE = Path('C:/Program Files/OpenShot Video Editor/openshot-qt-cmd.exe')
EXECUTABLE_SHA256 = '3637d631e5b01f263c87e7bbc0c9d3dd5b75274f7489bd2f56da8940ce292ca7'
OPERATIONS = {'inspect', 'apply', 'save', 'reopen'}
ID = re.compile('[a-f0-9]{32}')
SHA = re.compile('[a-f0-9]{64}')


class EditorJobError(RuntimeError):
    pass


def outcome(operation, status, error=None, **evidence):
    operation = operation if isinstance(operation, str) and operation in OPERATIONS else 'invalid'
    result = {'status': status, 'provider': 'openshot_native', 'publication_eligible': False,
              'operation': operation, **evidence}
    if error:
        result['error'] = error.upper() if re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,127}', error) else 'EDITOR_OPERATION_FAILED'
    return result


def _no_links(value, exists=True):
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or str(path).startswith('\\\\'):
        raise EditorJobError('EDITOR_LOCAL_PATH_REQUIRED')
    for part in (path, *path.parents):
        if part.is_symlink(): raise EditorJobError('EDITOR_REPARSE_POINT_DENIED')
        try:
            attributes = getattr(part.lstat(), 'st_file_attributes', 0)
        except FileNotFoundError:
            if not exists and part == path: continue
            raise
        if attributes & 0x400: raise EditorJobError('EDITOR_REPARSE_POINT_DENIED')
    return path


def from_environment(session):
    try:
        vault = local_spool(_no_links(os.environ['COLLECTOR_EDITOR_VAULT']))
        verify_spool_acl(vault)
        _no_links(EXECUTABLE)
        client = OpenShot(EXECUTABLE, EXECUTABLE_SHA256, vault, session)
        client._managed_session()
        return client
    except Exception:
        raise EditorJobError('EDITOR_CONFIGURATION_BLOCKED') from None


def _raw(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()


def _new(path, value):
    raw = _raw(value)
    if len(raw) > 8 * 1024 * 1024: raise EditorJobError('EDITOR_RECEIPT_LIMIT')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest()


def _revision(context):
    if not isinstance(context, dict) or type(context.get('revision')) is not int or context['revision'] < 0:
        raise EditorJobError('EDITOR_NATIVE_CONTEXT_INVALID')
    return context['revision']


def execute(job_id, inputs, cancel, factory=from_environment):
    operation = inputs.get('operation', 'invalid') if isinstance(inputs, dict) else 'invalid'
    dispatched = False
    try:
        if (not isinstance(job_id, str) or not ID.fullmatch(job_id) or not isinstance(inputs, dict) or
                set(inputs) != {'session_id', 'operation', 'request'} or not isinstance(operation, str) or operation not in OPERATIONS or
                not isinstance(inputs['session_id'], str) or not ID.fullmatch(inputs['session_id'])):
            raise EditorJobError('EDITOR_INPUT_INVALID')
        request = inputs['request']
        fields = {'inspect': set(), 'apply': {'commands', 'base_revision'}, 'save': {'path'}, 'reopen': {'path', 'sha256'}}
        if not isinstance(request, dict) or set(request) != fields[operation]:
            raise EditorJobError('EDITOR_INPUT_INVALID')
        if operation == 'apply' and (type(request['base_revision']) is not int or request['base_revision'] < 0):
            raise EditorJobError('EDITOR_INPUT_INVALID')
        if operation == 'reopen' and (not isinstance(request['sha256'], str) or not SHA.fullmatch(request['sha256'])):
            raise EditorJobError('EDITOR_INPUT_INVALID')
        client = factory(inputs['session_id'])
        if client.session != inputs['session_id']:
            raise EditorJobError('EDITOR_SESSION_MISMATCH')
        client._managed_session()
        _no_links(client.vault)
        _no_links(client.receipts)
        intent_path = client.receipts / ('service-' + job_id + '-intent.json')
        receipt_path = client.receipts / ('service-' + job_id + '.json')
        if intent_path.exists() or receipt_path.exists():
            return outcome(operation, 'reconciliation_required', 'EDITOR_JOB_ALREADY_RECORDED')
        if operation == 'apply':
            client.validate_edits(request['commands'])
            for command in request['commands']:
                if command['method'] == 'file.import': _no_links(command['params']['path'])
        elif operation in ('save', 'reopen'):
            if not isinstance(request['path'], str) or len(request['path']) > 4096:
                raise EditorJobError('EDITOR_INPUT_INVALID')
            _no_links(request['path'], exists=operation == 'reopen')
            client.local_path(request['path'], {'.osp'}, exists=operation == 'reopen')
        if cancel.is_set(): return outcome(operation, 'cancelled', 'EDITOR_CANCELLED_BEFORE_DISPATCH')
        before = client.inspect()
        revision = _revision(before)
        if operation == 'apply' and revision != request['base_revision']:
            return outcome(operation, 'blocked', 'EDITOR_REVISION_CONFLICT')
        intent = {'schema_version': 1, 'kind': 'service.editor.operation', 'job_id': job_id,
                  'session_id': client.session, 'operation': operation, 'request_sha256': hashlib.sha256(_raw(request)).hexdigest(),
                  'executable_sha256': EXECUTABLE_SHA256, 'before': before,
                  'expected_revision': request['base_revision'] if operation == 'apply' else revision,
                  'review_only': True, 'publication_eligible': False}
        if cancel.is_set(): return outcome(operation, 'cancelled', 'EDITOR_CANCELLED_BEFORE_DISPATCH')
        intent_hash = _new(intent_path, intent)
        if cancel.is_set(): return outcome(operation, 'cancelled', 'EDITOR_CANCELLED_BEFORE_DISPATCH')
        dispatched = True
        if operation == 'inspect':
            native, after = before, before
        elif operation == 'apply':
            native = client.apply(request['commands'], request['base_revision'])
            after = client.inspect()
        elif operation == 'save':
            native = client.save(request['path'])
            after = client.inspect()
        else:
            native = client.reopen(request['path'], request['sha256'])
            after = client.inspect()
        final_revision = _revision(after)
        if operation in ('apply', 'reopen') and (not isinstance(native, dict) or native.get('revision') != final_revision):
            raise EditorJobError('EDITOR_REVISION_CHANGED_RECONCILE_REQUIRED')
        if cancel.is_set(): return outcome(operation, 'reconciliation_required', 'EDITOR_CANCELLED_AFTER_DISPATCH')
        receipt_hash = _new(receipt_path, {**intent, 'intent_sha256': intent_hash,
                                         'native_result': native, 'after': after, 'status': 'completed'})
        return outcome(operation, 'completed', revision=final_revision, native_receipt_sha256=receipt_hash)
    except Exception as exc:
        if dispatched or isinstance(exc, FileExistsError):
            status = 'reconciliation_required'
        elif isinstance(exc, (EditorJobError, EditorError, VoiceError, OSError)):
            status = 'blocked'
        elif isinstance(exc, (ValueError, TypeError)):
            status = 'failed'
        else:
            status = 'reconciliation_required'
        code = str(exc) if isinstance(exc, (EditorJobError, EditorError, VoiceError)) else 'EDITOR_OPERATION_FAILED'
        return outcome(operation, status, code)
