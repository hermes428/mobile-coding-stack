# Mobile Coding Stack v1

A lean, hook-enforced agent workflow for Claude Code, built to run from the Claude mobile app (cloud sessions). It's the successor to Lean Build Mode v4.0 (VS Code + Copilot).

```
Understand enough → one bounded contract → you type "approve" → smallest correct change → independent verification → stop when evidence runs out
```

The difference from v4.0: the key rules are **enforced by hooks**, not just requested in prompts.

| Rule | How it's enforced |
|---|---|
| No code edits without an approved contract | `PreToolUse` hook denies Edit/Write until you type `approve` |
| Stay in scope | Edits outside `allowed_files` (or inside `forbidden_files`) are denied |
| Scope change needs re-approval | Approval is bound to a hash of the contract; editing it re-locks edits |
| Max 3 edit-and-check cycles | Hook counts edit → check runs; the 4th edit is denied. Re-approving the same contract doesn't reset it |
| Verification before done | `Stop` hook won't let Claude finish with unverified edits |
| Independent verifier | Separate read-only subagent (different model, fresh context, reads the evidence before the claims) |
| PASS before merge to main | `gh pr merge` / `git merge` / push to main denied without a current PASS |
| Audit trail | `.claude/stack/state.json` records approval hash, base commit, cycles, and verdict, and is committed with the PR |
| Learn from failures | FAIL/BLOCKED verdicts and cycle-cap hits auto-append to `.mcs/lessons.md` |

## What's in a project after install

```
.claude/
  settings.json            hooks (merged into your existing settings)
  agents/architect.md      read-only planner (Opus) for Full Understanding and replans
  agents/verifier.md       read-only verifier (Sonnet), plus deep mode for one hard question
  skills/build/            /build: route Fast vs Full → contract → approve → implement → verify
  skills/verify/           /verify, /verify deep <question>
  skills/status/           /status: five-line state
  skills/scientific-rigor/ loaded only when units/calibration/models/statistics are touched
  skills/capability-provisioning/  no silent installs or auth
  stack/hooks/stack.py     the hook engine (stdlib Python, no dependencies)
  stack/governance.md      rules injected at session start
  stack/state.json         written only by hooks
.mcs/
  contract.md              the current contract (one phone screen)
  lessons.md               failure log, your evidence for v2
  archive/                 finished contracts
```

The working files live in `.mcs/` because Claude Code treats `.claude/` as a protected folder that prompts on every write. The machinery staying in `.claude/` is a feature: Claude can't quietly edit its own guardrails.

## Install into a project (from your phone)

Open a cloud session on the target repo in the Claude app and paste:

```
Install the Mobile Coding Stack: git clone https://github.com/hermes428/mobile-coding-stack /tmp/mcs && bash /tmp/mcs/install.sh . — then commit .claude/ and .mcs/ and push.
```

If the clone fails because this repo is private, either make it public (it contains no secrets) or add it to the session's repositories. Re-running the installer upgrades in place and keeps your contract, state, and lessons.

## Daily use

| You type | What happens |
|---|---|
| `/build add CSV export to the report page` | Claude routes Fast or Full, writes `.mcs/contract.md`, and replies with a 6-line summary |
| `approve` | Edits unlock for exactly the files in the contract |
| *(nothing)* | Claude implements, runs checks, calls the verifier, commits, pushes, and opens a PR |
| `/status` | Contract, approval, cycles, verdict, base commit |
| `/verify deep is the unit conversion right?` | Verifier investigates only that question |
| `stack off` / `stack on` | Pause or resume the gates (only you can do this; it's a typed prompt) |

Review and merge the PR from GitHub on your phone.

## Honest limitations

- **Shell edits aren't gated.** `sed -i` or `echo >` through Bash bypass the Edit/Write gate. Governance forbids it, and the verifier checks the diff against `allowed_files`, so out-of-scope changes surface as FAIL. They just aren't blocked up front.
- **"approve" is detected from your prompt text.** Any prompt starting with `approve` (under 200 characters) counts.
- **Cycle counting matches check commands by substring.** Running a check differently than written in `checks` won't count.
- **All-Claude.** The verifier uses a different model and a fresh context, but it's not cross-vendor like the Codex/Sonnet split in v4.0.
- **One repo per session.** Cloud sessions with several repositories don't load repo hooks.

## Development

```
python3 tests/test_hooks.py     # 47 end-to-end hook checks in a throwaway repo
```

v1.0.0 was also validated against real Claude Code 2.1.296: an unapproved edit was blocked, then a two-turn `/build` → `approve` run produced a contract, one counted cycle, a verifier PASS recorded by the hook, and a commit on a contract branch.

See [CHANGELOG.md](CHANGELOG.md). Version is in `VERSION` and stamped into every installed project and contract.
