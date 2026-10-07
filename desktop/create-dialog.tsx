import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  GlyphSpinner,
  Input,
  Textarea,
  cn,
} from '@hermes/plugin-sdk'
import { useState } from 'react'
import { createDot } from './api'
import type { ProviderType } from './types'

interface CreateDotDialogProps {
  open: boolean
  onClose: () => void
  onCreated?: (dotName: string) => void
}

export function CreateDotDialog({ open, onClose, onCreated }: CreateDotDialogProps) {
  const [provider, setProvider] = useState<ProviderType>('open-dotz')
  const [name, setName] = useState('')
  const [mission, setMission] = useState('')
  const [defaultModel, setDefaultModel] = useState('cheap')
  const [escalateModel, setEscalateModel] = useState('frontier')
  const [workspace, setWorkspace] = useState('')
  const [allowedCaps, setAllowedCaps] = useState('files.read, repo.read, repo.modify, tests.run')
  const [deniedCaps, setDeniedCaps] = useState('secrets.read, filesystem.unrestricted')
  const [schedule, setSchedule] = useState('')
  const [drexPack, setDrexPack] = useState('safe-local-coding')

  const [showAdvanced, setShowAdvanced] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const trimmedName = name.trim()
    if (!trimmedName) {
      setError('Dot name is required.')
      return
    }
    if (!mission.trim()) {
      setError('Mission statement is required.')
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      const allowList = allowedCaps
        .split(',')
        .map(s => s.trim())
        .filter(Boolean)
      const denyList = deniedCaps
        .split(',')
        .map(s => s.trim())
        .filter(Boolean)

      const res = await createDot({
        name: trimmedName,
        provider,
        mission: mission.trim(),
        default_model: defaultModel.trim(),
        escalate_model: escalateModel.trim() || undefined,
        workspace: workspace.trim() || undefined,
        capabilities_allow: provider === 'drex-dotz' ? allowList : undefined,
        capabilities_deny: provider === 'drex-dotz' ? denyList : undefined,
        schedule: schedule.trim() || undefined,
        drex_pack: provider === 'drex-dotz' ? drexPack : undefined,
      })

      setName('')
      setMission('')
      setWorkspace('')
      setSchedule('')
      onClose()
      onCreated?.(res.name)
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={isOpen => !isOpen && onClose()}>
      <DialogContent className="max-w-md p-6 bg-background text-foreground border border-border shadow-2xl rounded-xl">
        <DialogHeader className="gap-1 mb-2">
          <DialogTitle className="text-base font-bold tracking-tight">Create Persistent Dot</DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Instantiate a first-class persistent worker with dedicated state, mission, and provider boundary.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {error && (
            <div className="p-2.5 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-mono">
              {error}
            </div>
          )}

          {/* Provider Selector */}
          <div className="space-y-1.5">
            <label className="font-semibold text-foreground/90 text-xs">Dot Type / Provider</label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setProvider('open-dotz')}
                className={cn(
                  'flex flex-col items-start p-2 rounded-lg border text-left transition-all',
                  provider === 'open-dotz'
                    ? 'border-primary bg-primary/10 text-foreground font-medium'
                    : 'border-border/60 hover:border-border text-muted-foreground'
                )}
              >
                <span className="font-bold text-[11px]">Open Dot</span>
                <span className="text-[10px] opacity-75 mt-0.5">Local worker</span>
              </button>

              <button
                type="button"
                onClick={() => setProvider('drex-dotz')}
                className={cn(
                  'flex flex-col items-start p-2 rounded-lg border text-left transition-all',
                  provider === 'drex-dotz'
                    ? 'border-primary bg-primary/10 text-foreground font-medium'
                    : 'border-border/60 hover:border-border text-muted-foreground'
                )}
              >
                <span className="font-bold text-[11px]">Drex Dot</span>
                <span className="text-[10px] opacity-75 mt-0.5">Firewall-governed</span>
              </button>

              <button
                type="button"
                onClick={() => setProvider('gpt-dotz')}
                className={cn(
                  'flex flex-col items-start p-2 rounded-lg border text-left transition-all',
                  provider === 'gpt-dotz'
                    ? 'border-primary bg-primary/10 text-foreground font-medium'
                    : 'border-border/60 hover:border-border text-muted-foreground'
                )}
              >
                <span className="font-bold text-[11px]">GPT Dot</span>
                <span className="text-[10px] opacity-75 mt-0.5">Persistent assistant</span>
              </button>
            </div>
          </div>

          {/* Name */}
          <div className="space-y-1">
            <label className="font-semibold text-foreground/90">Dot Name</label>
            <Input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. Researcher, CodeReviewer, Planner"
              className="h-8 text-xs font-mono"
              autoFocus
            />
          </div>

          {/* Mission */}
          <div className="space-y-1">
            <label className="font-semibold text-foreground/90">Mission Statement</label>
            <Textarea
              value={mission}
              onChange={e => setMission(e.target.value)}
              placeholder="Define this Dot worker's persistent objective, constraints, and operational focus..."
              className="text-xs resize-none h-18"
            />
          </div>

          {/* Provider-specific: Workspace & Schedule for Open and Drex */}
          {(provider === 'open-dotz' || provider === 'drex-dotz') && (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="font-semibold text-foreground/90">Workspace (Optional)</label>
                <Input
                  value={workspace}
                  onChange={e => setWorkspace(e.target.value)}
                  placeholder="~/workspace/..."
                  className="h-8 text-xs font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-foreground/90">Schedule (Optional)</label>
                <Input
                  value={schedule}
                  onChange={e => setSchedule(e.target.value)}
                  placeholder="e.g. 15m, 1h, 0 9 * * *"
                  className="h-8 text-xs font-mono"
                />
              </div>
            </div>
          )}

          {/* Drex-specific Capabilities */}
          {provider === 'drex-dotz' && (
            <div className="space-y-3 pt-1 border-t border-border/40">
              <div className="space-y-1">
                <label className="font-semibold text-foreground/90">Allowed Capabilities</label>
                <Input
                  value={allowedCaps}
                  onChange={e => setAllowedCaps(e.target.value)}
                  placeholder="files.read, repo.read, repo.modify"
                  className="h-8 text-xs font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-foreground/90">Denied Capabilities</label>
                <Input
                  value={deniedCaps}
                  onChange={e => setDeniedCaps(e.target.value)}
                  placeholder="secrets.read, filesystem.unrestricted"
                  className="h-8 text-xs font-mono"
                />
              </div>
            </div>
          )}

          {/* Model Selection */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="font-semibold text-foreground/90">Default Model</label>
              <Input
                value={defaultModel}
                onChange={e => setDefaultModel(e.target.value)}
                placeholder={provider === 'gpt-dotz' ? 'gpt-4o-mini' : 'cheap'}
                className="h-8 text-xs font-mono"
              />
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-foreground/90">Escalate Model</label>
              <Input
                value={escalateModel}
                onChange={e => setEscalateModel(e.target.value)}
                placeholder={provider === 'gpt-dotz' ? 'gpt-4o' : 'frontier'}
                className="h-8 text-xs font-mono"
              />
            </div>
          </div>

          <DialogFooter className="mt-4 flex items-center justify-between gap-2 border-t border-border/40 pt-3">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="text-xs text-muted-foreground"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={submitting || !name.trim() || !mission.trim()}
              className="text-xs font-semibold px-4"
            >
              {submitting ? <GlyphSpinner className="size-3 mr-1" /> : null}
              Create Dot
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
