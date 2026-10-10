#!/usr/bin/env python3
"""Mobile Coding Stack v1 - hook engine.

One stdlib-only script that every hook calls with a subcommand:
  session-start | prompt | pre-tool | post-tool | subagent-stop | stop | status

State lives in .claude/stack/state.json (written only by this script).
The contract lives in .mcs/contract.md (written by the main session,
approved by the user typing "approve").
"""
import datetime
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys

VERSION = "1.0.1"
MAX_CYCLES = 3
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
VERIFIER = "verifier"

# Planning artifacts: free to edit without a contract.
FREE = [".mcs/contract.md", ".mcs/lessons.md", ".mcs/backlog.md", ".mcs/archive/*"]
# Never editable by tools: only this script writes it.
LOCKED = [".claude/stack/state.json"]
# Stack machinery: editable only when approved AND explicitly listed in allowed_files.
# Only the stack's own files, so repos whose product is agents and skills can still build them.
PROTECTED = [".claude/settings.json", ".claude/settings.local.json", ".claude/stack/*", ".mcs/policy.md",
             ".claude/agents/architect.md", ".claude/agents/verifier.md",
             ".claude/skills/build/*", ".claude/skills/verify/*", ".claude/skills/status/*",
             ".claude/skills/scientific-rigor/*", ".claude/skills/capability-provisioning/*"]


# ---------- paths & io ----------

def root():
    return os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def p(*parts):
    """Machinery and state: .claude/stack (a protected folder in Claude Code)."""
    return os.path.join(root(), ".claude", "stack", *parts)


def w(*parts):
    """Working files the model writes (contract, lessons, archive): .mcs/ (not protected)."""
    return os.path.join(root(), ".mcs", *parts)


def read_input():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def load_state():
    try:
        with open(p("state.json")) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(st):
    st["stack_version"] = VERSION
    os.makedirs(p(), exist_ok=True)
    tmp = p("state.json.tmp")
    with open(tmp, "w") as f:
        json.dump(st, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, p("state.json"))


