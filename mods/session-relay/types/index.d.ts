export type RelayRole = 'planner' | 'builder'

export type RelayPair = { partner: string; role: RelayRole }

export type RelayMessage = {
  direction: 'in' | 'out'
  peer: string
  text: string
  at: number
}

declare module 'claude-code' {
  interface PluginState {
    'session-relay': {
      pair: RelayPair | null
      inbox: RelayMessage[]
    }
  }
}
