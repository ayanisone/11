export type DashAgent = { id: string; description: string; type: string; status: string }

export type DashEvent = { at: number; who: string; what: string }

export type DashUsage = { model: string; costUsd: number; contextPercent: number; turns: number }

export type DashNote = { name: string; mtimeMs: number }

declare module 'claude-code' {
  interface PluginState {
    'agent-dashboard': {
      agents: DashAgent[]
      events: DashEvent[]
      usage: DashUsage | null
      notes: DashNote[]
    }
  }
}
