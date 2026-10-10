---
name: capability-provisioning
description: Use when a task needs a tool, package, credential, network domain, MCP server, or data access that isn't verified in this session. Proposes a separate provisioning contract instead of silently installing or authenticating.
---

# Capability provisioning

First ask whether this task needs the capability right now. If not, ignore it.

If it does, verify it with a harmless operation in this session (a version command, read-only call, or dry run). Configuration being present doesn't prove the capability works.

## Ladder (stop at the first that works)
1. A capability already enabled in this session
2. A built-in or pre-installed tool (cloud sessions ship Python, Node, git, gh, jq, Docker, Postgres, Redis)
3. A small project-local helper script, inside the contract's allowed_files
4. A repo-committed skill or `.mcp.json` entry (project scope only)
5. Otherwise `BLOCKED`, naming the exact action the user must take (environment setup script, network allowlist, secret, GitHub access)

## Provisioning contract
Provisioning is its own contract (id suffix `-cap`), approved separately from feature work. It covers:
- capability needed and the existing options considered
- mechanism, provider/source, and pinned version
- scope (project only, by default), persistence, and the files, settings, and commands touched
- dependencies added, permissions, data exposure, and trust implications
- smoke test (becomes the `checks` entry) and rollback steps
- host actions the agent can't do (for example, editing the cloud environment's setup script or network access in the Claude app)

## Never silently
Install or trust software, authenticate, add credentials, widen network access, change global or profile settings, execute downloaded code, or commit secrets.
