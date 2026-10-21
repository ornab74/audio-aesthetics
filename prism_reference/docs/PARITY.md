# Feature parity audit (source vs. Flutter app)

**Meaning of status**: Live = Flutter screen with real backend route; Partial = screen/original module exists but workflow is narrowed; Source-only = original Python remains bundled, no Flutter route; New = not a feature in original.

| Original source feature | New status | Notes |
|---|---|---|
| Dashboard / project overview | Partial | Real ring/task counts; original QID color metrics not ported. |
| Local Gemma Chat | Partial | GGUF streaming + LiteRT Python; original encrypted Gemma download/unlock pipeline unported. |
| Encrypted GUI History | Partial | New encrypted sessions; old GUI database needs explicit migration. |
| Road Scanner | Partial | Typed inputs, local classification; no Quantum/entropy prompts, intentionally omitted. |
| Download Model | Partial | Local file inventory/config; downloader absent. |
| Global Settings and About | Live/partial | Runtime, vault, and settings; some specialized original settings absent. |
| Agent Chat / sessions | Partial | Persona chat only; complete multi-round AgentHarness tool engine not API-wrapped. |
| Memory Lab | Live | Original PrismStore remember/search/forget, with original TUI/Rhomgaic classes still preserved. |
| Ring Observatory | Live/partial | All seven true rings and search; local embedded Weaviate lifecycle not auto-started. |
| ChronoOrbit | Live/partial | Original task engine and approvals; no native background mobile scheduling. |
| CTX Lab | Partial | Original PRISM scoped summary; original reflex/subsurface Rhomgaic trace UI unported. |
| Tool Studio | Partial | Read-only AST scan; no file writes or shell execution via HTTP. |
| Local Models | Partial | GGUF server + LiteRT config; no model downloads/benchmark/launch process manager. |
| Activity | Live | Task audit events; original full GUI agent event bus not wrapped. |
| Deep Vault storage | Live/partial | Uses original AgentVault snapshots but a **new** passphrase-derived identity. |
| PRISM indexed Weaviate | Source-only | Original index code shipped, but new backend uses encrypted SQLite fallback. |
| Agent edit cycle, Chromatic/Rhomgaic maintenance | Source-only | Original `src/humoid_tui/` engine included intact; security gate pending. |
| Knowledge constellation | New | Visual project/ring mapping; not actual measured similarity. |
| Mobile-native embedded Python/LLM | Not implemented | Flutter mobile client requires secure connection to separately hosted Python backend. |

This is a substantial running-code foundation, **not a completed audited 1:1 conversion**. In particular, the GUI's original application is roughly 400KB of monolithic Python plus agent components and optional native inference dependencies; copying source unchanged is not equivalent to presenting those features in Flutter.
