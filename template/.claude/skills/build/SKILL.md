---
name: build
description: Mobile Coding Stack workflow. Use when the user types /build or asks to build, fix, add, or change code in this repo. Routes Fast vs Full, writes one contract, auto-proceeds on low risk or checks in, implements, then verifies.
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
- If there's a real judgment call, list it under `decisions:` as `OPEN: A) … B) … C) …` (2–3 genuinely different approaches). Don't manufacture options for obvious choices.
- Writing the contract triggers the hook, which replies AUTO-APPROVED or CHECK-IN REQUIRED with reasons. Follow it.
  - **Auto:** reply with one line, `AUTO — C-00N: <objective>. Working; reply stop to halt.`, and go straight to step 3.
  - **Check-in:** reply in phone format and stop:
    ```
    CHECK-IN — C-00N (fast|full)
    Why: <hook's reasons, short>
    <objective>
    Files: <allowed_files> · Done when: <criteria> · Checks: <commands>
    Options: A) … B) …   (only if decisions are open; one-line tradeoff each)
    Reply "approve" (or "approve B").
    ```
- Never restructure a contract to slip under the auto threshold. If it's naturally bigger, it's a check-in.

## 3. Implement (after auto-approval or "approve")
- Work on a branch dedicated to this contract (a cloud session's branch is fine).
- Make the smallest correct change inside `allowed_files`, following existing patterns. Write new tests if the contract lists them.
- Run the contract's `checks` commands verbatim. Each edit-then-check counts as one cycle. The cap is 3, hook-enforced.
- If the user picked an option, implement exactly that one. When you next archive the contract, its decision line becomes `DECIDED: <option> (user, C-00N)`.
- If new facts invalidate the contract or you need another file: stop, explain in 2–3 lines, and propose a contract update. Revisions always need a check-in. Don't improvise.

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
