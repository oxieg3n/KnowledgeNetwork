"""Read-only Tailscale inventory capture; credentials and responses stay private."""
import argparse
import getpass
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from urllib.parse import urlencode, parse_qs

from . import collector_credentials as credentials
from .collector_narration_common import socket_deadline

TARGET = 'KnowledgeNetworkCollector/TailscalePolicyReview/ReadOnly'
DEVICES = '/api/v2/tailnet/-/devices?fields=all'
POLICY = '/api/v2/tailnet/-/acl'
VALIDATE = POLICY + '/validate'
PREVIEW = POLICY + '/preview'
MAX_RESPONSE = 8 * 1024 * 1024
MAX_DEVICES = 1000
ID = re.compile(r'[A-Za-z0-9_-]{1,128}')


class Blocked(RuntimeError):
    pass


class ApiError(Blocked):
    def __init__(self, status, body):
        super().__init__('api_http_' + str(status))
        self.body = body


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def validate_token(secret):
    if (not isinstance(secret, str) or not 16 <= len(secret) <= 2048 or
            any(ord(c) < 33 or ord(c) > 126 for c in secret)):
        raise Blocked('invalid_api_access_token')
    if secret.startswith(('tskey-client-', 'tskey-auth-')):
        raise Blocked('wrong_api_credential_type')
    return secret


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Blocked('invalid_json')
            result[key] = value
        return result
    try:
        return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise Blocked('invalid_json') from None


def request(method, path, secret, deadline, body=None):
    get_allowed = path in (DEVICES, POLICY) or re.fullmatch(r'/api/v2/device/[A-Za-z0-9_-]{1,128}/routes', path)
    preview_allowed = False
    if path.startswith(PREVIEW + '?'):
        query = parse_qs(path.split('?', 1)[1], strict_parsing=True)
        if set(query) == {'type', 'previewFor'} and query['type'] == ['ipport'] and len(query['previewFor']) == 1:
            target = query['previewFor'][0]
            try:
                address, port = target.rsplit(':', 1)
                ipaddress.ip_address(address.strip('[]'))
                preview_allowed = port == '9443'
            except ValueError:
                pass
    post_allowed = path == VALIDATE or preview_allowed
    if not ((method == 'GET' and get_allowed and body is None) or
            (method == 'POST' and post_allowed and isinstance(body, bytes) and 1 <= len(body) <= MAX_RESPONSE)):
        raise Blocked('endpoint_denied')
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise Blocked('capture_deadline')
    connection = http.client.HTTPSConnection('api.tailscale.com',
        timeout=min(15, remaining), context=ssl.create_default_context())
    try:
        with socket_deadline(deadline, None, False) as (register, check):
            connection.connect()
            register(connection.sock)
            # http.client uses neither environment proxies nor automatic redirects.
            headers = {'Authorization': 'Bearer ' + validate_token(secret),
                'Accept': 'application/hujson' if path == POLICY else 'application/json'}
            if method == 'POST':
                headers['Content-Type'] = 'application/hujson'
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            if response.getheader('Location') or response.getheader('Link'):
                raise Blocked('redirect_or_pagination_unverified')
            chunks, size = [], 0
            while True:
                check()
                block = response.read(min(65536, MAX_RESPONSE + 1 - size))
                if not block:
                    break
                size += len(block)
                if size > MAX_RESPONSE:
                    raise Blocked('response_limit')
                chunks.append(block)
            check()
            raw = b''.join(chunks)
            if secret.encode('ascii') in raw:
                raise Blocked('api_response_contains_credential')
            if response.status != 200:
                raise ApiError(response.status, raw)
            return raw
    except Blocked:
        raise
    except Exception:
        raise Blocked('api_transport_unverified') from None
    finally:
        connection.close()


def get(path, secret, deadline):
    return request('GET', path, secret, deadline)


