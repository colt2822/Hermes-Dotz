import { Badge, Button, cn, host } from '@hermes/plugin-sdk'
import { useState } from 'react'
import { approveRequest, denyRequest } from './api'
import type { ApprovalRequest } from './types'

interface ApprovalCardProps {
  request: ApprovalRequest
  dotName: string
  onHandled?: () => void
}

export function ApprovalCard({ request, dotName, onHandled }: ApprovalCardProps) {
  const [acting, setActing] = useState(false)
  const isDrex = request.provider.includes('drex')

  const handleApprove = async () => {
    setActing(true)
    try {
      await approveRequest(dotName, request.approval_id, {
        ttl_seconds: 300,
        max_uses: 5,
      })
      host.notify?.({
        kind: 'info',
        title: isDrex ? 'Drex Grant Issued' : 'Action Authorized',
        message: `Approved ${request.action} on ${request.target || 'resource'}`,
      })
      onHandled?.()
    } catch (err: unknown) {
      host.notify?.({ kind: 'error', message: String(err) })
    } finally {
      setActing(false)
    }
  }

  const handleDeny = async () => {
    setActing(true)
    try {
      await denyRequest(dotName, request.approval_id)
      host.notify?.({
        kind: 'warning',
        title: 'Action Denied',
        message: `Denied ${request.action} on ${request.target || 'resource'}`,
      })
      onHandled?.()
    } catch (err: unknown) {
      host.notify?.({ kind: 'error', message: String(err) })
    } finally {
      setActing(false)
    }
  }

  return (
    <div className="my-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3.5 text-xs text-amber-200 shadow-xs">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className="font-mono text-[10px] tracking-wide uppercase border-amber-500/50 text-amber-300 font-bold bg-amber-950/40"
          >
            {isDrex ? 'Drex Approval Request' : 'Action Authorization'}
          </Badge>
          <span className="font-mono font-medium">{request.scope || request.capability}</span>
        </div>
        <span className="text-[10px] opacity-70">
          {request.created_at ? new Date(request.created_at * 1000).toLocaleTimeString() : 'pending'}
        </span>
      </div>

      <div className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 font-mono text-[11px]">
        <span className="opacity-60">Action:</span>
        <span className="font-semibold text-amber-100">{request.action}</span>

        {request.target && (
          <>
            <span className="opacity-60">Target:</span>
            <span className="truncate">{request.target}</span>
          </>
        )}

        {request.description && (
          <>
            <span className="opacity-60">Summary:</span>
            <span>{request.description}</span>
          </>
        )}
      </div>

      <div className="mt-3 flex items-center justify-end gap-2">
        <Button
          size="sm"
          variant="outline"
          disabled={acting}
          className="h-7 text-xs border-amber-500/40 text-rose-300 hover:bg-rose-950/30"
          onClick={handleDeny}
        >
          Deny
        </Button>
        <Button
          size="sm"
          disabled={acting}
          className="h-7 text-xs bg-amber-600 hover:bg-amber-500 text-white font-medium"
          onClick={handleApprove}
        >
          {isDrex ? 'Issue Bounded Grant (300s)' : 'Approve Action'}
        </Button>
      </div>
    </div>
  )
}
