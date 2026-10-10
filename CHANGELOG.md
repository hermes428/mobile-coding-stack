# Changelog

## 1.0.0 — 2026-10-10
First release. A Claude Code port of Lean Build Mode v4.0, designed for mobile cloud sessions.

- Main session orchestrates and implements. Two read-only subagents: `architect` (Opus) and `verifier` (Sonnet, with deep mode replacing v4.0's Advanced Verification agent).
- Hook-enforced gates: contract approval (hash-bound), allowed/forbidden files, 3-cycle cap, verify-before-stop, PASS-before-merge.
- Contract file with executable `checks`, plus base commit recorded at approval for diffs and rollback.
- Conditional skills for scientific rigor and capability provisioning.
- Auto-logged lessons file for evidence-based v2 changes.
- Delivered as a template + installer, because cloud sessions don't install plugins.
- Dropped from the v1 plan: the Codex cross-check (cloud network limits) and a plugin package.
