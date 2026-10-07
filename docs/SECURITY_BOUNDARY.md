# Security Boundary and Governance Model

Hermes Dotz enforces clear security and authorization boundaries across all supported worker provider classes.

---

## Governance Spectrum

| Provider Class | Governance Model | Tool / Action Enforcement | Mutation Grants | Upstream Guarantee |
| :--- | :--- | :--- | :--- | :--- |
| **Open Dotz** (`open-dotz`) | **Provider-managed** | Confined strictly to declared workspace filesystem | None (direct execution within workspace) | Actions execute directly in isolated directory. No kernel/firewall guarantees. |
| **Drex Dotz** (`drex-dotz`) | **Drex Agent Firewall** | Strict capability matrix evaluated per-action | Mandatory bounded grant with TTL & use count | Hard guarantee: Denied actions result in **0 upstream executions**. |
| **GPT Dotz** (`gpt-dotz`) | **Provider-managed** | **Zero tool access** (pure reasoning / planning) | None | Non-conversational actions are strictly rejected. No silent privilege inheritance. |

---

## Principle of Zero Silent Privileges

1. **No Implicit Privilege Escalation**:
   When running outside of a Drex environment, non-governed workers (Open Dot, GPT Dot) do **not** silently inherit unrestricted host execution or shell privileges.
2. **Accurate Representation**:
   Hermes UI explicitly displays the active governance model (`Governance: Drex` vs. `Governance: Provider-managed`), preventing false security assumptions by users.
3. **Workspace Isolation**:
   File modifications by Open Dot workers are strictly bound to their assigned workspace root (`~/workspace/<dot_name>`).
4. **Human in the Loop**:
   For Drex-governed workers, all sensitive or irreversible mutations require an explicit, time-bounded human approval grant issued via the Hermes interface.
