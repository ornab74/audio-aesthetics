"""Local GGUF / LiteRT inference adapters. No remote cloud inference by default."""
from __future__ import annotations
import asyncio, json
from pathlib import Path
from urllib.parse import urlparse
import httpx


def validate_local_url(url: str) -> str:
    u = urlparse(url)
    if u.scheme != 'http' or u.hostname not in {'localhost', '127.0.0.1', '::1'} or not u.port:
        raise ValueError('Inference server must be HTTP on localhost with explicit port')
    if u.username or u.password or u.query or u.fragment:
        raise ValueError('Invalid inference endpoint')
    return url.rstrip('/')


class Inference:
    def __init__(self):
        self.backend = 'llama_cpp'
        self.base_url = 'http://127.0.0.1:8081/v1'
        self.model = 'local-gguf'
        self.litert_path = ''
        self.temperature = 0.7
        self.max_tokens = 1024

    def config(self) -> dict:
        return {k:getattr(self,k) for k in ('backend','base_url','model','litert_path','temperature','max_tokens')}

    def configure(self, settings: dict):
        # Validate the entire new configuration before assigning anything.
        # Invalid URLs must not leave a half-updated inference backend behind.
        backend = settings.get('backend', self.backend)
        if backend not in {'llama_cpp','litert_lm'}: raise ValueError('Unknown model runtime')
        base_url = validate_local_url(str(settings.get('base_url', self.base_url)))
        model = str(settings.get('model', self.model))[:200]
        litert_path = str(settings.get('litert_path', self.litert_path))[:4096]
        temperature = max(0., min(2., float(settings.get('temperature', self.temperature))))
        tokens = max(16, min(8192, int(settings.get('max_tokens', self.max_tokens))))
        self.backend = backend
        self.base_url = base_url
        self.model = model
        self.litert_path = litert_path
        self.temperature = temperature
        self.max_tokens = tokens

    @staticmethod
    def _litert_blocking(path: str, messages: list[dict]) -> str:
        import litert_lm
        if not path or not Path(path).is_file() or not path.endswith('.litertlm'):
            raise ValueError('Select a readable local .litertlm model')
        # LiteRT conversation is stateful; rebuild the local context for each request.
        dialogue = '\n'.join(f"{m.get('role','user').upper()}: {m.get('content','')}" for m in messages[-24:])
        with litert_lm.Engine(path) as engine:
            with engine.create_conversation() as conv:
                res = conv.send_message(dialogue)
        return '\n'.join(str(item.get('text','')) for item in res.get('content',[]) if isinstance(item,dict))

    async def complete(self, messages: list[dict]) -> str:
        if self.backend == 'litert_lm':
            return await asyncio.to_thread(self._litert_blocking, self.litert_path, messages)
        url = validate_local_url(self.base_url) + '/chat/completions'
        payload = {'model':self.model,'messages':messages,'max_tokens':self.max_tokens,
                   'temperature':self.temperature,'stream':False}
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=8), trust_env=False) as client:
            res=await client.post(url,json=payload)
            res.raise_for_status()
            return str(res.json()['choices'][0]['message']['content'] or '')

    async def stream(self, messages: list[dict]):
        if self.backend == 'litert_lm':
            yield await self.complete(messages)
            return
        url = validate_local_url(self.base_url) + '/chat/completions'
        payload = {'model':self.model,'messages':messages,'max_tokens':self.max_tokens,
                   'temperature':self.temperature,'stream':True}
        async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=8),trust_env=False) as client:
            async with client.stream('POST',url,json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith('data: '): continue
                    data=line[6:].strip()
                    if data=='[DONE]':break
                    try:
                        token=json.loads(data)['choices'][0]['delta'].get('content') or ''
                        if token: yield str(token)
                    except (ValueError,KeyError,IndexError,TypeError):continue
