# Cloud Environment Validation

Validation of the default Claude Code cloud environment for this repository.

_Last validated: 2026-09-14 — container `vm`, Linux 6.18.44-fc-v24_

## Host

| | |
|---|---|
| OS | Ubuntu 24.04.4 LTS (x86_64) |
| CPU / RAM | 4 cores / 15 GiB |
| Disk | 30 GiB available |
| User | `root` (HOME=`/root`) |
| Working dir | `/home/user/11` |

## Toolchains

| Tool | Version |
|---|---|
| git | 2.43.0 |
| node / npm | 22.22.2 / 10.9.7 |
| yarn / pnpm / bun | 1.22.22 / 10.33.0 / 1.3.11 |
| python3 / pip | 3.11.15 / 24.0 |
| uv | 0.8.17 |
| ruby | 3.3.6 |
| go | 1.24.7 |
| rustc / cargo | 1.94.1 / 1.94.1 |
| java | OpenJDK 21.0.10 (+ maven, gradle) |
| gcc / make | 13.3.0 / 4.3 |
| jq / ripgrep / curl | 1.7 / 14.1.0 / 8.5.0 |
| psql (client) | 16.13 |
| Chromium (Playwright) | 141.0.7390.37 |

Not installed: `deno`, `gh`, `sqlite3`.

## Network

Outbound HTTPS is routed through the agent proxy at `127.0.0.1:43999`
(CA bundle `/root/.ccr/ca-bundle.crt`, covers every host; git config and
SSH rewrite injected; no relay failures recorded).

Reachable:

- `api.github.com`, and `github.com` on allowed repository paths
- `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`
- `index.crates.io`, `proxy.golang.org`
- `api.anthropic.com`

Blocked by network policy (proxy returns `403` on CONNECT): general internet,
including `example.com` and `cdnjs.cloudflare.com`. Only the allowlisted hosts
above are available — plan builds and tests around package registries rather
than arbitrary downloads.

Verified working end to end: `npm install`, `pip install`, `git fetch`,
`git push`.

## Known gaps

- **No Docker daemon.** The `docker` CLI (29.3.1) is installed but
  `/var/run/docker.sock` does not exist, so containers cannot be built or run.
  Anything requiring a live daemon — testcontainers, `docker compose` — will
  fail here.
- **No database servers.** The `psql` client is present but there is no local
  PostgreSQL server, and `sqlite3` is absent (Python's `sqlite3` module still
  works).
- **`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD` is unset**, so an `npm install` of
  `@playwright/test` may attempt to re-download browsers. Chromium is already
  present at `/opt/pw-browsers` (`PLAYWRIGHT_BROWSERS_PATH` is set); export
  `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` before installing to avoid the fetch.
- **Container is ephemeral.** The repository is cloned fresh per session and
  the container is reclaimed after inactivity. Commit and push anything worth
  keeping.

## Repository

This repository currently contains only `README.md`; there is no build,
test, or lint configuration, and no `.claude/` hooks. Nothing project-specific
was validated because there is nothing yet to run.
