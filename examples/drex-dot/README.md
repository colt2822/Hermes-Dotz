# Drex Dot Example: Developer Worker

A persistent engineering worker governed by **Drex Agent Firewall**.

## Characteristics
- **Provider**: `drex-dotz`
- **Governance**: Drex
- **Policy Enforcement**:
  - `ALLOW`: Safe reads and test runs within the workspace
  - `BLOCK`: Zero upstream execution for unauthorized access (e.g. `~/.ssh`, root filesystem)
  - `MUTATION_GRANT_REQUIRED`: Writes trigger a bounded human approval card in Hermes Desktop
- **Receipts**: Cryptographically verified append-only execution log

## Usage
1. Open Hermes Desktop ▸ **DOTZ** ▸ **+ New Dot**.
2. Select **Drex Dot**.
3. Set your target workspace path and capabilities.
4. When the worker attempts an ungranted mutation, approve or deny it directly from the approval card in Hermes!