PRIVATE_DIRECTORY = r'''
$ErrorActionPreference='Stop'
try {
 $r=[Console]::In.ReadToEnd() | ConvertFrom-Json
 $path=[IO.Path]::GetFullPath([string]$r.output)
 if($path.StartsWith('\\') -or ($r.create -and (Test-Path -LiteralPath $path))) {throw 'unsafe'}
 $parent=Get-Item -LiteralPath ([IO.Path]::GetDirectoryName($path)) -Force
 $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
 $allowed=@($sid,'S-1-5-18','S-1-5-32-544')
 $ancestorTrusted=@($allowed)+@('S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
 $first=$true
 for($item=$parent;$null -ne $item;$item=$item.Parent) {
  if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {throw 'unsafe'}
  $acl=Get-Acl -LiteralPath $item.FullName
  $raw=[Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(),0)
  $trusted=if($first){$allowed}else{$ancestorTrusted}
  if($null -eq $raw.DiscretionaryAcl -or $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $trusted) {throw 'unsafe'}
  foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
   if(($ace.PropagationFlags -band [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0) {continue}
   $mask=if($first){0x000D0156}else{0x000D0040}
   if($ace.AccessControlType -eq 'Allow' -and $ace.IdentityReference.Value -notin $trusted -and ($first -or ($ace.FileSystemRights -band $mask))) {throw 'unsafe'}
  }
  $first=$false
 }
 if(-not $r.create) {
  $file=Get-Item -LiteralPath $path -Force
  if($file.PSIsContainer -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint)) {throw 'unsafe'}
  $acl=Get-Acl -LiteralPath $path
  $raw=[Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(),0)
  if($null -eq $raw.DiscretionaryAcl -or $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $allowed) {throw 'unsafe'}
  foreach($ace in $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])) {
   if($ace.AccessControlType -ne 'Allow' -or $ace.IdentityReference.Value -notin $allowed) {throw 'unsafe'}
  }
  [Console]::Out.Write('{"ok":true}');exit 0
 }
 New-Item -ItemType Directory -Path $path -ErrorAction Stop | Out-Null
 $acl=[Security.AccessControl.DirectorySecurity]::new()
 $acl.SetOwner([Security.Principal.SecurityIdentifier]::new($sid));$acl.SetAccessRuleProtection($true,$false)
 foreach($who in $allowed) {$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($who),'FullControl','ContainerInherit,ObjectInherit','None','Allow'))}
 Set-Acl -LiteralPath $path -AclObject $acl
 $actual=Get-Acl -LiteralPath $path
 $raw=[Security.AccessControl.RawSecurityDescriptor]::new($actual.GetSecurityDescriptorBinaryForm(),0)
 if($null -eq $raw.DiscretionaryAcl -or -not $actual.AreAccessRulesProtected -or $actual.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne $sid) {throw 'unsafe'}
 $rules=@($actual.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
 if($rules.Count -ne 3) {throw 'unsafe'}
 foreach($rule in $rules) {
  if($rule.AccessControlType -ne 'Allow' -or $rule.IdentityReference.Value -notin $allowed -or $rule.IsInherited -or $rule.FileSystemRights -ne [Security.AccessControl.FileSystemRights]::FullControl -or $rule.InheritanceFlags -ne ([Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit) -or $rule.PropagationFlags -ne [Security.AccessControl.PropagationFlags]::None) {throw 'unsafe'}
 }
 [Console]::Out.Write('{"ok":true}')
 exit 0
} catch {[Console]::Out.Write('{"ok":false}');exit 1}
'''


