"""Owns original AgentVault and PrismStore; serialized access to decrypted state."""
from __future__ import annotations
import asyncio, os, sys, secrets
from pathlib import Path
from .security import unlock_key
from .inference import Inference

ORIGINAL=Path(__file__).resolve().parents[2]/'original'
if str(ORIGINAL) not in sys.path:sys.path.insert(0,str(ORIGINAL))
from prism_core import PrismStore, RINGS
from agent_vault import AgentVault

ROOT=Path(os.environ.get('HUMOID_VAULT_DIR',str(Path.home()/'.humoid-prism-flutter'))).expanduser().resolve()

class AppState:
    def __init__(self, root:Path=ROOT):
        self.root = root
        self.vault: AgentVault | None = None
        self.prism: PrismStore | None = None
        self.inference = Inference()
        self.token = os.environ.get('HUMOID_API_TOKEN') or secrets.token_urlsafe(36)
        self.serial = asyncio.Lock()
        self.busy = False

    @property
    def unlocked(self): return self.vault is not None and self.prism is not None

    def open(self, password:str):
        if self.unlocked:return
        key=unlock_key(self.root,password)
        vault=AgentVault(key,root=self.root)
        try:
            vault.mount()
            prism=PrismStore(vault.prism_path)
            prism.restore_interrupted()
            self.vault=vault
            self.prism=prism
            self.inference.configure(vault.read_json('agent_settings.json.aes',{}).get('inference',{}))
            self.vault.persist()
        except BaseException:
            vault.abort()
            self.vault=self.prism=None
            raise

    def save(self):
        if self.vault:self.vault.persist()

    def close(self):
        if self.vault: self.vault.close() # on IO failure, don't discard working DB
        self.vault=None; self.prism=None

    def read_settings(self)->dict:
        return self.vault.read_json('agent_settings.json.aes',{})

    def write_settings(self, data:dict):
        self.vault.write_json('agent_settings.json.aes',data)

    def sessions(self)->dict:
        return self.vault.read_json('agent_sessions.json.aes',{'chats':{}})

    def save_sessions(self, obj:dict):
        self.vault.write_json('agent_sessions.json.aes',obj)

state = AppState()
