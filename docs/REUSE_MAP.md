# Hermes Dotz Bridge — Reuse & Classification Map

This document establishes the audit and component classification for extracting and open-sourcing the **Hermes Dotz Bridge** from the initial private `nova-dotz` implementation.

## Component Classification Summary

| Component | Origin Location | Classification | Action in Public Bridge |
| :--- | :--- | :--- | :--- |
| **Top-level DOTZ Navigation** | `apps/desktop/src/components/pane-shell/tree/store.ts` | `PUBLIC_GENERIC` | Reused directly. Preserves `SESSIONS \| BOTS \| DOTZ` invariant. |
| **Dot Rail / List View** | `apps/desktop/src/plugins/nova-dotz/dotz-pane.tsx` | `PUBLIC_GENERIC` | Extracted and generalized with provider badges (`OPEN`, `DREX`, `GPT`). |
| **Dot Creation UI** | `apps/desktop/src/plugins/nova-dotz/create-dialog.tsx` | `REFACTOR_REQUIRED` | Extracted. Replaced NOVA defaults with Provider selection (`Open Dot`, `Drex Dot`, `GPT Dot`) and conditional field rendering. |
| **Dot Central View** | `apps/desktop/src/plugins/nova-dotz/dot-view.tsx` | `REFACTOR_REQUIRED` | Extracted. Unified header and activity stream with feature-detected tabs (`Activity`, `Receipts`, `Capabilities`, `Approvals`). Removed hardcoded private tabs. |
| **Activity Timeline** | `apps/desktop/src/plugins/nova-dotz/dot-view.tsx` | `PUBLIC_GENERIC` | Normalized across all provider types (tasks, steering messages, executions). |
| **Message Composer / Steer**| `apps/desktop/src/plugins/nova-dotz/dot-view.tsx` | `PUBLIC_GENERIC` | Reused across all provider types. |
| **Status Indicators** | `apps/desktop/src/plugins/nova-dotz/dotz-pane.tsx` | `PUBLIC_GENERIC` | Retained state indicator colors (`RUNNING`: emerald, `BLOCKED`: rose, `WAITING`: amber, `IDLE`/`STOPPED`: neutral). |
| **Approval Cards** | `apps/desktop/src/plugins/nova-dotz/drex-decision-card.tsx` | `REFACTOR_REQUIRED` | Extracted into generic `ApprovalRequest` card contract with provider-specific adapters (Drex bounded grants vs provider-level authorization). |
| **Drex Decision Cards** | `apps/desktop/src/plugins/nova-dotz/drex-decision-card.tsx` | `DREX_SPECIFIC` | Preserved for Drex-governed providers to render ALLOW / BLOCK / GRANT receipts and upstream execution counters. |
| **Desktop REST API Client**| `apps/desktop/src/plugins/nova-dotz/api.ts` | `REFACTOR_REQUIRED` | Renamed from `nova-dotz` client to `dotz` client, added provider registry query and generic approval methods. |
| **Backend Plugin API** | `plugins/dotz/dashboard/plugin_api.py` | `REFACTOR_REQUIRED` | Extracted to backend-neutral router delegating to `DotProvider` registry. |
| **Scheduler / Tick Interface** | `dotz/schedules.py`, `plugins/dotz/dashboard/plugin_api.py` | `PUBLIC_GENERIC` | Supported for providers with `features.scheduling == True`. |
| **Dotz Runtime Adapter** | `drex-dotz/dotz/runtime.py` | `DREX_SPECIFIC` | Wrapped behind `DrexDotzProvider` adapter. |
| **Open Dotz Engine** | New generic implementation | `PUBLIC_GENERIC` | Created `OpenDotzProvider` using standard filesystem workspace and SQLite persistence without firewall dependency. |
| **GPT Dotz Engine** | New generic implementation | `PUBLIC_GENERIC` | Created `GPTDotzProvider` for lightweight persistent conversational agents. |
| **NOVA Delegation UI** | `apps/desktop/src/plugins/nova-dotz/dot-view.tsx` (`nova` tab) | `NOVA_PRIVATE` | Deleted from public repository. Available through generic external provider extension API. |
| **NOVA Frontier Adapter** | `drex-dotz/dotz/integrations/nova/adapter.py` | `NOVA_PRIVATE` | Stays in private codebase. Registered via external provider extension. |
| **Commercial Lead Pipeline Logic**| Private modules | `DELETE_FROM_PUBLIC` | Completely excluded from public bridge. |
| **Proprietary Trading & Customer Systems**| Private modules | `DELETE_FROM_PUBLIC` | Hard boundary: zero private references, credentials, or customer data permitted. |

---

## Detailed Classification Definitions

- **PUBLIC_GENERIC**: Clean, portable code suitable for any Hermes user regardless of backend.
- **DREX_SPECIFIC**: Specific to the Drex Agent Firewall integration; preserved for governed Dotz but isolated so non-Drex providers do not depend on it.
- **NOVA_PRIVATE**: Private internal architecture or proprietary prompts that must remain outside the public repository.
- **REFACTOR_REQUIRED**: Reusable core concept that requires decoupling from private system identifiers and restructuring into a provider-neutral interface.
- **DELETE_FROM_PUBLIC**: Proprietary, commercial, or sensitive files that must never appear in the public git history or release.
