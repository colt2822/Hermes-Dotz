import type { HermesPlugin, PluginContext } from '@hermes/plugin-sdk'
import { PALETTE_AREA } from '@hermes/plugin-sdk'
import { $createDotDialogOpen, $selectedDotName, setDotzContext } from './api'
import { DotView } from './dot-view'
import { DotzPane } from './dotz-pane'

// Match the backend API plugin name so PluginContext.rest stays scoped to
// /api/plugins/dotz rather than calling an unmounted namespace.
export const ID = 'dotz'

const plugin: HermesPlugin = {
  id: ID,
  name: 'DOTZ',
  description:
    'Hermes Dotz: Persistent autonomous workers with pluggable providers (Open Dotz, Drex-governed Dotz, and GPT-backed Dotz).',
  defaultEnabled: true,
  register(ctx: PluginContext) {
    setDotzContext(ctx)

    // Register left rail pane: SESSIONS | BOTS | DOTZ
    ctx.register({
      id: 'pane',
      area: 'panes',
      title: 'DOTZ',
      data: {
        placement: 'left',
        width: '260px',
        collapsible: true,
        hideOnly: true,
        tabTitle: () => <span className="font-semibold tracking-wide">DOTZ</span>,
        tabTitleText: () => 'DOTZ',
        dock: {
          pane: 'hermes-bots:pane',
          pos: 'center',
          enforce: true,
        },
      },
      render: () => <DotzPane />,
    })

    // Register main workspace view for active Dot conversation & activity stream
    ctx.register({
      id: 'view',
      area: 'panes',
      title: 'Dot Activity',
      data: {
        placement: 'main',
        tabTitle: () => {
          const sel = $selectedDotName.get()
          return <span>{sel ? `${sel} · Dot` : 'Dot Activity'}</span>
        },
        tabTitleText: () => {
          const sel = $selectedDotName.get()
          return sel ? `${sel} · Dot` : 'Dot Activity'
        },
        dock: {
          pane: 'workspace',
          pos: 'center',
          enforce: true,
        },
      },
      render: () => <DotView />,
    })

    // Register palette command: New Dot…
    ctx.register({
      id: 'new-dot',
      area: PALETTE_AREA,
      data: {
        id: `${ID}.new-dot`,
        label: 'New Dot…',
        keywords: ['dot', 'dotz', 'worker', 'drex', 'gpt', 'autonomous', 'create'],
        run: () => {
          $createDotDialogOpen.set(true)
        },
      },
    })
  },
}

export default plugin
