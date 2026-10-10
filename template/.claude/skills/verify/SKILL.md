---
name: verify
description: Independent verification for the Mobile Coding Stack. Use when the user types /verify, after implementing an approved contract, or with "deep <question>" to settle one hard question. Delegates to the read-only verifier subagent.
---

# /verify

Arguments: $ARGUMENTS

1. Make sure the contract's checks have been run since the last edit. If not, run them first.
2. Delegate to the `verifier` subagent. Build its prompt in this order and keep it lean. Don't paste the diff; it inspects the repo itself.
   - `Contract: .mcs/contract.md` and `Base commit: see .claude/stack/state.json`
   - If the arguments start with `deep`: `DEEP MODE`, the single question, the affected acceptance criterion, the evidence for and against, and why routine verification couldn't decide it.
   - Last, under a heading `CLAIMS (read last)`: your own 3–6 line summary of what you changed and what you believe passes.
3. Relay its result to the user in phone format: the VERDICT line, the reason line, and up to 4 lines of evidence or routing. The hooks record the verdict automatically.
4. Act on routing: repair (cycles permitting), replan via the architect, or stop and ask the user.
