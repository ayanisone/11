# Claude Code mods

Three mods (function-hook plugins) for Claude Code.

| Mod | What it does | Commands |
| --- | --- | --- |
| `session-relay` | Pair two sessions so one plans while the other builds, and pass work between them | `/peers`, `/pair <session> [planner\|builder]`, `/handoff [note]`, `/send [session] <text>`, `/inbox` |
| `agent-dashboard` | A live pane: session cost/context, agents and their status, tool activity, messages between sessions, and the newest files in your notes folder | `/dashboard` |
| `model-router` | Sends simple look-up prompts to a cheaper model (default Claude Haiku 4.5); anything that asks for work stays on your main model | `/route on\|off\|status`; prefix a prompt with `!cheap` or `!main` to force it |

## Install

In a terminal Claude Code session:

```
/plugin install session-relay --marketplace ayanisone/11
/plugin install agent-dashboard --marketplace ayanisone/11
/plugin install model-router --marketplace ayanisone/11
```

Answer `y` to add the marketplace, then pick a scope (user scope = every session).

## Settings

Set in `/config` once installed:

- `agent-dashboard` → **Notes folder**: absolute path of your notes / second-brain folder.
- `model-router` → **Cheap model** (default `claude-haiku-4-5-20251001`) and **Max context for routing** (default 60000 tokens; past it the router stays on the main model, because switching models drops the prompt cache).

## Planner / builder workflow

1. Open two sessions. In the planner: `/pair <builder-session> planner`. In the builder: `/pair <planner-session> builder`. (`/peers` lists the names.)
2. Plan in the planner, then `/handoff`: its last answer goes to the builder as a message.
3. The builder works, then `/handoff` sends its report back.
