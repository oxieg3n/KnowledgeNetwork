"""Provider-neutral private narration storage, PCM validation and bounded I/O."""
from contextlib import contextmanager
import hashlib
import io
import ipaddress
import json
import os
from pathlib import Path
import socket
import threading
import time
import wave

MAX_JSON = 8 * 1024 * 1024
MAX_WAV = 64 * 1024 * 1024

class VoiceError(RuntimeError):
    """Public-safe status, never a raw server body, address or secret."""


@contextmanager
def socket_deadline(deadline, cancel, is_post):
    """Interrupt blocking headers, TLS or body I/O even if a peer keeps dripping."""
    stopped, active, cause = threading.Event(), [None], [None]

    def reason():
        if cancel and cancel.is_set():
            return 'VOICE_CANCELLED_RESULT_UNKNOWN' if is_post else 'VOICE_CANCELLED'
        if time.monotonic() >= deadline:
            return 'VOICE_TIMEOUT_RESULT_UNKNOWN' if is_post else 'VOICE_READ_DEADLINE'
        return None

    def check():
        code = cause[0] or reason()
        if code:
            raise VoiceError(code)

    def register(transport):
        active[0] = transport
        check()

    def watch():
        while not stopped.wait(.02):
            if code := reason():
                cause[0] = code
                if active[0] is not None:
                    try:
                        active[0].shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    # Windows file wrappers can defer socket.close(). Detach
                    # and close the handle now to wake a stalled buffered read.
                    try:
                        socket.close(active[0].detach())
                    except OSError:
                        pass
                return

    watcher = threading.Thread(target=watch, name='collector-voice-deadline', daemon=True)
    watcher.start()
    try:
        yield register, check
    finally:
        stopped.set()
        watcher.join(timeout=.2)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def sha256_file(path, *, deadline=None):
    if deadline is not None and time.monotonic() >= deadline:
        raise VoiceError('VOICE_HASH_DEADLINE')
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            if deadline is not None and time.monotonic() >= deadline:
                raise VoiceError('VOICE_HASH_DEADLINE')
            result.update(block)
    return result.hexdigest()


def checkpoint(path, value):
    with path.with_suffix('.tmp').open('w', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.flush(); os.fsync(stream.fileno())
    os.replace(path.with_suffix('.tmp'), path)


def read_json(path):
    if Path(path).stat().st_size > MAX_JSON:
        raise VoiceError('VOICE_INPUT_TOO_LARGE')
    value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise VoiceError('INVALID_VOICE_JSON')
    return value


def inspect_wav(source):
    """Decode all PCM frames without loading an entire remote recording into RAM."""
    data = io.BytesIO(source) if isinstance(source, bytes) else str(source)
    try:
        with wave.open(data, 'rb') as audio:
            channels, width, rate, frames = (audio.getnchannels(), audio.getsampwidth(),
                                            audio.getframerate(), audio.getnframes())
            if channels not in (1, 2) or width not in (2, 3, 4) or not 8000 <= rate <= 192000:
                raise VoiceError('INVALID_AUDIO_FORMAT')
            if not 0 < frames / rate <= 600:
                raise VoiceError('INVALID_AUDIO_DURATION')
            decoded = sum(len(block) for block in iter(lambda: audio.readframes(16384), b''))
            if decoded != frames * channels * width:
                raise VoiceError('TRUNCATED_AUDIO')
    except (wave.Error, EOFError) as exc:
        raise VoiceError('INVALID_WAV') from exc
    return {'duration_seconds': frames / rate, 'sample_rate': rate, 'channels': channels,
            'sample_width': width, 'frames': frames,
            'sha256': hashlib.sha256(source).hexdigest() if isinstance(source, bytes) else sha256_file(source)}


def private_address(value):
    address = ipaddress.ip_address(value)
    allowed = (ipaddress.ip_network('10.0.0.0/8'), ipaddress.ip_network('172.16.0.0/12'),
               ipaddress.ip_network('192.168.0.0/16'), ipaddress.ip_network('100.64.0.0/10'),
               ipaddress.ip_network('fc00::/7'))
    return any(address.version == network.version and address in network for network in allowed)


def local_spool(path):
    spool = Path(path)
    if not spool.is_absolute() or not spool.is_dir() or str(spool).startswith('\\\\'):
        raise VoiceError('BLOCKED_LOCAL_VOICE_SPOOL')
    for part in (spool, *spool.parents):
        if part.is_symlink() or getattr(part.stat(), 'st_file_attributes', 0) & 0x400:
            raise VoiceError('BLOCKED_VOICE_SPOOL_REPARSE_POINT')
    return spool


@contextmanager
def voice_lease(spool):
    with (spool / 'remote-voice.lock').open('a+b') as stream:
        if stream.tell() == 0:
            stream.write(b'0'); stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise VoiceError('BLOCKED_VOICE_BACKPRESSURE') from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

