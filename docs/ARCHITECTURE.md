# Hermes Dotz Architecture

## Overview

The Hermes Dotz Bridge exposes persistent autonomous workers ("Dotz") to Hermes through a unified plugin interface and backend protocol.

```text
               Hermes Desktop / Web UI
                         │
                         ▼
             Hermes REST API & Plugin Host
               (/api/plugins/dotz/*)
                         │
                         ▼
                 ProviderRegistry
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
  OpenDotzProvider  DrexDotzProvider  GPTDotzProvider
       │                 │                 │
  Local Filesystem  Drex Firewall       LLM Endpoint
       │                 │                 │
       └─────────────────┴─────────────────┘
                         │
                 SQLite DotzStore
             (dots, tasks, receipts, events)
```

## Protocol Methods

All providers implement `DotProvider`:
- `list_dots()`: Roster of persistent workers
- `get_dot(dot_id)`: Detailed configuration, models, tasks, and state
- `create_dot(config)`: Worker initialization
- `start_dot(dot_id)` / `stop_dot(dot_id)`: Lifecycle transitions
- `assign_task(dot_id, task)`: Work obligation assignment
- `steer_dot(dot_id, message)`: Direct conversational guidance
- `get_activity(dot_id)`: Normalized chronological event stream
- `get_receipts(dot_id)`: Cryptographic audit trail
- `list_approvals(dot_id)`: Pending human-in-the-loop decisions
- `approve_action(dot_id, approval_id)`: Issue authorization or bounded grant
- `deny_action(dot_id, approval_id)`: Reject action
- `execute_action(dot_id, capability, action, args)`: Guarded execution
- `tick(dot_id)`: Trigger scheduled recurring obligations
