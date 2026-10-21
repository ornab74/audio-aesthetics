"""Optional, read-only PRISM memory importer from original Humoid Fusion vault.

Run only while the original GUI is CLOSED and after taking encrypted backups.
Does not import GUI chat_history.db.aes, model weights, TUI tools, or tasks.
"""
from __future__ import annotations
import argparse, getpass, hmac, struct, sys
from pathlib import Path
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from server.state import AppState
from agent_vault import AgentVault
from prism_core import PrismStore

MAGIC=b'HMK2'


def gui_master_key(keyfile:Path,password:str)->bytes:
    raw=keyfile.read_bytes()
    if raw.startswith(MAGIC):
        if len(raw)<5+4+16+12+16 or raw[4]!=2:raise ValueError('Unsupported original key record')
        iterations=struct.unpack('>I',raw[5:9])[0]
        if not 100000<=iterations<=5_000_000:raise ValueError('Unsupported KDF work factor')
        salt,nonce,cipher=raw[9:25],raw[25:37],raw[37:]
        k=PBKDF2HMAC(algorithm=hashes.SHA256(),length=32,salt=salt,iterations=iterations).derive(password.encode())
        return AESGCM(k).decrypt(nonce,cipher,MAGIC)
    if len(raw)>=48:
        salt,expected=raw[:16],raw[16:48]
        key=PBKDF2HMAC(algorithm=hashes.SHA256(),length=32,salt=salt,iterations=200000).derive(password.encode())
        if not hmac.compare_digest(key,expected):raise ValueError('Incorrect original passphrase')
        return key
    if len(raw)==32:return raw
    raise ValueError('Unrecognized keyfile layout')


def import_vault(legacy_root:Path,new_root:Path,original_password:str,new_password:str)->int:
    legacy_root=legacy_root.resolve();new_root=new_root.resolve()
    if legacy_root==new_root or (legacy_root/'.humoid').resolve()==new_root:
        raise ValueError('Destination must be a separate vault directory')
    source=legacy_root/'.humoid'/'agent_prism.sqlite3.aes'
    if not source.is_file():raise FileNotFoundError(f'Original encrypted PRISM snapshot not found: {source}')
    oldkey=gui_master_key(legacy_root/'.enc_key',original_password)
    oldvault=AgentVault(oldkey,root=legacy_root/'.humoid')
    newstate=AppState(new_root)
    try:
        oldvault.mount(read_only=True)
        if not oldvault.prism_path or not oldvault.prism_path.exists():
            raise RuntimeError('Decrypted PRISM snapshot absent')
        store=PrismStore(oldvault.prism_path)
        newstate.open(new_password)
        count=0
        with store.db() as db:
            rows=[dict(r) for r in db.execute('SELECT * FROM ring_memories WHERE deleted=0 ORDER BY created_at')]
        for mem in rows:
            source_id='migration:original-prism:'+mem['id']
            with newstate.prism.db() as db:
                if db.execute('SELECT 1 FROM ring_memories WHERE source_id=?',(source_id,)).fetchone():continue
            newstate.prism.remember(mem['text'],ring=mem['ring'],project=mem['project'],
                summary=mem['summary'],importance=mem['importance'],verified=bool(mem['verified']),
                consent_index=False,source_id=source_id)
            count+=1
        newstate.save()
        return count
    finally:
        if newstate.unlocked:newstate.close()
        oldvault.abort() # NEVER write to the original encrypted vault


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Read-only import of PRISM memories from original Humoid vault')
    parser.add_argument('original_project',type=Path,help='Directory containing .enc_key and .humoid/')
    parser.add_argument('--target',type=Path,default=Path.home()/'.humoid-prism-flutter')
    args=parser.parse_args()
    print('Close the original GUI first. Backup BOTH encrypted vault folders before proceeding.')
    print('Only PRISM memory text is imported, not chat history, tasks or encrypted models.')
    try:
        old_pw=getpass.getpass('Original Humoid passphrase (if applicable): ')
        new_pw=getpass.getpass('New Flutter vault passphrase: ')
        count=import_vault(args.original_project,args.target,old_pw,new_pw)
        print(f'Imported {count} new PRISM memories into {args.target}. Source vault unchanged.')
    except Exception as exc:
        print(f'Import failed: {exc}',file=sys.stderr);raise SystemExit(1)
