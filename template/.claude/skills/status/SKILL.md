---
name: status
description: Show the Mobile Coding Stack state in about five lines. Use when the user types /status or asks where things stand.
---

Run `python3 .claude/stack/hooks/stack.py status` and reply with its output verbatim in a code block. If a contract is PROPOSED, add one line: Reply "approve" to start. If the verdict is stale or missing after edits, add one line suggesting /verify. Nothing else.
