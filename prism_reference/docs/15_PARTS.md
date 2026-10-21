# Fifteen-part implementation map

This archive contains one consolidated source tree. The 15 parts here are **implementation work packages**, not separate installable binary releases. Existing code is linked in each stage; uncompleted parity work is flagged.

1. **Original baseline** — `original/main.py`, `original/agent_gui.py`, `original/prism_core.py`; original source and tests preserved. ✅
2. **Flutter workspace** — `flutter/main.dart`, `flutter/pubspec.yaml`, `flutter/screens/shell.dart`; responsive desktop/mobile navigation. ✅ source, ⚠️ not compiled here.
3. **Retro Material 3 components** — `flutter/core/palette.dart`, `flutter/widgets/orbit_widgets.dart`, included art. ✅
4. **Authenticated vault backend** — `backend/server/security.py`, `state.py`, `app.py`; original `AgentVault`. ✅ API-tested.
5. **LiteRT-LM / GGUF** — `backend/server/inference.py` and Local Models UI. ✅ adapters, ⚠️ models/native packages untested.
6. **Chat and encrypted history** — `/chat`, `/chat/stream`, `/sessions`, `ChatPage`, `HistoryPage`. ✅ simulated model integration test.
7. **Mission Control / Road Scanner** — `HomePage`, `RoadPage`, `/road-scan`. ✅ partial QID parity.
8. **Agent Workshop** — `/agents`, `AgentsPage`, system-profile chat. ✅ persona layer; ⚠️ original multi-tool harness remains source-only.
9. **Memory Lab** — `/memories`, search, forget and memory screen. ✅ PRISM integration-tested.
10. **Ring Observatory** — seven real rings + interactive `ConstellationPage`. ✅ project-derived graph, not semantic embedding.
11. **CTX Lab** — `/context`, original `PrismStore.summary_packet`. ✅ bounded recall, ⚠️ full Rhomgaic trace not ported.
12. **ChronoOrbit** — `/tasks`, `/tasks/due`, `/tasks/{id}/approve`, `OrbitPage`. ✅ approvals and recurrence, no OS background alerts.
13. **Tools / code intelligence** — `/workspace/scan`, `ToolPage`. ✅ read-only; ⚠️ write/execute tools not exposed.
14. **Models, unified settings, activity** — `/models`, `/config`, `/activity`, settings/activity screens. ✅ model inventory/config; ⚠️ downloader absent.
15. **Release and parity validation** — 13 Python backend tests + 18 original fusion tests + Flutter widget test source + audit docs; ⚠️ Flutter compilation, platform packaging, 1:1 feature completion still need development.
