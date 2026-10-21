# Internal localhost HTTP API

All routes except `/health` require `Authorization: Bearer <printed-token>`.

| Method | Route | Scope |
|---|---|---|
| GET | `/vault/status` | Locked/unlocked model metadata |
| POST | `/vault/unlock` | `{ "passphrase": "..." }` |
| POST | `/vault/lock` | Seal and close vault |
| GET | `/overview` | PRISM counts and due tasks |
| GET | `/memories` | Query: ring, project, limit |
| POST | `/memories` | `{text,ring,project,importance,summary,consent_index}` |
| GET | `/memories/search?q=...` | Real PRISM weighted search, strict scope optional |
| DELETE | `/memories/{id}` | Tombstone a memory |
| POST | `/memories/capsules` | `{query,project}` |
| GET | `/context?q=...` | Bounded scoped context packet |
| GET/POST | `/tasks` | List/create a scheduled task |
| GET | `/tasks/due` | Due task list, not auto-execution |
| POST | `/tasks/{id}/approve` | Explicit start → sealed → complete |
| POST | `/tasks/{id}/cancel` | Cancel a nonrunning task |
| GET | `/tasks/{id}/events` | Task audit trail |
| GET | `/sessions` | Encrypted chat history |
| DELETE | `/sessions/{name}` | Delete chat history by name |
| POST | `/chat` | Blocking local-model completion |
| POST | `/chat/stream` | SSE `data: {"delta":"..."}` then `{ "done":true }` |
| GET | `/agents` | Agent persona profiles |
| POST/DELETE | `/agents`, `/agents/{name}` | Manage persona prompts |
| GET/PUT | `/config`, `/config/inference` | Inference settings (vault-encrypted) |
| GET | `/models` | Local `.gguf`, `.litertlm` inventory |
| GET | `/workspace/scan` | Bounded read-only symbol scan |
| POST | `/road-scan` | Typed road risk classification (not driving guidance) |
| GET | `/activity` | Task events |

No remote API, push notifications, file editing, unrestricted shell access, or auto-execution endpoints are exposed.