def contract_text():
    try:
        with open(w("contract.md")) as f:
            return f.read()
    except Exception:
        return None


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def git(*args):
    try:
        out = subprocess.run(["git", "-C", root(), *args], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def emit(obj):
    print(json.dumps(obj))


def lesson(line):
    try:
        with open(w("lessons.md"), "a") as f:
            f.write(f"- {now()} | {line}\n")
    except Exception:
        pass


# ---------- contract parsing (tiny YAML subset) ----------

def parse_contract(text):
    """Top-level `key: value` scalars and `key:` followed by `  - item` lists."""
    data, key = {}, None
    for line in (text or "").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line.startswith("```"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m and not line.startswith((" ", "\t")):
            key, val = m.group(1), re.sub(r"\s+#.*$", "", m.group(2)).strip()
            data[key] = val.strip("\"'") if val else []
            continue
        m = re.match(r"^\s+-\s+(.*)$", line)
        if m and key is not None:
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(m.group(1).strip().strip("\"'`"))
    return data


def as_list(v):
    if isinstance(v, list):
        return [x for x in v if x and x.lower() not in ("none", "n/a", "[]")]
    return [] if not v or v in ("[]", "none") else [v]


def matches(rel, patterns):
    for pat in patterns:
        pat = pat.strip()
        if pat.startswith("./"):
            pat = pat[2:]
        if not pat:
            continue
        if pat.endswith("/**") or pat.endswith("/"):
            base = pat.rstrip("*").rstrip("/")
            if rel == base or rel.startswith(base + "/"):
                return True
        if fnmatch.fnmatch(rel, pat):
            return True
    return False


# ---------- status ----------

def contract_status(st, text):
    if text is None:
        return "NONE"
    if not st.get("approved_hash"):
        return "PROPOSED"
    return "APPROVED" if st["approved_hash"] == sha(text) else "CHANGED-NEEDS-APPROVAL"


def status_lines(st=None):
    st = st if st is not None else load_state()
    text = contract_text()
    c = parse_contract(text) if text else {}
    cs = contract_status(st, text)
    lines = [f"Mobile Coding Stack v{VERSION}" + ("  [STACK OFF]" if st.get("disabled") else "")]
    if text is None:
        lines.append("Contract: none. Start with /build <task>.")
        return lines
    who = f" by {st.get('approved_by')}" if cs == "APPROVED" and st.get("approved_by") else ""
    lines.append(f"Contract: {c.get('id', '?')} [{cs}{who}] {str(c.get('objective', ''))[:70]}")
    if cs != "APPROVED" and st.get("pending_reasons"):
        lines.append("Check-in because: " + "; ".join(st["pending_reasons"])[:160])
    files = as_list(c.get("allowed_files"))
    lines.append(f"Depth: {c.get('depth', '?')} | Files: {', '.join(files[:4]) or '-'}{' …' if len(files) > 4 else ''}")
    lines.append(f"Cycles: {st.get('cycles', 0)}/{MAX_CYCLES} | Unchecked edits: {'yes' if st.get('dirty') else 'no'}")
    v = st.get("verdict")
    if v:
        fresh = st.get("verdict_gen") == st.get("edit_gen", 0)
        lines.append(f"Verdict: {v} ({'current' if fresh else 'stale, edits since'})")
    else:
        lines.append("Verdict: none")
    if st.get("base_sha"):
        lines.append(f"Base commit: {st['base_sha'][:10]}")
    return lines


# ---------- autonomy tiers (Twilight Factory: approval / expertise / variance / interest) ----------

AUTO_MAX_FILES_DEFAULT = 3
SENSITIVE_DEFAULT = [
    ".env*", "*secret*", "*credential*", "*password*", "*auth*", "*/auth/*", "*migration*",
    "*.sql", "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "requirements*.txt",
    "pyproject.toml", "poetry.lock", "uv.lock", "Pipfile*", "setup.py", "setup.cfg", "Cargo.toml",
    "Cargo.lock", "go.mod", "go.sum", "Gemfile*", "*.gemspec", "Dockerfile*", "docker-compose*",
    ".github/*", ".gitlab-ci*", "infra/*", "terraform/*", "*.tf", "deploy/*",
]


def load_policy():
    try:
        with open(w("policy.md")) as f:
            pol = parse_contract(f.read())
    except Exception:
        pol = {}
    try:
        max_files = int(str(pol.get("auto_max_files", AUTO_MAX_FILES_DEFAULT)))
    except ValueError:
        max_files = AUTO_MAX_FILES_DEFAULT
    return {
        "autonomy": str(pol.get("autonomy") or "tiered").lower(),
        "auto_max_files": max_files,
        "sensitive": SENSITIVE_DEFAULT + as_list(pol.get("sensitive")),
        "interest": as_list(pol.get("interest")),
        "ungated": as_list(pol.get("ungated")),
    }


def ungated(rel):
    """User-declared paths that are always editable (e.g. a live record another session maintains)."""
    return matches(rel, load_policy()["ungated"]) and not matches(rel, PROTECTED) and not matches(rel, LOCKED)


def hits(rel, patterns):
    """Match a path or glob against patterns anywhere in the tree."""
    base = rel.rsplit("/", 1)[-1]
    for pat in patterns:
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(base, pat) or fnmatch.fnmatch(rel, "*/" + pat):
            return True
    return False


def open_decisions(c):
    return [d for d in as_list(c.get("decisions")) if not d.upper().startswith("DECIDED")]


def finished(st):
    return st.get("verdict") == "PASS" and st.get("verdict_gen") == st.get("edit_gen", 0)


def classify(c, st):
    """Return ('auto' | 'check-in', reasons). Computed by the hook, never self-declared."""
    pol, reasons = load_policy(), []
    files = as_list(c.get("allowed_files"))
    if pol["autonomy"] in ("ask", "always-ask", "off", "manual"):
        reasons.append("policy says always ask")
    if str(c.get("depth", "")).lower() != "fast":
        reasons.append("full-depth work")
    if str(c.get("scientific", "")).lower().startswith("y"):
        reasons.append("scientific meaning affected")
    if open_decisions(c):
        reasons.append(f"{len(open_decisions(c))} open decision(s) need your judgment")
    if str(c.get("check_in", "")).lower().startswith("y"):
        reasons.append("Claude flagged it for a check-in")
    if not as_list(c.get("checks")):
        reasons.append("no runnable checks")
    if len(files) > pol["auto_max_files"]:
        reasons.append(f"{len(files)} files (auto limit {pol['auto_max_files']})")
    if any(ch in f for f in files for ch in "*?["):
        reasons.append("broad file globs")
    sens = [f for f in files if hits(f, pol["sensitive"]) or matches(f, PROTECTED)]
    if sens:
        reasons.append("sensitive files: " + ", ".join(sens[:3]))
    intr = [f for f in files if hits(f, pol["interest"])]
    if intr:
        reasons.append("your interest list: " + ", ".join(intr[:3]))
    if st.get("approved_hash") and c.get("id") == st.get("contract_id"):
        reasons.append("revises an already-approved contract (scope change)")
    elif st.get("approved_hash") and st.get("edit_gen", 0) and not finished(st):
        reasons.append(f"previous contract {st.get('contract_id')} isn't verified PASS")
    return ("check-in" if reasons else "auto"), reasons


def approve(st, text, by, note=""):
    h, c = sha(text), parse_contract(text)
    if c.get("id", "?") != st.get("contract_id"):
        # New contract: fresh cycle budget and baseline. Same-id revisions keep their cycles.
        st.update({"cycles": 0, "dirty": False, "edit_gen": 0, "verdict": None, "verdict_gen": None,
                   "base_sha": git("rev-parse", "HEAD")})
    st.update({"approved_hash": h, "contract_id": c.get("id", "?"), "approved_at": now(),
               "approved_by": by, "approval_note": note[:200], "pending_reasons": []})
    save_state(st)
    return h, c


def evaluate_contract(st):
    """Auto-approve a low-risk proposed contract, or record why it needs a check-in."""
    text = contract_text()
    if text is None or st.get("approved_hash") == sha(text) or st.get("disabled"):
        return None
    c = parse_contract(text)
    tier, reasons = classify(c, st)
    if tier == "auto":
        approve(st, text, "auto")
        return (f"AUTO-APPROVED contract {c.get('id', '?')} (low risk: fast, {len(as_list(c.get('allowed_files')))} "
                f"file(s), tested, nothing sensitive). Proceed now without waiting. Tell the user in one line: "
                f"'AUTO — {c.get('id', '?')}: <objective>. Working; reply stop to halt.' The verifier and the "
                f"user's PR merge still apply.")
    st["pending_reasons"] = reasons
    save_state(st)
    return (f"CHECK-IN REQUIRED for contract {c.get('id', '?')}: " + "; ".join(reasons) +
            ". Show the user the PROPOSED summary with these reasons (and the options for any open decision), "
            "then wait for them to reply 'approve' (or 'approve <option>').")


# ---------- handlers ----------

def h_session_start(_inp):
    out = []
    try:
        with open(p("governance.md")) as f:
            out.append(f.read().strip())
    except Exception:
        out.append("Mobile Coding Stack governance file missing (.claude/stack/governance.md).")
    out.append("\nCurrent stack status:\n" + "\n".join(status_lines()))
    print("\n".join(out)[:9500])


def h_prompt(inp):
    prompt = (inp.get("prompt") or "").strip()
    low = prompt.lower()
    st = load_state()

    if re.fullmatch(r"stack\s+off", low):
        st["disabled"] = True
        save_state(st)
        print("The user turned the Mobile Coding Stack gates OFF for this repo. Edits are not gated until they type 'stack on'.")
        return
    if re.fullmatch(r"stack\s+on", low):
        st["disabled"] = False
        save_state(st)
        print("The user turned the Mobile Coding Stack gates back ON.")
        return

    if not re.match(r"^approve(d)?\b", low) or len(prompt) > 200:
        return
    text = contract_text()
    if text is None:
        print("The user typed 'approve' but there is no .mcs/contract.md to approve. Tell them.")
        return
    h, c = approve(st, text, "user", prompt)
    print(f"The user APPROVED contract {c.get('id', '?')} (hash {h[:12]}) with: \"{prompt[:120]}\". "
          f"If they picked an option for an open decision, implement that option. "
          f"Base commit: {st.get('base_sha') or 'none'}. Edits to allowed_files are now unlocked. "
          f"Cycles used: {st.get('cycles', 0)}/{MAX_CYCLES}. Changing contract.md will re-lock edits.")


def deny(reason):
    emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                 "permissionDecision": "deny",
                                 "permissionDecisionReason": reason}})


