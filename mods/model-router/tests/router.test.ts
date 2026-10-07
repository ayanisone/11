import { describe, expect, test } from 'claude-code/testing'

import { classify } from '../hooks/register'

describe('classify', () => {
  test('simple questions go cheap', () => {
    expect(classify('what is a git rebase?').route).toBe('cheap')
    expect(classify('explain this regex: ^a+$').route).toBe('cheap')
    expect(classify('translate "hello" to French').route).toBe('cheap')
  })

  test('work and anything unsure stays on the main model', () => {
    expect(classify('fix the login bug').route).toBe('main')
    expect(classify('yes, go ahead').route).toBe('main')
    expect(classify('what is failing in the auth tests?').route).toBe('main')
    expect(classify('explain\n```ts\nconst a = 1\n```').route).toBe('main')
    expect(classify('').route).toBe('main')
  })

  test('a prefix forces the route and is stripped', () => {
    expect(classify('!cheap fix the typo in README')).toEqual({
      route: 'cheap', text: 'fix the typo in README', reason: 'forced cheap', isForced: true,
    })
    expect(classify('!main what is 2+2').route).toBe('main')
  })
})

async function stepModel($: any, on: any, turnId: string, text: string, tokens: number) {
  let seen = ''
  on('session.usage', () => ({ value: { startedAt: 0, context: { tokens, window: 200000 }, rateLimits: [] } }))
  on('turn.start', ($: any, e: any) => ({ turnId: e.turnId }))
  on('ui.status', () => ({ value: undefined }))
  on('turn.step', async function* ($: any, e: any) {
    seen = e.model

    return { turnId: e.turnId, index: e.index, answer: '', toolUses: [] }
  })
  await $.turn.start({ text, turnId })
  for await (const _ of $.turn.step({ turnId, index: 0, model: 'main-model', messageCount: 1 })) void _

  return seen
}

test('a simple prompt is sent to the cheap model', async ($, on) => {
  expect(await stepModel($, on, 't1', 'what is a monorepo?', 1000)).toBe('claude-haiku-4-5-20251001')
})

test('a work prompt keeps the main model', async ($, on) => {
  expect(await stepModel($, on, 't2', 'refactor the auth module', 1000)).toBe('main-model')
})

test('a long conversation keeps the main model', async ($, on) => {
  expect(await stepModel($, on, 't3', 'what is a monorepo?', 90000)).toBe('main-model')
})