def private_path(output, create):
    output = Path(output)
    if os.name != 'nt' or not output.is_absolute() or '..' in output.parts or str(output).startswith('\\\\'):
        raise Blocked('private_output_required')
    from .collector_narrator_host import _system_powershell
    result = subprocess.run([str(_system_powershell()), '-NoLogo', '-NoProfile', '-NonInteractive',
        '-Command', PRIVATE_DIRECTORY], input=json.dumps({'output': str(output), 'create': create}),
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=15,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode or result.stdout != '{"ok":true}':
        raise Blocked('private_output_acl_unverified')
    return output


def private_directory(output):
    return private_path(output, True)


def write(output, name, raw):
    with (output / name).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'file': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def devices(raw):
    value = decode(raw)
    if not isinstance(value, dict) or set(value) != {'devices'} or not isinstance(value['devices'], list) or len(value['devices']) > MAX_DEVICES:
        raise Blocked('device_inventory_incomplete')
    seen = set()
    for device in value['devices']:
        if (not isinstance(device, dict) or not isinstance(device.get('id'), str) or
                not ID.fullmatch(device['id']) or device['id'] in seen or
                not isinstance(device.get('addresses'), list) or not device['addresses']):
            raise Blocked('device_inventory_invalid')
        for address in device['addresses']:
            try:
                ipaddress.ip_address(address)
            except (ValueError, TypeError):
                raise Blocked('device_address_invalid') from None
        seen.add(device['id'])
    return value['devices']


def routes(raw):
    value = decode(raw)
    if not isinstance(value, dict) or set(value) != {'advertisedRoutes', 'enabledRoutes'}:
        raise Blocked('route_coverage_incomplete')
    for key in ('advertisedRoutes', 'enabledRoutes'):
        if not isinstance(value[key], list):
            raise Blocked('route_coverage_incomplete')
        for route in value[key]:
            if not isinstance(route, str):
                raise Blocked('route_coverage_invalid')
            try:
                ipaddress.ip_network(route, strict=False)
            except ValueError:
                raise Blocked('route_coverage_invalid') from None
    # Enabled routes may be preapproved before a node advertises them.
    return value


def capture(output):
    try:
        secret, _ = credentials.read_secret(TARGET)
        validate_token(secret)
    except ValueError:
        raise Blocked('dedicated_credential_unavailable') from None
    output = private_directory(output)
    deadline = time.monotonic() + 90
    receipt = {'schema_version': 1, 'status': 'BLOCKED', 'files': [], 'routes': [], 'started_at': timestamp(),
        'policy_applied': False, 'official_policy_evaluation': 'NOT_TESTED',
        'identity_completeness': 'NOT_VERIFIED_NO_USERS_ENDPOINT'}
    try:
        raw = get(DEVICES, secret, deadline)
        receipt['files'].append(write(output, 'devices.private.json', raw))
        inventory = devices(raw)
        receipt['device_count'] = len(inventory)
        for index, device in enumerate(inventory):
            item = {'device_id': device['id'], 'status': 'BLOCKED'}
            try:
                raw = get('/api/v2/device/' + device['id'] + '/routes', secret, deadline)
                receipt['files'].append(write(output, f'routes-{index:04d}.private.json', raw))
                value = routes(raw)
                item.update(status='PASS', advertised_count=len(value['advertisedRoutes']),
                    enabled_count=len(value['enabledRoutes']), exit_node_advertised=any(
                        ipaddress.ip_network(x, strict=False).prefixlen == 0 for x in value['advertisedRoutes']),
                    exit_node_enabled=any(ipaddress.ip_network(x, strict=False).prefixlen == 0 for x in value['enabledRoutes']))
            except Blocked as error:
                item['error'] = str(error)
            receipt['routes'].append(item)
        raw = get(POLICY, secret, deadline)
        receipt['files'].append(write(output, 'policy.private.hujson', raw))
        try:
            if not raw.decode('utf-8-sig').strip():
                raise ValueError()
        except (ValueError, UnicodeError):
            raise Blocked('policy_response_invalid') from None
        if all(item['status'] == 'PASS' for item in receipt['routes']):
            receipt['status'] = 'PASS_CAPTURE_ONLY'
    except Blocked as error:
        receipt['error'] = str(error)
    finally:
        receipt['finished_at'] = timestamp()
        receipt['freshness'] = 'CAPTURE_INTERVAL_NOT_ATOMIC_SNAPSHOT'
        write(output, 'capture.private.json', json.dumps(receipt, indent=2).encode())
    return {'status': receipt['status'], 'device_count': receipt.get('device_count', 0),
        'route_failures': sum(x['status'] != 'PASS' for x in receipt['routes']),
        'error': receipt.get('error'), 'policy_applied': False}


def validate_policy(policy_file, expected_hash, output):
    if not re.fullmatch('[a-f0-9]{64}', expected_hash):
        raise Blocked('invalid_policy_digest')
    policy = private_path(policy_file, False)
    for part in (policy, *policy.parents):
        if part.is_symlink() or getattr(part.lstat(), 'st_file_attributes', 0) & 0x400:
            raise Blocked('policy_path_untrusted')
    if not policy.is_file() or policy.stat().st_nlink != 1:
        raise Blocked('policy_path_untrusted')
    with policy.open('rb') as stream:
        raw_policy = stream.read(MAX_RESPONSE + 1)
    if not raw_policy or len(raw_policy) > MAX_RESPONSE or hashlib.sha256(raw_policy).hexdigest() != expected_hash:
        raise Blocked('policy_digest_mismatch')
    # Select hypothetical-policy mode, never the endpoint's JSON-array test mode.
    try:
        prefix = raw_policy.decode('utf-8-sig').lstrip()
        while prefix.startswith(('//', '/*')):
            if prefix.startswith('//'):
                prefix = prefix.split('\n', 1)[1].lstrip()
            else:
                end = prefix.index('*/', 2)
                prefix = prefix[end + 2:].lstrip()
        if not prefix.startswith('{'):
            raise ValueError()
    except (ValueError, UnicodeError, IndexError):
        raise Blocked('hypothetical_policy_object_required') from None
    try:
        secret, _ = credentials.read_secret(TARGET)
        validate_token(secret)
    except ValueError:
        raise Blocked('dedicated_credential_unavailable') from None
    output = private_directory(output)
    deadline = time.monotonic() + 90
    receipt = {'schema_version': 1, 'status': 'BLOCKED', 'started_at': timestamp(),
        'policy_sha256': expected_hash, 'files': [], 'policy_applied': False,
        'preview_status': 'NOT_TESTED', 'identity_completeness': 'NOT_VERIFIED_NO_USERS_ENDPOINT'}
    try:
        receipt['files'].append(write(output, 'candidate.private.hujson', raw_policy))
        raw = request('POST', VALIDATE, secret, deadline, raw_policy)
        receipt['files'].append(write(output, 'validation.private.json', raw))
        value = decode(raw) if raw.strip() else {}
        if not isinstance(value, dict) or any(value.get(key) for key in ('message', 'error', 'errors', 'warnings', 'data')):
            raise Blocked('official_validation_failed_or_warned')
        receipt['status'] = 'PASS_OFFICIAL_VALIDATION_ONLY'
        # Preview targets come only from the pinned JSON candidate tests, never argv.
        try:
            candidate = decode(raw_policy)
            targets = sorted({target for test in candidate.get('tests', [])
                for key in ('accept', 'deny') for target in test.get(key, []) if target.endswith(':9443')})
        except (Blocked, TypeError, AttributeError):
            targets = []
        if not targets or len(targets) > 20:
            receipt['preview_status'] = 'BLOCKED_TARGETS_UNVERIFIED'
        else:
            receipt['preview_status'] = 'CAPTURED_REQUIRES_RULE_REVIEW'
            for index, target in enumerate(targets):
                path = PREVIEW + '?' + urlencode({'type': 'ipport', 'previewFor': target})
                raw = request('POST', path, secret, deadline, raw_policy)
                receipt['files'].append(write(output, f'preview-{index:02d}.private.json', raw))
                value = decode(raw)
                if (not isinstance(value, dict) or value.get('type') != 'ipport' or
                        value.get('previewFor') != target or not isinstance(value.get('matches'), list)):
                    raise Blocked('preview_response_unverified')
    except Blocked as error:
        receipt['status'] = 'BLOCKED'
        receipt['error'] = str(error)
        if isinstance(error, ApiError):
            receipt['files'].append(write(output, 'api-error.private.json', error.body))
    finally:
        receipt['finished_at'] = timestamp()
        write(output, 'validation-receipt.private.json', json.dumps(receipt, indent=2).encode())
    return {key: receipt.get(key) for key in ('status', 'error', 'preview_status', 'policy_applied')}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('credential-save')
    command = commands.add_parser('capture')
    command.add_argument('--output', required=True)
    command = commands.add_parser('validate')
    command.add_argument('--policy-file', required=True)
    command.add_argument('--policy-sha256', required=True)
    command.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'credential-save':
            if not sys.stdin.isatty():
                raise Blocked('interactive_hidden_input_required')
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                secret = validate_token(getpass.getpass('Dedicated read-only Tailscale access token: '))
                credentials.write_secret(TARGET, secret)
            print(json.dumps({'status': 'SAVED'}))
            return 0
        result = (capture(args.output) if args.command == 'capture' else
            validate_policy(args.policy_file, args.policy_sha256, args.output))
        print(json.dumps(result))
        return 0 if result['status'].startswith('PASS_') else 1
    except Exception as error:
        code = str(error) if isinstance(error, Blocked) else 'review_unverified'
        print(json.dumps({'status': 'BLOCKED', 'error': code, 'credential_target': TARGET}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
