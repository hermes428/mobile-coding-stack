# Mobile Coding Stack v1 — governance (loaded at session start)

This repo uses the Mobile Coding Stack. The user usually works from a phone: keep every reply short and start reports with a one-line verdict.

Loop: understand enough → one bounded contract → auto-approve or check in → smallest correct change → independent verification → stop when evidence runs out.

## Autonomy (human-aware, not human-gated)
Claude handles tedious, low-risk work alone and brings the user in where their judgment changes the outcome. The hook, not Claude, decides:
- **Auto:** fast depth, few files (policy `auto_max_files`, default 3), runnable checks, no sensitive or interest-list paths, no open decisions, previous contract verified. Proceed immediately and tell the user in one line.
- **Check-in:** anything else. The hook gives the reasons; show them and wait for `approve`.
- **Expertise and variance:** a real judgment call (design choice, competing models, UX tradeoff) goes in `decisions:` as `OPEN: A) … B) … C) …` with a one-line tradeoff each. The user replies `approve B`.
- You may escalate with `check_in: yes`. Never shrink a contract or mark decisions DECIDED to dodge a check-in; decisions are DECIDED only after the user chose.
- Unchanged by autonomy: the verifier always runs, and the user always merges.

## Rules
- No code edits without an approved contract in `.mcs/contract.md` (auto- or user-approved). Hooks enforce this for Edit/Write; do not route around it with shell redirects, `sed -i`, or scripts.
- One contract = one smallest next task = one branch/PR. Never silently expand scope; a scope change means editing the contract and asking for approval again.
- Prefer existing patterns → existing abstractions → standard library → approved dependencies → new code. No speculative abstractions.
- Preserve existing and uncommitted work. Don't revert, delete, or "finish" unrelated partial work. Code presence is not proof of intent or correctness.
- Never silently install software, add dependencies, authenticate, trust servers, change global settings, expose data, or commit secrets. Use the capability-provisioning skill.
- Missing evidence or capability = BLOCKED, not a guess.
- Max 3 edit-and-check cycles per contract (hook-enforced). At the cap: stop, report, replan.
- Completion requires a current verifier verdict (hook-enforced). Merging to main requires PASS (hook-enforced).
- When work touches measurements, units, calibration, transforms, models, statistics, or engineering conclusions, load the scientific-rigor skill. Otherwise don't.

## Commands the user may type
- `/build <task>` start or continue the workflow · `/status` five-line state · `/verify` independent check (`/verify deep <question>` for one hard question)
- `approve` / `approve B` approve the contract (and pick an option) · `stack off` / `stack on` pause or resume the gates
- The user edits `.mcs/policy.md` to tune autonomy (`autonomy: tiered|ask`, `auto_max_files`, `sensitive`, `interest`, `ungated`). Paths under `ungated` are live records you may edit freely when that is the session's job. You can't edit it without an approved contract that names it.

## Reporting (phone-sized)
First line: `PASS`, `FAIL`, `BLOCKED`, `PROPOSED`, or `UNRESOLVED`. Then at most ~8 short lines. Details go in the PR description, not chat.

## Backlog
Ideas raised while using the program go in `.mcs/backlog.md` (one dated line each; no contract needed). `/build` with no task offers the top items.
