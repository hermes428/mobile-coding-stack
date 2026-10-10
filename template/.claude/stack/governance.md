# Mobile Coding Stack v1 — governance (loaded at session start)

This repo uses the Mobile Coding Stack. The user usually works from a phone: keep every reply short and start reports with a one-line verdict.

Loop: understand enough → one bounded contract → user types "approve" → smallest correct change → independent verification → stop when evidence runs out.

## Rules
- No code edits without an approved contract in `.mcs/contract.md`. Hooks enforce this for Edit/Write; do not route around it with shell redirects, `sed -i`, or scripts.
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
- `approve` approve the current contract · `stack off` / `stack on` pause or resume the gates

## Reporting (phone-sized)
First line: `PASS`, `FAIL`, `BLOCKED`, `PROPOSED`, or `UNRESOLVED`. Then at most ~8 short lines. Details go in the PR description, not chat.
