---
name: build
description: Mobile Coding Stack workflow. Use when the user types /build or asks to build, fix, add, or change code in this repo. Routes Fast vs Full, writes one contract, waits for "approve", implements, then verifies.
---

# /build — Mobile Coding Stack v1

Task: $ARGUMENTS

Run `python3 .claude/stack/hooks/stack.py status` first. If a contract is already APPROVED and unfinished, continue it instead of starting a new one.

## 1. Route
**Fast** when the task is localized, reversible, already understood, limited to a few known files, and easy to check (bug fix, small feature, refactor, test or config change).
**Full** when it's new, inherited, partial, undocumented, cross-cutting, scientific or numerical, security- or privacy-sensitive, architecture-impacting, or depends on an unverified capability. When unsure, choose Full.

## 2. Contract
- **Fast:** inspect the minimum relevant context yourself and draft the contract.
- **Full:** delegate to the `architect` subagent with the task and any constraints the user gave. Use its contract text.
- Archive any finished previous contract first: move it to `.mcs/archive/<id>.md` (with Bash `git mv` or plain `mv`).
- Write the contract to `.mcs/contract.md` using `.claude/stack/contract.template.md`. Increment the id.
- Reply in phone format:
  ```
  PROPOSED — C-00N (fast|full)
  <objective>
  Files: <allowed_files>
  Done when: <acceptance criteria, short>
  Checks: <commands>
  Reply "approve" to start.
  ```
- Stop and wait. The edit gate stays locked until the user types `approve`.

## 3. Implement (after "approve")
- Work on a branch dedicated to this contract (a cloud session's branch is fine).
- Make the smallest correct change inside `allowed_files`, following existing patterns. Write new tests if the contract lists them.
- Run the contract's `checks` commands verbatim. Each edit-then-check counts as one cycle. The cap is 3, hook-enforced.
- If new facts invalidate the contract or you need another file: stop, explain in 2–3 lines, and propose a contract update. Don't improvise.

## 4. Verify
When the checks pass, invoke `/verify`. If it returns FAIL with Route: repair, fix within the contract and verify again. Route: replan goes back to step 2 with the architect.

## 5. Finish
On PASS: commit, including `.mcs/` (contract, lessons, archive) and `.claude/stack/state.json` (the audit trail). Push the branch and open a PR. The PR description should hold the contract summary, the verifier's verdict block, and the checks run. Reply:
```
PASS — C-00N
<one line: what changed>
PR: <link>
```
On FAIL or BLOCKED: report the verdict line, the reason, and the smallest next decision the user needs to make. Add a one-line cause to `.mcs/lessons.md` if you know it.
