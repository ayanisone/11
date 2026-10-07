import { expect, test } from 'claude-code/testing'

import { parsePair } from '../hooks/register'

test('parsePair reads partner and role', () => {
  expect(parsePair('builder-session builder')).toEqual({ partner: 'builder-session', role: 'builder' })
  expect(parsePair('other')).toEqual({ partner: 'other', role: 'planner' })
  expect(typeof parsePair('')).toBe('string')
  expect(typeof parsePair('x boss')).toBe('string')
})
