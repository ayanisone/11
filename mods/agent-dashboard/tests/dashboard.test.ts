import { expect, test } from 'claude-code/testing'

import { clip } from '../hooks/register'

test('clip keeps lines inside the pane', () => {
  expect(clip('short', 20)).toBe('short')
  expect(clip('a  b\n c', 20)).toBe('a b c')
  expect(clip('0123456789abc', 10)).toBe('012345678…')
})
