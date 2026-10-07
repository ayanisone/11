export type RouterMode = 'auto' | 'off'

export type RouterStats = { cheap: number; main: number; last: string }

declare module 'claude-code' {
  interface PluginState {
    'model-router': {
      mode: RouterMode
      stats: RouterStats
    }
  }
}