def target_path(inp):
    ti = inp.get("tool_input") or {}
    return ti.get("file_path") or ti.get("notebook_path") or ti.get("path") or ""


def rel_to_root(path):
    if not path:
        return None
    full = os.path.realpath(path if os.path.isabs(path) else os.path.join(inp_cwd or root(), path))
    r = root()
    if full == r or not full.startswith(r + os.sep):
        return None  # outside the project (scratch, tmp): not gated
    return os.path.relpath(full, r).replace(os.sep, "/")


inp_cwd = None

MERGE_RE = re.compile(r"\bgh\s+pr\s+merge\b|\bgit\s+merge\b|\bgit\s+push\b[^\n;&|]*\b(main|master)\b")
STATE_WRITE_RE = re.compile(r">|\btee\b|\bsed\b[^\n]*-i|\bmv\b|\bcp\b|\brm\b|\btruncate\b|\bpython|\bperl\b|\bnode\b|\bruby\b")


def h_pre_tool(inp):
    st = load_state()
    tool = inp.get("tool_name", "")

    if tool == "Bash":
        cmd = (inp.get("tool_input") or {}).get("command", "")
        if "stack/state.json" in cmd and STATE_WRITE_RE.search(cmd):
            return deny("state.json is written only by the stack hooks. Read it with cat, or run /status.")
        if st.get("disabled"):
            return
        if MERGE_RE.search(cmd):
            gen = st.get("edit_gen", 0)
            if gen and not (st.get("verdict") == "PASS" and st.get("verdict_gen") == gen):
                return deny("Merging/pushing to main requires a current verifier PASS. Run /verify first. "
                            "Pushing the feature branch and opening a PR is fine.")
        return

    if tool not in EDIT_TOOLS:
        return
    rel = rel_to_root(target_path(inp))
    if rel is None:
        return
    if matches(rel, LOCKED):
        return deny("state.json is written only by the stack hooks.")
    if matches(rel, FREE) or ungated(rel):
        return
    if st.get("disabled"):
        return

    text = contract_text()
    if text is None:
        return deny(f"No contract. Edits to {rel} are locked until a contract exists in "
                    ".mcs/contract.md and the user replies 'approve'. Use /build.")
    cs = contract_status(st, text)
    if cs != "APPROVED":
        evaluate_contract(st)
        st = load_state()
        cs = contract_status(st, text)
    if cs == "PROPOSED":
        return deny("Contract needs a check-in: " + "; ".join(st.get("pending_reasons") or ["not approved"]) +
                    ". Show the user the summary and reasons and wait for 'approve'.")
    if cs == "CHANGED-NEEDS-APPROVAL":
        return deny("contract.md changed after approval (" + "; ".join(st.get("pending_reasons") or ["scope change"]) +
                    "). Summarize what changed and ask the user to reply 'approve' again before editing.")
    c = parse_contract(text)
    allowed, forbidden = as_list(c.get("allowed_files")), as_list(c.get("forbidden_files"))
    if matches(rel, forbidden):
        return deny(f"{rel} is in forbidden_files. Stop and replan if it must change.")
    if not matches(rel, allowed):
        return deny(f"{rel} is outside allowed_files ({', '.join(allowed) or 'none'}). "
                    "That is a scope change: propose a contract update and get approval.")
    if matches(rel, PROTECTED) and not any(rel == a.strip() for a in allowed):
        return deny(f"{rel} is stack machinery. It must be listed by exact path in allowed_files.")
    if st.get("cycles", 0) >= MAX_CYCLES:
        lesson(f"{c.get('id', '?')} | CYCLE CAP hit at {MAX_CYCLES} | {str(c.get('objective', ''))[:80]}")
        return deny(f"Cycle cap reached ({MAX_CYCLES} edit-and-check cycles). Stop, report what failed, "
                    "and route to replanning: a revised contract needs new approval.")


