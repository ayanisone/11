import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { RelayMessage, RelayPair, RelayRole } from '../types'

const pair = atom({ plugin: 'session-relay', key: 'pair' } as const, null)
const inbox = atom({ plugin: 'session-relay', key: 'inbox' } as const, [])

const COMMANDS = [
  {
    name: 'peers',
    description: 'List the other Claude sessions and agents this one can message',
  },
  {
    name: 'pair',
    description: 'Pair with another session: /pair <session> [planner|builder]',
    argumentHint: '<session> [planner|builder]',
  },
  {
    name: 'send',
    description: 'Send a message to a session: /send <session> <text> (session optional once paired)',
    argumentHint: '[session] <text>',
  },
  {
    name: 'handoff',
    description: "Send this session's last answer (the plan, or the build report) to the paired session",
    argumentHint: '[note]',
  },
  {
    name: 'inbox',
    description: 'Show the messages this session sent and received',
  },
]

const HANDOFF_HEADER: Record<RelayRole, string> = {
  planner: 'HANDOFF FROM PLANNER: build the plan below, then /handoff the result back.',
  builder: 'HANDOFF FROM BUILDER: here is what was built; review it and send the next step.',
}

export function parsePair(args: string): RelayPair | string {
  const [partner, role = 'planner'] = args.trim().split(/\s+/)
  if (!partner) return 'Usage: /pair <session> [planner|builder]'
  if (role !== 'planner' && role !== 'builder') return `Role must be planner or builder, not "${role}".`

  return { partner, role }
}

async function record($: EngineInterface, message: RelayMessage) {
  await update($, inbox, list => [...list, message].slice(-50))
}

async function deliver($: EngineInterface, to: string, text: string) {
  const sent = await $.session.send({ to, text })
  if (!sent.isDelivered) return `Not delivered to ${to}: ${sent.reason}`
  await record($, { direction: 'out', peer: to, text, at: await $.clock.now() })

  return `Sent to ${to}.`
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    for (const spec of COMMANDS) await $.command.register(spec)

    return next(e)
  })

  on('command.run', { command: 'peers' }, async $ => {
    const listed = await $.tool.call({ tool: 'ListAgents' })

    return { text: 'text' in listed && listed.text ? listed.text : 'No peers found.' }
  })

  on('command.run', { command: 'pair' }, async ($, e) => {
    const parsed = parsePair(e.args)
    if (typeof parsed === 'string') return { text: parsed }
    await update($, pair, () => parsed)
    $.ui.status(`relay: ${parsed.role} ⇄ ${parsed.partner}`)

    return { text: `Paired with ${parsed.partner}; this session is the ${parsed.role}.` }
  })

  on('command.run', { command: 'send' }, async ($, e) => {
    const paired = await read($, pair)
    const [first = '', ...rest] = e.args.trim().split(/\s+/)
    const to = rest.length > 0 || !paired ? first : paired.partner
    const text = rest.length > 0 || !paired ? rest.join(' ') : e.args.trim()
    if (!to || !text) return { text: 'Usage: /send <session> <text>' }

    return { text: await deliver($, to, text) }
  })

  on('command.run', { command: 'handoff' }, async ($, e) => {
    const paired = await read($, pair)
    if (!paired) return { text: 'Pair first: /pair <session> [planner|builder]' }
    const rows = await $.session.messages({})
    if (!Array.isArray(rows)) return { text: 'Could not read this conversation.' }
    const last = [...rows].reverse().find(row => row.role === 'assistant' && row.text.trim())
    if (!last) return { text: 'Nothing to hand off yet: no answer in this session.' }
    const note = e.args.trim()
    const text = [HANDOFF_HEADER[paired.role], note && `Note: ${note}`, '', last.text]
      .filter(line => line !== '')
      .join('\n')

    return { text: await deliver($, paired.partner, text) }
  })

  on('command.run', { command: 'inbox' }, async $ => {
    const list = await read($, inbox)
    if (list.length === 0) return { text: 'No messages yet.' }
    const lines = list.map(m => `${m.direction === 'in' ? '←' : '→'} ${m.peer}: ${(m.text.split('\n')[0] ?? '').slice(0, 100)}`)

    return { text: lines.join('\n') }
  })

  on('session.receive', async ($, e, next) => {
    const isPeer = e.agentId === undefined && 'kind' in e.origin && (e.origin.kind === 'peer' || e.origin.kind === 'peer-send-message')
    if (isPeer) {
      const preview = e.text.split('\n').find(line => line.trim()) ?? ''
      await record($, { direction: 'in', peer: 'peer', text: e.text, at: await $.clock.now() })
      $.ui.toast(`📨 ${preview.slice(0, 80)}`)
    }

    return next(e)
  })
}
