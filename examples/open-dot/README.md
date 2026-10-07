# Open Dot Example: Research Worker

An autonomous persistent research worker that operates with provider-managed local boundaries.

## Characteristics
- **Provider**: `open-dotz`
- **Governance**: Provider-managed (runs in declared isolated workspace)
- **Lifecycle**: Self-scheduling (ticks every 30 minutes to check arXiv and model updates)
- **Tool Capabilities**: Local workspace filesystem reading and markdown summarization

## Installation / Usage in Hermes
1. Open Hermes Desktop.
2. Select **DOTZ** in the left rail beside SESSIONS and BOTS.
3. Click **+ New Dot**, choose **Open Dot**, and supply the configuration above.
4. Or use the CLI / REST API:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/plugins/dotz/dots \
     -H "Content-Type: application/json" \
     -d @config.yaml
   ```