def h_post_tool(inp):
    st = load_state()
    tool = inp.get("tool_name", "")
    if tool in EDIT_TOOLS:
        rel = rel_to_root(target_path(inp))
        if rel == ".mcs/contract.md":
            msg = evaluate_contract(st)
            if msg:
                emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}})
            return
        if rel is None or matches(rel, FREE) or matches(rel, LOCKED) or ungated(rel):
            return
        st["dirty"] = True
        st["edit_gen"] = st.get("edit_gen", 0) + 1
        save_state(st)
        return
    if tool == "Bash" and st.get("dirty"):
        cmd = (inp.get("tool_input") or {}).get("command", "")
        checks = as_list(parse_contract(contract_text() or "").get("checks"))
        if any(ch and ch in cmd for ch in checks):
            st["cycles"] = st.get("cycles", 0) + 1
            st["dirty"] = False
            st["last_check"] = {"cmd": cmd[:200], "at": now()}
            save_state(st)


def h_subagent_stop(inp):
    if inp.get("agent_type", "").split(":")[-1] != VERIFIER:
        return
    msg = inp.get("last_assistant_message") or ""
    m = re.search(r"VERDICT:\s*\**\s*(PASS|FAIL|BLOCKED|UNRESOLVED)", msg)
    if not m:
        return
    v = m.group(1)
    st = load_state()
    st["verdict"] = v
    st["verdict_gen"] = st.get("edit_gen", 0)
    st["verdict_at"] = now()
    save_state(st)
    if v != "PASS":
        reason = ""
        for line in msg.splitlines()[1:]:
            if line.strip():
                reason = line.strip()[:120]
                break
        lesson(f"{st.get('contract_id', '?')} | VERIFIER {v} | {reason}")


def h_stop(inp):
    if inp.get("stop_hook_active"):
        return
    st = load_state()
    if st.get("disabled"):
        return
    gen = st.get("edit_gen", 0)
    if gen and st.get("verdict_gen") != gen and st.get("cycles", 0) < MAX_CYCLES:
        emit({"decision": "block",
              "reason": "Code changed under the approved contract but no verifier verdict covers the latest "
                        "edits. Run the checks, then delegate to the verifier subagent (/verify) before finishing. "
                        "If you are blocked, say so and stop."})


def main():
    global inp_cwd
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print("\n".join(status_lines()))
        return
    inp = read_input()
    inp_cwd = inp.get("cwd")
    handler = {"session-start": h_session_start, "prompt": h_prompt, "pre-tool": h_pre_tool,
               "post-tool": h_post_tool, "subagent-stop": h_subagent_stop, "stop": h_stop}.get(cmd)
    if not handler:
        return
    try:
        handler(inp)
    except Exception as e:  # fail closed only for the edit gate
        if cmd == "pre-tool" and inp.get("tool_name") in EDIT_TOOLS:
            deny(f"Stack hook error ({type(e).__name__}: {e}). Edit blocked; fix the hook or type 'stack off'.")
        else:
            print(f"stack hook error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
