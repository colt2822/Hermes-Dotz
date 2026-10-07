# Hermes Dotz

> Run persistent AI workers as first-class agents inside Hermes.

Hermes Dotz connects Hermes to autonomous, stateful workers with persistent missions, scheduled obligations, execution history, and capability firewalls.

```text
       ┌───────────┬─────────┬─────────┐
       │ SESSIONS  │  BOTS   │  DOTZ   │
       └───────────┴─────────┴─────────┘
```

---

## Bots vs. Dotz

| Concept | Description |
| :--- | :--- |
| **Bot** | A configured conversational persona or assistant designed for ad-hoc dialog within interactive chat sessions. |
| **Dot** | A persistent autonomous worker with an ongoing mission, persistent state, assigned task obligations, activity history, and optional capability governance. |

---

## Provider Architecture

Hermes Dotz is backend-neutral. One unified UI and API contract supports multiple Dot implementations:

```text
                      Hermes
                        │
                        ▼
                Hermes Dotz Bridge
                        │
       ┌────────────────┼────────────────┐
       │                │                │
   Open Dotz        Drex Dotz         GPT Dotz
  (Autonomous)     (Firewall)        (Planning)
       │                │                │
       └────── public providers ─────────┘
                        │
                 extension API
                        │
                External Providers
                (e.g. custom extensions)
```

### 1. Open Dotz (`open-dotz`)
Default open-source provider for persistent workers operating with provider-managed workspace boundaries.
- **Persistence**: SQLite + filesystem state
- **Scheduling**: Automated tick / recurring obligations
- **Governance**: Provider-managed (runs within declared workspace)

### 2. Drex-governed Dotz (`drex-dotz`)
Governed worker experience powered by [Drex Agent Firewall](https://github.com/colt2822/Drex-Agent-Firewall).
- **Enforcement**: Hard `ALLOW` / `BLOCK` capability gates
- **Zero Upstream Execution**: Denied actions never reach the shell, filesystem, or network
- **Bounded Grants**: Mutation actions trigger interactive approval cards in Hermes Desktop
- **Receipts**: Cryptographically verified audit log with upstream execution counters

### 3. GPT-backed Dotz (`gpt-dotz`)
Lightweight persistent conversational and planning assistant backed by standard LLM endpoints.
- **Security Boundary**: Zero privileged tool access without declared capabilities
- **Governance**: Provider-managed

---

## Installation

### 1. Install via Hermes Plugin System

```bash
hermes plugins install colt2822/Hermes-Dotz
```

Or clone directly into your Hermes plugins directory:

```bash
git clone https://github.com/colt2822/Hermes-Dotz.git ~/.hermes/plugins/dotz
```

### 2. Python Package Installation

```bash
pip install hermes-dotz
# Or with Drex firewall support:
pip install "hermes-dotz[drex]"
```

---

## Quick Start

### 1. Start Hermes with Dotz Enabled

When Hermes boots, the left navigation rail will show:

```text
SESSIONS | BOTS | DOTZ
```

Click **DOTZ** to open the Dot roster.

### 2. Create Your First Dot

Click **+ New Dot** in the top rail or trigger `New Dot…` from the Command Palette (`Ctrl/Cmd+K`):

1. **Select Type**: Choose between **Open Dot**, **Drex Dot**, or **GPT Dot**.
2. **Name**: e.g., `Researcher` or `Developer`.
3. **Mission**: State the worker's primary operational goal.
4. **Click Create Dot**.

### 3. Assign Tasks & Steer

- Use the composer to assign task obligations.
- Click **Steer** to inject immediate guidance without interrupting the worker's mission.
- Review the chronological **Activity Stream** and **Receipts**.

---

## Extensibility

External or private providers can register with the bridge via the extension API:

```python
from hermes_dotz.registry import register_provider
from hermes_dotz.providers import BaseDotProvider

class CustomDotProvider(BaseDotProvider):
    @property
    def id(self) -> str:
        return "custom-dotz"
    # Implement protocol methods...

register_provider(CustomDotProvider)
```

---

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
Compatible with Hermes MIT interfaces.
