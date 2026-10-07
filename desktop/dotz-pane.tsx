import {
  Button,
  GlyphSpinner,
  cn,
  host,
  useValue,
} from '@hermes/plugin-sdk'
import { useEffect } from 'react'
import {
  $createDotDialogOpen,
  $dotsList,
  $dotzLoading,
  $selectedDotName,
  fetchDotDetail,
  fetchDots,
} from './api'
import { CreateDotDialog } from './create-dialog'

export function DotzPane() {
  const dots = useValue($dotsList)
  const selected = useValue($selectedDotName)
  const loading = useValue($dotzLoading)
  const createDialogOpen = useValue($createDotDialogOpen)

  useEffect(() => {
    void fetchDots()
    const timer = setInterval(() => {
      void fetchDots()
    }, 4000)
    return () => clearInterval(timer)
  }, [])

  // Auto-select first dot if none selected
  useEffect(() => {
    if (!selected && dots.length > 0) {
      $selectedDotName.set(dots[0].name)
      void fetchDotDetail(dots[0].name)
    }
  }, [dots, selected])

  const handleSelectDot = (name: string) => {
    $selectedDotName.set(name)
    void fetchDotDetail(name)
    host.revealPane?.('dotz:view')
  }

  return (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground select-none overflow-hidden">
      {/* Header with Title and + New Dot button */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-sidebar-border">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-xs tracking-wider uppercase text-foreground/80">
            Dotz
          </span>
          {loading && <GlyphSpinner className="size-2.5 text-muted-foreground" />}
        </div>
        <Button
          size="sm"
          variant="outline"
          className="h-6 px-2 text-[11px] gap-1 font-medium bg-background/50 hover:bg-background"
          onClick={() => $createDotDialogOpen.set(true)}
        >
          <span>+ New Dot</span>
        </Button>
      </div>

      {/* Dot List */}
      <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
        {dots.length === 0 && !loading && (
          <div className="p-4 text-center text-xs text-muted-foreground">
            No Dotz found.
            <div className="mt-2">
              <Button
                size="sm"
                variant="ghost"
                className="text-xs text-primary"
                onClick={() => $createDotDialogOpen.set(true)}
              >
                + Create your first Dot
              </Button>
            </div>
          </div>
        )}

        {dots.map(dot => {
          const isSelected = selected === dot.name
          const stateUpper = (dot.state || 'IDLE').toUpperCase()
          const isRunning = stateUpper === 'RUNNING'
          const isBlocked = stateUpper === 'BLOCKED'
          const isWaiting = stateUpper === 'WAITING'

          // Color indicators
          const dotColor = isRunning
            ? 'bg-emerald-500 shadow-xs shadow-emerald-500/50'
            : isBlocked
            ? 'bg-rose-500 shadow-xs shadow-rose-500/50'
            : isWaiting
            ? 'bg-amber-500'
            : 'bg-muted-foreground/60'

          const providerShort = dot.provider?.toLowerCase().includes('drex')
            ? 'DREX'
            : dot.provider?.toLowerCase().includes('gpt')
            ? 'GPT'
            : 'OPEN'

          return (
            <div
              key={dot.name}
              onClick={() => handleSelectDot(dot.name)}
              className={cn(
                'group relative flex flex-col gap-0.5 rounded-md px-2.5 py-2 text-xs transition-colors cursor-pointer',
                isSelected
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium shadow-xs'
                  : 'hover:bg-sidebar-accent/50 text-sidebar-foreground'
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <span className={cn('size-2 rounded-full shrink-0 transition-transform group-hover:scale-125', dotColor)} />
                  <span className="truncate font-semibold text-[13px]">{dot.name}</span>
                  <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-muted/60 text-muted-foreground border border-border/40">
                    {providerShort}
                  </span>
                </div>
                <span
                  className={cn(
                    'text-[10px] font-mono tracking-tight shrink-0',
                    isRunning && 'text-emerald-500 dark:text-emerald-400 font-semibold',
                    isBlocked && 'text-rose-500 dark:text-rose-400 font-semibold',
                    isWaiting && 'text-amber-500 dark:text-amber-400',
                    !isRunning && !isBlocked && !isWaiting && 'text-muted-foreground'
                  )}
                >
                  {stateUpper}
                </span>
              </div>

              {/* Sub-label: task / schedule / blocked status */}
              <div className="flex items-center justify-between text-[11px] text-muted-foreground pl-4">
                <span className="truncate max-w-[170px]">
                  {isBlocked
                    ? dot.blocked_reason || 'Needs capability approval'
                    : isRunning
                    ? dot.last_task || 'Active task'
                    : dot.next_wake
                    ? `Scheduled ${dot.next_wake}`
                    : dot.mission || 'Persistent worker'}
                </span>
                {dot.task_count !== undefined && dot.task_count > 0 && (
                  <span className="text-[10px] font-mono opacity-60">#{dot.task_count}</span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Creation Modal Dialog */}
      <CreateDotDialog
        open={createDialogOpen}
        onClose={() => $createDotDialogOpen.set(false)}
        onCreated={name => {
          $selectedDotName.set(name)
          void fetchDotDetail(name)
          host.revealPane?.('dotz:view')
        }}
      />
    </div>
  )
}
