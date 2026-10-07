/**
 * Hermes Dotz Bridge Data Layer.
 *
 * Communicates with the Dotz backend via the `/api/plugins/dotz/*` routes.
 * Uses the scoped PluginContext REST client for the registered Dotz plugin.
 */

import { atom } from 'nanostores'
import type { PluginContext, PluginRestOptions } from '@hermes/plugin-sdk'
import type {
  ApprovalRequest,
  CreateDotPayload,
  DotActivityEvent,
  DotDetail,
  DotSummary,
  DrexReceipt,
  ProviderDescriptor,
} from './types'

type RestFn = <T>(path: string, opts?: PluginRestOptions) => Promise<T>

let _rest: RestFn | null = null
let _pluginCtx: PluginContext | null = null

export function setDotzContext(ctx: PluginContext) {
  _pluginCtx = ctx
  if (ctx && typeof ctx.rest === 'function') {
    _rest = ctx.rest.bind(ctx)
  }
}

/** Atom holding the selected Dot name */
export const $selectedDotName = atom<string | null>(null)

/** Atom holding the roster of Dotz */
export const $dotsList = atom<DotSummary[]>([])

/** Atom holding available providers and feature matrices */
export const $availableProviders = atom<ProviderDescriptor[]>([])

/** Atom holding the active Dot's detailed state */
export const $activeDotDetail = atom<DotDetail | null>(null)

/** Loading and refreshing status */
export const $dotzLoading = atom<boolean>(false)

/** Create Dot Dialog visibility */
export const $createDotDialogOpen = atom<boolean>(false)

/** Helper to call REST endpoints */
async function callRest<T>(endpoint: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const method = options.method || 'GET'
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`

  if (_rest) {
    const restOpts: PluginRestOptions = {
      method: method as PluginRestOptions['method'],
    }
    if (options.body) {
      restOpts.body = options.body
      restOpts.headers = { 'Content-Type': 'application/json' }
    }
    return await _rest<T>(path, restOpts)
  }
  throw new Error('Dotz plugin REST context is not available; refusing unscoped request')
}

export async function fetchProviders(): Promise<ProviderDescriptor[]> {
  try {
    const res = await callRest<{ providers: ProviderDescriptor[] }>('/providers')
    $availableProviders.set(res.providers || [])
    return res.providers || []
  } catch (err) {
    console.error('[dotz] Failed to fetch providers:', err)
    return []
  }
}

export async function fetchDots(): Promise<DotSummary[]> {
  try {
    $dotzLoading.set(true)
    const res = await callRest<{ dots: DotSummary[] }>('/dots')
    const list = res.dots || []
    $dotsList.set(list)
    return list
  } catch (err) {
    console.error('[dotz] Failed to fetch dots:', err)
    return []
  } finally {
    $dotzLoading.set(false)
  }
}

export async function fetchDotDetail(name: string): Promise<DotDetail | null> {
  try {
    const detail = await callRest<DotDetail>(`/dots/${encodeURIComponent(name)}`)
    $activeDotDetail.set(detail)
    return detail
  } catch (err) {
    console.error(`[dotz] Failed to fetch detail for ${name}:`, err)
    return null
  }
}

export async function createDot(payload: CreateDotPayload): Promise<{ name: string; state: string; provider: string }> {
  const res = await callRest<{ name: string; state: string; provider: string }>('/dots', {
    method: 'POST',
    body: payload,
  })
  await fetchDots()
  $selectedDotName.set(res.name)
  await fetchDotDetail(res.name)
  return res
}

export async function startDot(name: string): Promise<{ status: string; state: string }> {
  const res = await callRest<{ status: string; state: string }>(`/dots/${encodeURIComponent(name)}/start`, {
    method: 'POST',
  })
  await fetchDotDetail(name)
  await fetchDots()
  return res
}

export async function stopDot(name: string): Promise<{ status: string; state: string }> {
  const res = await callRest<{ status: string; state: string }>(`/dots/${encodeURIComponent(name)}/stop`, {
    method: 'POST',
  })
  await fetchDotDetail(name)
  await fetchDots()
  return res
}

export async function assignTask(dotName: string, task: string): Promise<{ status: string; task_id: string }> {
  const res = await callRest<{ status: string; task_id: string }>(`/dots/${encodeURIComponent(dotName)}/assign`, {
    method: 'POST',
    body: { task, source: 'hermes' },
  })
  await fetchDotDetail(dotName)
  await fetchDots()
  return res
}

export async function steerDot(dotName: string, input: string): Promise<{ status: string }> {
  const res = await callRest<{ status: string }>(`/dots/${encodeURIComponent(dotName)}/steer`, {
    method: 'POST',
    body: { input },
  })
  await fetchDotDetail(dotName)
  await fetchDots()
  return res
}

export async function fetchActivity(dotName: string): Promise<DotActivityEvent[]> {
  const res = await callRest<{ activity: DotActivityEvent[] }>(`/dots/${encodeURIComponent(dotName)}/activity`)
  return res.activity || []
}

export async function fetchApprovals(dotName: string): Promise<ApprovalRequest[]> {
  const res = await callRest<{ approvals: ApprovalRequest[] }>(`/dots/${encodeURIComponent(dotName)}/approvals`)
  return res.approvals || []
}

export async function approveRequest(
  dotName: string,
  approvalId: string,
  options: { ttl_seconds?: number; max_uses?: number } = {}
): Promise<any> {
  const res = await callRest<any>(`/dots/${encodeURIComponent(dotName)}/approvals/${encodeURIComponent(approvalId)}/approve`, {
    method: 'POST',
    body: options,
  })
  await fetchDotDetail(dotName)
  return res
}

export async function denyRequest(dotName: string, approvalId: string): Promise<any> {
  const res = await callRest<any>(`/dots/${encodeURIComponent(dotName)}/approvals/${encodeURIComponent(approvalId)}/deny`, {
    method: 'POST',
    body: { approval_id: approvalId },
  })
  await fetchDotDetail(dotName)
  return res
}

export async function executeAction(
  dotName: string,
  capability: string,
  action: string,
  args: Record<string, unknown> = {}
): Promise<any> {
  const res = await callRest<any>(`/dots/${encodeURIComponent(dotName)}/action`, {
    method: 'POST',
    body: { capability, action, args },
  })
  await fetchDotDetail(dotName)
  return res
}

export async function approveGrant(
  dotName: string,
  payload: { task_id: string; session_id: string; capability: string; resources: string[]; ttl_seconds?: number; max_uses?: number }
): Promise<any> {
  const res = await callRest<any>(`/dots/${encodeURIComponent(dotName)}/grants/approve`, {
    method: 'POST',
    body: payload,
  })
  await fetchDotDetail(dotName)
  return res
}

export async function tickScheduler(): Promise<string[]> {
  const res = await callRest<{ triggered_tasks: string[] }>('/tick', { method: 'POST' })
  return res.triggered_tasks || []
}
