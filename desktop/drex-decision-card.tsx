import { Badge, cn } from '@hermes/plugin-sdk'
import type { DrexReceipt } from './types'

interface DrexDecisionCardProps {
  receipt: DrexReceipt
  dotName: string
}

export function DrexDecisionCard({ receipt, dotName }: DrexDecisionCardProps) {
  const isBlock = receipt.decision === 'BLOCK'
  const isGrant = receipt.decision === 'GRANT'
  const isAllow = receipt.decision === 'ALLOW'

  return (
    <div
      className={cn(
        'my-1.5 rounded-lg border p-3 text-xs transition-colors',
        isBlock && 'border-rose-500/40 bg-rose-500/10 text-rose-200',
        isAllow && 'border-emerald-500/30 bg-emerald-500/10 text-emerald-100',
        isGrant && 'border-amber-500/40 bg-amber-500/10 text-amber-100'
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {isBlock && (
            <Badge variant="destructive" className="font-mono text-[10px] tracking-wide uppercase font-bold">
              Drex BLOCK
            </Badge>
          )}
          {isAllow && (
            <Badge
              variant="outline"
              className="font-mono text-[10px] tracking-wide uppercase border-emerald-500/50 text-emerald-400 font-bold bg-emerald-950/40"
            >
              Drex ALLOW
            </Badge>
          )}
          {isGrant && (
            <Badge
              variant="outline"
              className="font-mono text-[10px] tracking-wide uppercase border-amber-500/50 text-amber-300 font-bold bg-amber-950/40"
            >
              Drex GRANT
            </Badge>
          )}
          <span className="font-mono font-medium">{receipt.capability}</span>
        </div>
        <span className="text-[10px] opacity-60">
          {receipt.ts ? new Date(receipt.ts * 1000).toLocaleTimeString() : 'now'}
        </span>
      </div>

      <div className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[11px] font-mono">
        {receipt.target && (
          <>
            <span className="opacity-60">target:</span>
            <span className="truncate">{receipt.target}</span>
          </>
        )}
        {receipt.action && (
          <>
            <span className="opacity-60">action:</span>
            <span>{receipt.action}</span>
          </>
        )}
        {isBlock && (
          <>
            <span className="opacity-60 text-rose-300 font-semibold">upstream executions:</span>
            <span className="text-rose-300 font-bold">0</span>
          </>
        )}
        {receipt.reason && (
          <>
            <span className="opacity-60">reason:</span>
            <span>{receipt.reason}</span>
          </>
        )}
        {receipt.rule && (
          <>
            <span className="opacity-60">rule:</span>
            <span>{receipt.rule}</span>
          </>
        )}
        {isGrant && receipt.grant_id && (
          <>
            <span className="opacity-60">grant ID:</span>
            <span className="truncate">{receipt.grant_id}</span>
          </>
        )}
      </div>
    </div>
  )
}
