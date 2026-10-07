import { describe, expect, it, vi, beforeEach } from 'vitest'
import plugin from './plugin'
import {
  $dotsList,
  $selectedDotName,
  $activeDotDetail,
  $availableProviders,
  fetchDots,
  fetchDotDetail,
  fetchProviders,
  createDot,
  assignTask,
  steerDot,
  stopDot,
  startDot,
  executeAction,
  approveRequest,
  denyRequest,
  setDotzContext,
} from './api'
import type { PluginContext } from '@hermes/plugin-sdk'

describe('Hermes Dotz Plugin Core', () => {
  let registeredItems: Array<{ id: string; area: string; data?: any; title?: string }> = []
  let mockContext: PluginContext

  beforeEach(() => {
    registeredItems = []
    mockContext = {
      i18n: {
        register: vi.fn(),
        t: vi.fn((k: string) => k),
      },
      onDispose: vi.fn(),
      register: vi.fn((item: any) => {
        registeredItems.push(item)
      }),
      rest: vi.fn(),
      storage: {
        get: vi.fn(),
        set: vi.fn(),
      },
    } as unknown as PluginContext
  })

  it('declares correct plugin identity and metadata', () => {
    expect(plugin.id).toBe('dotz')
    expect(plugin.name).toBe('DOTZ')
    expect(plugin.defaultEnabled).toBe(true)
    expect(plugin.description).toContain('Open Dotz')
  })

  it('registers the top-level DOTZ rail pane center-docked to hermes-bots:pane with enforce: true', () => {
    plugin.register(mockContext)

    const railPane = registeredItems.find(i => i.id === 'pane' && i.area === 'panes')
    expect(railPane).toBeDefined()
    expect(railPane?.title).toBe('DOTZ')
    expect(railPane?.data?.dock).toEqual({
      pane: 'hermes-bots:pane',
      pos: 'center',
      enforce: true,
    })
    expect(railPane?.data?.hideOnly).toBe(true)
    expect(railPane?.data?.placement).toBe('left')
  })

  it('registers the central Dot Activity view center-docked to workspace', () => {
    plugin.register(mockContext)

    const viewPane = registeredItems.find(i => i.id === 'view' && i.area === 'panes')
    expect(viewPane).toBeDefined()
    expect(viewPane?.data?.placement).toBe('main')
    expect(viewPane?.data?.dock).toEqual({
      pane: 'workspace',
      pos: 'center',
      enforce: true,
    })
  })

  it('registers the command palette action for New Dot…', () => {
    plugin.register(mockContext)

    const paletteItem = registeredItems.find(i => i.id === 'new-dot' && i.area === 'palette')
    expect(paletteItem).toBeDefined()
    expect(paletteItem?.data?.label).toBe('New Dot…')
  })
})

