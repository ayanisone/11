import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { DashAgent, DashEvent, DashNote, DashUsage } from '../types'

const PANE = 'agent-dashboard'
const agents = atom({ plugin: 'agent-dashboard', key: 'agents' } as const, [])
const events = atom({ plugin: 'agent-dashboard', key: 'events' } as const, [])
const usage = atom({ plugin: 'agent-dashboard', key: 'usage' } as const, null)
const notes = atom({ plugin: 'agent-dashboard', key: 'notes' } as const, [])

const STATUS_MARK: Record<string, string> = {
  running: '●',
  pending: '◌',
  waiting: '◐',
  idle: '○',
  completed: '✓',
  failed: '✗',
  killed: '✗',
}

export function clip(text: string, width: number): string {
  const line = text.replace(/\s+/g, ' ').trim()

  return line.length > width ? `${line.slice(0, Math.max(0, width - 1))}…` : line
}

function ago(now: number, at: number): string {
  const s = Math.max(0, Math.round((now - at) / 1000))

  return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`
}

async function log($: EngineInterface, who: string, what: string) {
  const event: DashEvent = { at: await $.clock.now(), who, what }
  await update($, events, list => [...list, event].slice(-100))
}

const names = new Map<string, string>()

async function refresh($: EngineInterface) {
  const list = await $.agent.list()
  for (const a of list) names.set(a.id, a.description || a.type)
  const next: DashAgent[] = list.map(a => ({ id: a.id, description: a.description, type: a.type, status: a.status }))
  await update($, agents, () => next)

  const u = await $.session.usage()
  const snapshot: DashUsage = {
    model: await $.session.model(),
    costUsd: u.cost?.usd ?? 0,
    contextPercent: u.context.percent ?? 0,
    turns: await $.session.turns(),
  }
  await update($, usage, () => snapshot)
}

async function refreshNotes($: EngineInterface, notesDir: string) {
  if (!notesDir) return
  const entries = await $.fs.list(notesDir).catch(() => [])
  const newest: DashNote[] = entries
    .filter(f => f.kind === 'file' && !f.name.startsWith('.'))
    .sort((a, b) => b.mtimeMs - a.mtimeMs)
    .slice(0, 6)
    .map(f => ({ name: f.name, mtimeMs: f.mtimeMs }))
  await update($, notes, () => newest)
}

export const register: Register = (on, options) => {
  const notesDir = typeof options.notesDir === 'string' ? options.notesDir.trim() : ''

  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'dashboard', description: 'Open the live agent / session dashboard pane' })
    await refresh($)
    await refreshNotes($, notesDir)
    $.clock.every(2000, () => void refresh($).catch(() => undefined))
    $.clock.every(30000, () => void refreshNotes($, notesDir).catch(() => undefined))

    return next(e)
  })

  on('command.run', { command: 'dashboard' }, async $ => {
    await $.ui.open({ id: PANE, title: 'Dashboard' })

    return { text: 'Dashboard opened.' }
  })

  on('tool.call', async ($, e, next) => {
    const who = e.agentId ? names.get(e.agentId) ?? e.agentId.slice(0, 8) : 'main'
    await log($, who, e.tool)

    return next(e)
  })

  on('session.send', async ($, e, next) => {
    const sent = await next(e)
    await log($, 'main', `→ ${e.to}${sent.isDelivered ? '' : ' (not delivered)'}: ${e.text}`)

    return sent
  })

  on('session.receive', async ($, e, next) => {
    if (e.agentId === undefined) await log($, 'inbox', `← ${e.text}`)

    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const width = Math.max(20, e.props.bodyColumns ?? e.viewport?.columns ?? 60)
    const rows = Math.max(10, (e.viewport?.rows ?? 30) - 4)
    const now = await $.clock.now()
    const agentList = await read($, agents)
    const eventList = await read($, events)
    const u = await read($, usage)
    const noteList = await read($, notes)
    const live = agentList.filter(a => a.status !== 'completed' && a.status !== 'killed')
    const shownAgents = (live.length > 0 ? live : agentList).slice(-6)
    const room = Math.max(3, rows - shownAgents.length - noteList.length - 9)

    return (
      <Box flexDirection="column">
        <Text bold>Session</Text>
        <Text dimColor>
          {u
            ? clip(`${u.model} · $${u.costUsd.toFixed(2)} · context ${u.contextPercent}% · ${u.turns} turns`, width)
            : 'reading…'}
        </Text>
        <Text bold>Agents ({live.length} live / {agentList.length})</Text>
        {shownAgents.length === 0 && <Text dimColor>none yet</Text>}
        {shownAgents.map(a => (
          <Text dimColor={a.status === 'completed'}>
            {clip(`${STATUS_MARK[a.status] ?? '?'} ${a.status.padEnd(9)} ${a.description || a.type}`, width)}
          </Text>
        ))}
        <Text bold>Activity</Text>
        {eventList.length === 0 && <Text dimColor>no tool calls yet</Text>}
        {eventList.slice(-room).map(ev => (
          <Text>{clip(`${ago(now, ev.at).padStart(3)} ${ev.who}: ${ev.what}`, width)}</Text>
        ))}
        {notesDir !== '' && <Text bold>Notes</Text>}
        {noteList.map(n => (
          <Text dimColor>{clip(`${ago(now, n.mtimeMs).padStart(3)} ${n.name}`, width)}</Text>
        ))}
      </Box>
    )
  })
}
