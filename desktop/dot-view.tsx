import {
  Badge,
  Button,
  cn,
  host,
  Input,
  useValue,
} from '@hermes/plugin-sdk'
import { useEffect, useRef, useState } from 'react'
import {
  $activeDotDetail,
  $selectedDotName,
  assignTask,
  executeAction,
  fetchDotDetail,
  startDot,
  steerDot,
  stopDot,
  tickScheduler,
} from './api'
import { ApprovalCard } from './approval-card'
import { DrexDecisionCard } from './drex-decision-card'
import type { DotDetail, DrexReceipt } from './types'

export function DotView() {
  const selectedName = useValue($selectedDotName)
  const detail = useValue($activeDotDetail)
  const [composerInput, setComposerInput] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [activeTab, setActiveTab] = useState<'activity' | 'receipts' | 'capabilities'>('activity')

  const scrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (selectedName) {
      void fetchDotDetail(selectedName)
      const timer = setInterval(() => {
        void fetchDotDetail(selectedName)
      }, 3000)
      return () => clearInterval(timer)
    }
  }, [selectedName])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [detail?.tasks?.length, detail?.receipts?.length, detail?.activity?.length])

  if (!selectedName || !detail) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center text-muted-foreground">
        <div className="size-12 rounded-full border border-border/50 bg-muted/20 flex items-center justify-center mb-3">
          <span className="size-3 rounded-full bg-emerald-500 animate-pulse" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">Select a Dot</h3>
        <p className="mt-1 max-w-sm text-xs">
          Select a persistent Dot from the left rail, or create a new Dot (Open Dot, Drex Dot, or GPT Dot).
        </p>
      </div>
    )
  }

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const text = composerInput.trim()
    if (!text || submitting) return

    setSubmitting(true)
    setComposerInput('')

    try {
      await assignTask(selectedName, text)
    } catch (err: unknown) {
      host.notify?.({
        kind: 'error',
        title: 'Task Assignment Failed',
        message: String(err),
      })
    } finally {
      setSubmitting(false)
    }
  }

  const handleSteer = async () => {
    const text = composerInput.trim()
    if (!text || submitting) return

    setSubmitting(true)
    setComposerInput('')

    try {
      await steerDot(selectedName, text)
      host.notify?.({
        kind: 'info',
        title: 'Dot Steered',
        message: `Steering instruction dispatched to ${selectedName}`,
      })
    } catch (err: unknown) {
      host.notify?.({ kind: 'error', message: String(err) })
    } finally {
      setSubmitting(false)
    }
  }

  const handleToggleState = async () => {
    try {
      if (detail.state === 'STOPPED') {
        await startDot(selectedName)
        host.notify?.({ kind: 'info', title: 'Dot Resumed', message: `Dot "${selectedName}" is now active.` })
      } else {
        await stopDot(selectedName)
        host.notify?.({ kind: 'info', title: 'Dot Stopped', message: `Dot "${selectedName}" transitioned to STOPPED.` })
      }
    } catch (err: unknown) {
      host.notify?.({ kind: 'error', message: String(err) })
    }
  }

  const handleTriggerTick = async () => {
    try {
      const triggered = await tickScheduler()
      host.notify?.({
        kind: 'info',
        title: 'Scheduler Ticked',
        message: triggered.length ? `Triggered: ${triggered.join(', ')}` : 'No scheduled tasks due.',
      })
    } catch (err: unknown) {
      host.notify?.({ kind: 'error', message: String(err) })
    }
  }

  const isRunning = detail.state === 'RUNNING'
  const isBlocked = detail.state === 'BLOCKED'
  const isWaiting = detail.state === 'WAITING'
  const isStopped = detail.state === 'STOPPED'

  const features = detail.features || {
    receipts: false,
    approvals: false,
    capabilities: false,
    scheduling: false,
    drex_governance: false,
  }

  return (
    <div className="flex h-full flex-col bg-background text-foreground overflow-hidden">
      {/* Header */}
      <div className="flex flex-col border-b border-border/50 bg-muted/10 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span
              className={cn(
                'size-3 rounded-full',
                isRunning && 'bg-emerald-500 animate-pulse',
                isBlocked && 'bg-rose-500',
                isWaiting && 'bg-amber-500',
                !isRunning && !isBlocked && !isWaiting && 'bg-neutral-500'
              )}
            />
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold tracking-tight">{detail.name}</h2>
                <Badge
                  variant="outline"
                  className={cn(
                    'text-[10px] font-mono uppercase tracking-wider',
                    isRunning && 'border-emerald-500/50 text-emerald-400 bg-emerald-950/20',
                    isBlocked && 'border-rose-500/50 text-rose-400 bg-rose-950/20',
                    isWaiting && 'border-amber-500/50 text-amber-400 bg-amber-950/20',
                    isStopped && 'border-neutral-500/50 text-neutral-400 bg-neutral-950/20'
                  )}
                >
                  {detail.state}
                </Badge>
                <Badge variant="secondary" className="text-[10px] font-mono">
                  {detail.provider}
                </Badge>
                <span className="text-[10px] font-mono opacity-65">
                  Governance: {detail.governance || (features.drex_governance ? 'Drex' : 'Provider-managed')}
                </span>
                {detail.models?.default && (
                  <span className="text-[10px] font-mono text-muted-foreground">
                    model: {detail.models.default}
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-xs text-muted-foreground">{detail.mission}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {features.scheduling && (
              <Button
                size="sm"
                variant="outline"
                className="text-xs h-7"
                onClick={handleTriggerTick}
              >
                Tick Scheduler
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              className={cn(
                'text-xs h-7',
                isStopped
                  ? 'text-emerald-400 border-emerald-500/30'
                  : 'text-rose-400 border-rose-500/30'
              )}
              onClick={handleToggleState}
            >
              {isStopped ? 'Resume Dot' : 'Stop Dot'}
            </Button>
          </div>
        </div>

        {/* Pending Approvals Banner */}
        {features.approvals && detail.approvals && detail.approvals.length > 0 && (
          <div className="mt-3">
            {detail.approvals.map(appr => (
              <ApprovalCard
                key={appr.approval_id}
                request={appr}
                dotName={detail.name}
                onHandled={() => void fetchDotDetail(detail.name)}
              />
            ))}
          </div>
        )}

        {/* Tabs */}
        <div className="flex items-center gap-4 mt-4 text-xs font-medium border-t border-border/30 pt-2.5">
          <button
            onClick={() => setActiveTab('activity')}
            className={cn(
              'pb-1 transition-colors border-b-2',
              activeTab === 'activity'
                ? 'border-primary text-foreground font-semibold'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            Activity Stream
          </button>

          {features.receipts && (
            <button
              onClick={() => setActiveTab('receipts')}
              className={cn(
                'pb-1 transition-colors border-b-2',
                activeTab === 'receipts'
                  ? 'border-primary text-foreground font-semibold'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              Drex Receipts ({detail.receipts?.length || 0})
            </button>
          )}

          {features.capabilities && (
            <button
              onClick={() => setActiveTab('capabilities')}
              className={cn(
                'pb-1 transition-colors border-b-2',
                activeTab === 'capabilities'
                  ? 'border-primary text-foreground font-semibold'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              Capability Scopes
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4">
        {activeTab === 'activity' && (
          <div className="space-y-3">
            {(!detail.activity || detail.activity.length === 0) &&
              (!detail.tasks || detail.tasks.length === 0) && (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  No activity recorded yet for {detail.name}. Assign a task or send instructions below.
                </div>
              )}

            {/* Normalized Activity Events */}
            {detail.activity?.map(evt => (
              <div
                key={evt.event_id}
                className="flex items-start gap-3 rounded-lg border border-border/40 bg-muted/10 p-3 text-xs"
              >
                <div className="size-2 rounded-full bg-primary mt-1.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground">{evt.title}</span>
                    <span className="text-[10px] text-muted-foreground">
                      {new Date(evt.timestamp * 1000).toLocaleTimeString()}
                    </span>
                  </div>
                  {evt.description && (
                    <p className="mt-1 text-muted-foreground text-[11px] whitespace-pre-wrap">
                      {evt.description}
                    </p>
                  )}
                </div>
              </div>
            ))}

            {/* Tasks Fallback if activity not populated */}
            {(!detail.activity || detail.activity.length === 0) &&
              detail.tasks?.map(task => (
                <div
                  key={task.task_id}
                  className="rounded-lg border border-border/50 bg-muted/10 p-3.5 text-xs"
                >
                  <div className="flex items-center justify-between font-mono text-[11px]">
                    <span className="font-semibold text-foreground">{task.title}</span>
                    <Badge variant="outline" className="text-[9px] uppercase">
                      {task.status}
                    </Badge>
                  </div>
                  {task.result && (
                    <div className="mt-2 text-[11px] text-muted-foreground bg-background/50 p-2 rounded border border-border/30 font-mono">
                      {task.result}
                    </div>
                  )}
                </div>
              ))}
          </div>
        )}

        {activeTab === 'receipts' && features.receipts && (
          <div className="space-y-2">
            {(!detail.receipts || detail.receipts.length === 0) && (
              <div className="p-8 text-center text-xs text-muted-foreground">
                No Drex capability receipts recorded yet.
              </div>
            )}
            {detail.receipts?.map(rcpt => (
              <DrexDecisionCard key={rcpt.receipt_id} receipt={rcpt} dotName={detail.name} />
            ))}
          </div>
        )}

        {activeTab === 'capabilities' && features.capabilities && (
          <div className="space-y-4">
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-4">
              <h4 className="font-semibold text-emerald-400 text-xs mb-2">Allowed Capabilities</h4>
              <div className="flex flex-wrap gap-1.5">
                {detail.capabilities?.allow?.map(c => (
                  <Badge key={c} variant="outline" className="font-mono text-[11px] border-emerald-500/40 text-emerald-300">
                    {c}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-rose-500/30 bg-rose-500/5 p-4">
              <h4 className="font-semibold text-rose-400 text-xs mb-2">Explicitly Denied Capabilities</h4>
              <div className="flex flex-wrap gap-1.5">
                {detail.capabilities?.deny?.map(c => (
                  <Badge key={c} variant="destructive" className="font-mono text-[11px]">
                    {c}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="p-4 border-t border-border/50 bg-muted/10">
        <form onSubmit={handleSend} className="flex items-center gap-2">
          <Input
            value={composerInput}
            onChange={e => setComposerInput(e.target.value)}
            placeholder={`Instruct or assign obligation to ${detail.name}...`}
            className="text-xs h-9"
            disabled={submitting || isStopped}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-9 text-xs"
            disabled={submitting || !composerInput.trim() || isStopped}
            onClick={handleSteer}
          >
            Steer
          </Button>
          <Button
            type="submit"
            size="sm"
            className="h-9 text-xs px-4 font-semibold"
            disabled={submitting || !composerInput.trim() || isStopped}
          >
            Assign Task
          </Button>
        </form>
      </div>
    </div>
  )
}
