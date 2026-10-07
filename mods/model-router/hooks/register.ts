import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { RouterMode } from '../types'

const mode = atom({ plugin: 'model-router', key: 'mode' } as const, 'auto')
const stats = atom({ plugin: 'model-router', key: 'stats' } as const, { cheap: 0, main: 0, last: '' })

export type Route = 'cheap' | 'main'

// Words that mean "change something" or "think hard": always the main model.
const HARD = /\b(fix|add|change|update|write|create|make|delete|remove|implement|refactor|debug|architect\w*|design|migrat\w*|optimi[sz]e|security|vulnerab\w*|race|deadlock|concurren\w*|why|fails?|failing|error|exception|stack ?trace|build|test(s|ing)?|review|plan|deploy|commit|push|merge)\b/i
// Look-ups and rewording: safe for the cheap model.
const EASY = /^(what('s| is| are| does)|who|when|where|which|define|explain|list|show|summari[sz]e|translate|reword|rephrase|spell|convert|how do (i|you)|what's the (command|flag|syntax))\b/i

/** Decides one prompt's route: forced by a `!cheap` / `!main` prefix, else by shape. Anything unsure stays on main. */
export function classify(text: string): { route: Route; text: string; reason: string; isForced: boolean } {
  const forced = /^!(cheap|main)\s+/i.exec(text)
  if (forced) {
    const route = forced[1]!.toLowerCase() as Route

    return { route, text: text.slice(forced[0].length), reason: `forced ${route}`, isForced: true }
  }
  const body = text.trim()
  if (body === '') return { route: 'main', text, reason: 'continuation', isForced: false }
  if (body.includes('```') || body.length > 280) return { route: 'main', text, reason: 'long or has code', isForced: false }
  if (HARD.test(body)) return { route: 'main', text, reason: 'asks for work', isForced: false }
  if (EASY.test(body)) return { route: 'cheap', text, reason: 'simple question', isForced: false }

  return { route: 'main', text, reason: 'unsure', isForced: false }
}

export const register: Register = (on, options) => {
  const cheapModel = typeof options.cheapModel === 'string' && options.cheapModel ? options.cheapModel : 'claude-haiku-4-5-20251001'
  const maxContext = typeof options.maxContextTokens === 'number' ? options.maxContextTokens : 60000
  // turnId -> route; a `!cheap` / `!main` prefix is parked in `forced` between prompt.submit and turn.start
  const routes = new Map<string, Route>()
  let forced: Route | undefined

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'route',
      description: 'Model router: /route on | off | status',
      argumentHint: 'on|off|status',
    })

    return next(e)
  })

  on('command.run', { command: 'route' }, async ($, e) => {
    const arg = e.args.trim().toLowerCase()
    if (arg === 'on' || arg === 'off') {
      const next: RouterMode = arg === 'on' ? 'auto' : 'off'
      await update($, mode, () => next)
      $.ui.status(arg === 'off' ? undefined : 'router: auto')

      return { text: `Model router ${arg}.` }
    }
    const s = await read($, stats)
    const m = await read($, mode)

    return {
      text: `Router ${m === 'auto' ? 'on' : 'off'} · cheap model ${cheapModel} · under ${maxContext} context tokens\n` +
        `Turns routed: ${s.cheap} cheap, ${s.main} main${s.last ? ` · last: ${s.last}` : ''}`,
    }
  })

  on('prompt.submit', async ($, e, next) => {
    const decided = classify(e.text)
    if (!decided.isForced) return next(e)
    forced = decided.route

    return next({ ...e, text: decided.text })
  })

  on('turn.start', async ($, e, next) => {
    const decided = forced ? { route: forced, reason: `forced ${forced}`, isForced: true } : classify(e.text)
    forced = undefined
    const isOff = (await read($, mode)) === 'off'
    let route: Route = isOff && !decided.isForced ? 'main' : decided.route
    let reason = isOff && !decided.isForced ? 'router off' : decided.reason
    if (route === 'cheap' && !decided.isForced) {
      const tokens = (await $.session.usage()).context.tokens ?? 0
      if (tokens > maxContext) {
        route = 'main'
        reason = `context ${tokens} > ${maxContext}`
      }
    }
    routes.set(e.turnId, route)
    await update($, stats, s => ({
      cheap: s.cheap + (route === 'cheap' ? 1 : 0),
      main: s.main + (route === 'main' ? 1 : 0),
      last: `${route} (${reason})`,
    }))
    $.ui.status(route === 'cheap' ? `router: → ${cheapModel} (${reason})` : 'router: main model')

    return next(e)
  })

  on('turn.step', async function* ($, e, next) {
    const isCheap = e.agentId === undefined && routes.get(e.turnId) === 'cheap'

    return yield* next(isCheap ? { ...e, model: cheapModel, effort: undefined } : e)
  })

  on('turn.complete', async ($, e, next) => {
    if (e.agentId === undefined) routes.delete(e.turnId)

    return next(e)
  })
}