describe('Hermes Dotz Multi-Provider Data Layer', () => {
  beforeEach(() => {
    $dotsList.set([])
    $selectedDotName.set(null)
    $activeDotDetail.set(null)
    $availableProviders.set([])
  })

  it('fetches provider descriptors and feature matrix', async () => {
    const mockProviders = [
      { id: 'open-dotz', name: 'Open Dot', description: 'Local', features: { drex_governance: false } },
      { id: 'drex-dotz', name: 'Drex Dot', description: 'Governed', features: { drex_governance: true } },
      { id: 'gpt-dotz', name: 'GPT Dot', description: 'Assistant', features: { tool_execution: false } },
    ]
    const mockRest = vi.fn().mockResolvedValue({ providers: mockProviders })
    setDotzContext({ rest: mockRest } as unknown as PluginContext)

    const providers = await fetchProviders()
    expect(mockRest).toHaveBeenCalledWith('/providers', expect.anything())
    expect(providers).toEqual(mockProviders)
    expect($availableProviders.get()).toEqual(mockProviders)
  })

  it('fetches dots roster across providers', async () => {
    const mockDots = [
      { name: 'ResearchWorker', state: 'RUNNING', provider: 'open-dotz' },
      { name: 'DevWorker', state: 'BLOCKED', provider: 'drex-dotz' },
      { name: 'Planner', state: 'IDLE', provider: 'gpt-dotz' },
    ]
    const mockRest = vi.fn().mockResolvedValue({ dots: mockDots })
    setDotzContext({ rest: mockRest } as unknown as PluginContext)

    const dots = await fetchDots()
    expect(mockRest).toHaveBeenCalledWith('/dots', expect.anything())
    expect(dots).toEqual(mockDots)
    expect($dotsList.get()).toEqual(mockDots)
  })

  it('creates an Open Dot and sets active selection', async () => {
    const mockRest = vi.fn()
      .mockResolvedValueOnce({ name: 'Researcher', state: 'IDLE', provider: 'open-dotz' })
      .mockResolvedValueOnce({ dots: [{ name: 'Researcher', state: 'IDLE', provider: 'open-dotz' }] })
      .mockResolvedValueOnce({ name: 'Researcher', state: 'IDLE', provider: 'open-dotz', tasks: [] })

    setDotzContext({ rest: mockRest } as unknown as PluginContext)

    const res = await createDot({
      name: 'Researcher',
      provider: 'open-dotz',
      mission: 'Literature survey',
      default_model: 'cheap',
    })

    expect(res.name).toBe('Researcher')
    expect(res.provider).toBe('open-dotz')
    expect($selectedDotName.get()).toBe('Researcher')
  })

  it('creates a GPT Dot with prompt mission and model', async () => {
    const mockRest = vi.fn()
      .mockResolvedValueOnce({ name: 'Planner', state: 'IDLE', provider: 'gpt-dotz' })
      .mockResolvedValueOnce({ dots: [{ name: 'Planner', state: 'IDLE', provider: 'gpt-dotz' }] })
      .mockResolvedValueOnce({ name: 'Planner', state: 'IDLE', provider: 'gpt-dotz', tasks: [] })

    setDotzContext({ rest: mockRest } as unknown as PluginContext)

    const res = await createDot({
      name: 'Planner',
      provider: 'gpt-dotz',
      mission: 'High-level planning',
      default_model: 'gpt-4o-mini',
    })

    expect(res.name).toBe('Planner')
    expect(res.provider).toBe('gpt-dotz')
  })

  it('handles Drex decisions: ALLOW and BLOCK', async () => {
    const allowResp = { decision: 'ALLOW', upstream_executed: true, result: 'File read' }
    const blockResp = { decision: 'BLOCK', upstream_executed: false, rule: 'POLICY_BLOCK' }

    const mockRest = vi.fn()
      .mockResolvedValueOnce(allowResp)
      .mockResolvedValueOnce({ name: 'DevWorker', state: 'RUNNING' })
      .mockResolvedValueOnce(blockResp)
      .mockResolvedValueOnce({ name: 'DevWorker', state: 'BLOCKED' })

    setDotzContext({ rest: mockRest } as unknown as PluginContext)

    const allowRes = await executeAction('DevWorker', 'files.read', 'read_file', { path: 'README.md' })
    expect(allowRes.decision).toBe('ALLOW')
    expect(allowRes.upstream_executed).toBe(true)

    const blockRes = await executeAction('DevWorker', 'secrets.read', 'read_file', { path: '~/.ssh/id_rsa' })
    expect(blockRes.decision).toBe('BLOCK')
    expect(blockRes.upstream_executed).toBe(false)
  })

  it('handles generic approval requests and denials', async () => {
    const approveResp = { status: 'approved', grant_id: 'grant_123', max_uses: 5 }
    const denyResp = { decision: 'BLOCK', upstream_executed: false }

    const mockRest = vi.fn()
      .mockResolvedValueOnce(approveResp)
      .mockResolvedValueOnce({ name: 'DevWorker', state: 'IDLE' })
      .mockResolvedValueOnce(denyResp)
      .mockResolvedValueOnce({ name: 'DevWorker', state: 'BLOCKED' })

    setDotzContext({ rest: mockRest } as unknown as PluginContext)

    const apprRes = await approveRequest('DevWorker', 'appr_01', { ttl_seconds: 300, max_uses: 5 })
    expect(apprRes.status).toBe('approved')
    expect(apprRes.grant_id).toBe('grant_123')

    const denyRes = await denyRequest('DevWorker', 'appr_02')
    expect(denyRes.decision).toBe('BLOCK')
  })
})
