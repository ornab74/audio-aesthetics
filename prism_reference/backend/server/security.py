"""A separate password-derived key for the *new* Flutter vault.

It DOES NOT guess or overwrite original Tkinter vault credentials.
"""
from __future__ import annotations
import json, os, secrets
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b'HUMOID-PRISM-FLUTTER-V1'


def derive(password: str, salt: bytes) -> bytes:
    if len(password) < 10:
        raise ValueError('Passphrase must be at least 10 characters')
    return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(password.encode())


def unlock_key(root: Path, password: str) -> bytes:
    """Create sentinel on the first run; authenticate before mounting on later runs."""
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    sentinel = root / 'vault.identity.json'
    if not sentinel.exists():
        # Refuse to initialize over original/mismatched encrypted vault contents.
        if list(root.glob('*.aes')):
            raise ValueError('Existing encrypted vault found without Flutter identity. Use an empty directory.')
        salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
        key = derive(password, salt)
        content = dict(salt=salt.hex(), nonce=nonce.hex(), proof=AESGCM(key).encrypt(nonce, MAGIC, MAGIC).hex())
        fd = os.open(sentinel, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as out:
            json.dump(content, out)
            out.flush(); os.fsync(out.fileno())
        return key
    blob = json.loads(sentinel.read_text())
    key = derive(password, bytes.fromhex(blob['salt']))
    try:
        check = AESGCM(key).decrypt(bytes.fromhex(blob['nonce']), bytes.fromhex(blob['proof']), MAGIC)
        if check != MAGIC: raise ValueError('Passphrase rejected')
    except Exception as exc:
        raise ValueError('Incorrect passphrase or corrupted vault identity') from exc
    return key
