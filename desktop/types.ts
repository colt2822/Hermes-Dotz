export type ProviderType = 'open-dotz' | 'drex-dotz' | 'gpt-dotz' | string

export interface ProviderFeatures {
  persistence: boolean
  scheduling: boolean
  model_selection: boolean
  tool_execution: boolean
  capabilities: boolean
  approvals: boolean
  receipts: boolean
  drex_governance: boolean
  events?: boolean
}

export interface ProviderDescriptor {
  id: string
  name: string
  description: string
  features: ProviderFeatures
  governance: string
}

export interface DotSummary {
  name: string
  state: 'IDLE' | 'RUNNING' | 'WAITING' | 'BLOCKED' | 'FAILED' | 'STOPPED' | string
  mission?: string
  provider: ProviderType
  governance?: string
  workspace?: string
  created_at?: number
  updated_at?: number
  task_count?: number
  last_task?: string
  next_wake?: string
  blocked_reason?: string
}

export interface ApprovalRequest {
  approval_id: string
  provider: string
  dot_id: string
  action: string
  description: string
  scope: string
  payload_summary: string
  created_at: number
  expires_at?: number
  status: 'pending' | 'approved' | 'denied' | string
  target?: string
  task_id?: string
  session_id?: string
  capability?: string
  details?: Record<string, unknown>
}

export interface DotActivityEvent {
  event_id: string
  dot_id: string
  event_type:
    | 'task_created'
    | 'task_started'
    | 'message'
    | 'tool_request'
    | 'tool_result'
    | 'approval_requested'
    | 'approval_granted'
    | 'approval_denied'
    | 'action_executed'
    | 'action_failed'
    | 'task_completed'
    | string
  title: string
  timestamp: number
  description?: string
  details?: Record<string, unknown>
}

export interface DotTask {
  task_id: string
  dot: string
  title: string
  status: string
  source: string
  result?: string | null
  created_at: number
  updated_at: number
}

export interface DrexReceipt {
  receipt_id: string
  dot: string
  task_id?: string
  session_id?: string
  capability: string
  action: string
  target: string
  decision: 'ALLOW' | 'BLOCK' | 'GRANT' | string
  reason?: string
  rule?: string
  grant_id?: string
  result?: string
  upstream_executed?: boolean | number
  ts: number
}

export interface DotResponsibility {
  name: string
  trigger: string
  next_due_at?: number | null
  last_run_at?: number | null
}

export interface DotDetail extends DotSummary {
  features: ProviderFeatures
  models?: {
    default: string
    escalate?: string
  }
  capabilities?: {
    allow: string[]
    deny: string[]
  }
  tasks?: DotTask[]
  receipts?: DrexReceipt[]
  activity?: DotActivityEvent[]
  approvals?: ApprovalRequest[]
  responsibilities?: DotResponsibility[]
  drex?: {
    pack: string
  }
}

export interface CreateDotPayload {
  name: string
  mission: string
  provider?: ProviderType
  workspace?: string
  default_model?: string
  escalate_model?: string
  capabilities_allow?: string[]
  capabilities_deny?: string[]
  schedule?: string
  drex_pack?: string
}
