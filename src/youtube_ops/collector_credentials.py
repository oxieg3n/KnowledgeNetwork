"""User-scoped Windows Credential Manager; never an environment-secret fallback."""
import ctypes
from ctypes import wintypes
import hashlib
import os
import re


def credential_target(base_url):
    return 'KnowledgeNetworkCollector/VoiceStudio/' + hashlib.sha256(base_url.encode()).hexdigest()


def validate_secret(secret, mode):
    if not isinstance(secret, str) or any(ord(c) < 33 or ord(c) > 126 for c in secret):
        raise ValueError('INVALID_VOICE_CREDENTIAL')
    if mode == 'share_pin':
        if not re.fullmatch(r'[0-9]{6}', secret):
            raise ValueError('INVALID_VOICE_PIN')
    elif mode == 'scoped_bearer':
        if not 16 <= len(secret) <= 2048 or secret.startswith('ovs_admin_session_'):
            raise ValueError('INVALID_SCOPED_VOICE_CREDENTIAL')
    else:
        raise ValueError('UNSUPPORTED_VOICE_AUTH_MODE')


class Credential(ctypes.Structure):
    _fields_ = [('Flags', wintypes.DWORD), ('Type', wintypes.DWORD),
                ('TargetName', wintypes.LPWSTR), ('Comment', wintypes.LPWSTR),
                ('LastWritten', wintypes.FILETIME), ('CredentialBlobSize', wintypes.DWORD),
                ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)), ('Persist', wintypes.DWORD),
                ('AttributeCount', wintypes.DWORD), ('Attributes', ctypes.c_void_p),
                ('TargetAlias', wintypes.LPWSTR), ('UserName', wintypes.LPWSTR)]


def _api():
    if os.name != 'nt':
        raise ValueError('BLOCKED_WINDOWS_CREDENTIAL_STORE')
    api = ctypes.WinDLL('Advapi32.dll', use_last_error=True)
    api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                             ctypes.POINTER(ctypes.POINTER(Credential))]
    api.CredReadW.restype = wintypes.BOOL
    api.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]
    api.CredWriteW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    return api


def read_credential(base_url, mode):
    api = _api()
    pointer = ctypes.POINTER(Credential)()
    if not api.CredReadW(credential_target(base_url), 1, 0, ctypes.byref(pointer)):
        raise ValueError('BLOCKED_VOICE_CREDENTIAL_MISSING')
    try:
        record = pointer.contents
        if record.CredentialBlobSize > 4096:
            raise ValueError('INVALID_VOICE_CREDENTIAL')
        secret = ctypes.string_at(record.CredentialBlob, record.CredentialBlobSize).decode('utf-16-le')
        validate_secret(secret, mode)
        version = (record.LastWritten.dwHighDateTime << 32) | record.LastWritten.dwLowDateTime
        return secret, version
    finally:
        api.CredFree(pointer)


def write_credential(base_url, secret, mode):
    validate_secret(secret, mode)
    api = _api()
    blob = bytearray(secret.encode('utf-16-le'))
    buffer = (ctypes.c_ubyte * len(blob)).from_buffer(blob)
    record = Credential(Type=1, TargetName=credential_target(base_url),
                        CredentialBlobSize=len(blob), CredentialBlob=buffer, Persist=2,
                        UserName='VoiceStudio consumption only', Comment='Collector private speech route')
    try:
        if not api.CredWriteW(ctypes.byref(record), 0):
            raise ValueError('VOICE_CREDENTIAL_SAVE_FAILED')
    finally:
        for index in range(len(blob)):
            blob[index] = 0
