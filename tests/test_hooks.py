#!/usr/bin/env python3
"""End-to-end test of the Mobile Coding Stack hooks.
Installs the stack into a throwaway git repo and drives each hook with the JSON
Claude Code would send. Run: python3 tests/test_hooks.py
"""
import json, os, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ok   {name}")
    else:
        failed += 1
        print(f"  FAIL {name} {detail}")


def main():
    d = tempfile.mkdtemp(prefix="mcs-")
    run = lambda *a, **k: subprocess.run(a, cwd=d, capture_output=True, text=True, **k)
    run("git", "init", "-q")
    run("git", "config", "user.email", "t@t")
    run("git", "config", "user.name", "t")
    os.makedirs(f"{d}/src")
    open(f"{d}/src/app.py", "w").write("x = 1\n")
    open(f"{d}/.claude_placeholder", "w").write("")
    run("git", "add", "-A"); run("git", "commit", "-qm", "init")

    # Pre-existing user settings must survive the merge.
    os.makedirs(f"{d}/.claude")
    json.dump({"permissions": {"allow": ["Bash(ls:*)"]}}, open(f"{d}/.claude/settings.json", "w"))
    r = subprocess.run(["bash", f"{REPO}/install.sh", d], capture_output=True, text=True)
    check("installer runs", r.returncode == 0, r.stderr)
    s = json.load(open(f"{d}/.claude/settings.json"))
    check("settings merged, user keys kept", "permissions" in s and "PreToolUse" in s["hooks"])
    subprocess.run(["bash", f"{REPO}/install.sh", d], capture_output=True)
    s = json.load(open(f"{d}/.claude/settings.json"))
    check("re-install doesn't duplicate hooks", len(s["hooks"]["PreToolUse"]) == 1)

    env = dict(os.environ, CLAUDE_PROJECT_DIR=d)
    hook = f"{d}/.claude/stack/hooks/stack.py"

    def h(event, payload):
        payload.setdefault("cwd", d)
        out = subprocess.run(["python3", hook, event], input=json.dumps(payload),
                             capture_output=True, text=True, env=env, cwd=d)
        return out.stdout.strip()

    def edit(path, agent=None):
        p = {"tool_name": "Edit", "tool_input": {"file_path": os.path.join(d, path)}}
        if agent:
            p["agent_type"] = agent
        return h("pre-tool", p)

    def denied(out):
        return '"deny"' in out

    def state():
        return json.load(open(f"{d}/.claude/stack/state.json"))

    print("gate")
    check("edit blocked with no contract", denied(edit("src/app.py")))
    check("contract.md is free to write", not denied(edit(".mcs/contract.md")))
    check("files outside project not gated", h("pre-tool", {"tool_name": "Write", "tool_input": {"file_path": "/tmp/x.txt"}}) == "")
    check("SessionStart injects governance", "governance" in h("session-start", {}).lower())

    contract = """id: C-001
depth: fast            # fast | full
objective: bump x
allowed_files:
  - src/app.py
  - tests/**
forbidden_files:
  - src/secret.py
checks:
  - python3 -c 'import src'
"""
    open(f"{d}/.mcs/contract.md", "w").write(contract)
    out = edit("src/app.py")
    check("broad-glob contract needs check-in", denied(out) and "broad file globs" in out, out)
    check("prompt 'approve this?' long text ignored", h("prompt", {"prompt": "can you explain " * 30}) == "")
    out = h("prompt", {"prompt": "approve"})
    check("'approve' approves", "APPROVED contract C-001" in out, out)
    check("base sha recorded", len(state().get("base_sha", "")) == 40)
    check("depth parsed without inline comment", "Depth: fast |" in subprocess.run(["python3", hook, "status"], capture_output=True, text=True, env=env).stdout)

    print("scope")
    check("allowed file edit passes", not denied(edit("src/app.py")))
    check("glob tests/** passes", not denied(edit("tests/deep/test_a.py")))
    check("out-of-scope file blocked", denied(edit("src/other.py")))
    open(f"{d}/.mcs/contract.md", "a").write("  - src/secret.py\n")  # sneaks into forbidden list only
    out = edit("src/app.py")
    check("contract change re-locks edits", denied(out) and "changed after approval" in out)
    open(f"{d}/.mcs/contract.md", "w").write(contract)
    check("restoring approved contract unlocks", not denied(edit("src/app.py")))
    check("settings.json protected", denied(edit(".claude/settings.json")))
    check("state.json locked", denied(edit(".claude/stack/state.json")))
    bash = lambda c: h("pre-tool", {"tool_name": "Bash", "tool_input": {"command": c}})
    check("bash write to state.json blocked", denied(bash("echo {} > .claude/stack/state.json")))
    check("bash read of state.json allowed", not denied(bash("cat .claude/stack/state.json")))

    print("cycles")
    for i in range(1, 4):
        h("post-tool", {"tool_name": "Edit", "tool_input": {"file_path": f"{d}/src/app.py"}})
        h("post-tool", {"tool_name": "Bash", "tool_input": {"command": "ls"}})  # not a check
        h("post-tool", {"tool_name": "Bash", "tool_input": {"command": "cd x && python3 -c 'import src'"}})
        check(f"cycle {i} counted", state()["cycles"] == i)
    check("check without new edit doesn't count",
          (h("post-tool", {"tool_name": "Bash", "tool_input": {"command": "python3 -c 'import src'"}}), state()["cycles"])[1] == 3)
    out = edit("src/app.py")
    check("4th cycle blocked", denied(out) and "Cycle cap" in out)
    h("prompt", {"prompt": "approve"})
    check("re-approving same contract does NOT reset cycles", state()["cycles"] == 3)

    print("verification")
    out = h("stop", {})
    check("stop allowed at cycle cap (report instead)", out == "")
    # New contract resets the budget.
    open(f"{d}/.mcs/contract.md", "w").write(contract.replace("C-001", "C-002"))
    h("prompt", {"prompt": "Approve"})
    check("new contract resets cycles", state()["cycles"] == 0 and state()["contract_id"] == "C-002")
    h("post-tool", {"tool_name": "Edit", "tool_input": {"file_path": f"{d}/src/app.py"}})
    out = h("stop", {})
    check("stop blocked: edits without verdict", '"block"' in out)
    check("stop_hook_active prevents loop", h("stop", {"stop_hook_active": True}) == "")
    check("merge blocked without PASS", denied(bash("gh pr merge 3")))
    check("feature-branch push allowed", not denied(bash("git push -u origin feat/x")))
    h("subagent-stop", {"agent_type": "verifier", "last_assistant_message": "VERDICT: FAIL\nAC1 not met: x still 1"})
    check("FAIL verdict recorded", state()["verdict"] == "FAIL")
    check("FAIL logged to lessons", "VERIFIER FAIL | AC1 not met" in open(f"{d}/.mcs/lessons.md").read())
    check("merge still blocked on FAIL", denied(bash("git merge feat/x")))
    h("subagent-stop", {"agent_type": "architect", "last_assistant_message": "VERDICT: PASS"})
    check("non-verifier verdict ignored", state()["verdict"] == "FAIL")
    h("subagent-stop", {"agent_type": "verifier", "last_assistant_message": "VERDICT: **PASS**\nall good"})
    check("PASS recorded", state()["verdict"] == "PASS")
    check("stop allowed after current verdict", h("stop", {}) == "")
    check("merge allowed after PASS", not denied(bash("gh pr merge 3")))
    h("post-tool", {"tool_name": "Edit", "tool_input": {"file_path": f"{d}/src/app.py"}})
    check("new edit makes verdict stale", "stale" in subprocess.run(["python3", hook, "status"], capture_output=True, text=True, env=env).stdout)
    check("merge re-blocked after new edit", denied(bash("gh pr merge 3")))

    print("kill switch & robustness")
    h("prompt", {"prompt": "stack off"})
    check("stack off ungates edits", not denied(edit("src/other.py")))
    check("state.json still locked when off", denied(edit(".claude/stack/state.json")))
    h("prompt", {"prompt": "stack on"})
    check("stack on re-gates", denied(edit("src/other.py")))
    os.remove(f"{d}/.mcs/contract.md")
    check("missing contract handled", denied(edit("src/app.py")))
    out = subprocess.run(["python3", hook, "pre-tool"], input="not json", capture_output=True, text=True, env=env)
    check("garbage input doesn't crash", out.returncode == 0)

    autonomy_tests()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


def autonomy_tests():
    print("autonomy tiers")
    d = tempfile.mkdtemp(prefix="mcs-auto-")
    run = lambda *a: subprocess.run(a, cwd=d, capture_output=True, text=True)
    run("git", "init", "-q"); run("git", "config", "user.email", "t@t"); run("git", "config", "user.name", "t")
    os.makedirs(f"{d}/src"); open(f"{d}/src/app.py", "w").write("x = 1\n")
    run("git", "add", "-A"); run("git", "commit", "-qm", "init")
    subprocess.run(["bash", f"{REPO}/install.sh", d], capture_output=True)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=d)
    hook = f"{d}/.claude/stack/hooks/stack.py"

    def h(event, payload):
        payload.setdefault("cwd", d)
        return subprocess.run(["python3", hook, event], input=json.dumps(payload), capture_output=True,
                              text=True, env=env, cwd=d).stdout.strip()

    def write_contract(body):
        open(f"{d}/.mcs/contract.md", "w").write(body)
        return h("post-tool", {"tool_name": "Write", "tool_input": {"file_path": f"{d}/.mcs/contract.md"}})

    edit = lambda p: h("pre-tool", {"tool_name": "Edit", "tool_input": {"file_path": f"{d}/{p}"}})
    st = lambda: json.load(open(f"{d}/.claude/stack/state.json"))
    verify_pass = lambda: (h("post-tool", {"tool_name": "Bash", "tool_input": {"command": "python3 -m pytest"}}),
                           h("subagent-stop", {"agent_type": "verifier", "last_assistant_message": "VERDICT: PASS"}))
    base = "id: {id}\ndepth: {depth}\nobjective: o\nallowed_files:\n  - {f}\nchecks:\n  - python3 -m pytest\n{extra}"
    C = lambda id="C-001", depth="fast", f="src/app.py", extra="": base.format(id=id, depth=depth, f=f, extra=extra)

    out = write_contract(C())
    check("low-risk contract auto-approves", "AUTO-APPROVED" in out and st().get("approved_by") == "auto", out)
    check("auto-approved edit allowed", '"deny"' not in edit("src/app.py"))
    check("auto scope still enforced", '"deny"' in edit("src/other.py"))
    h("post-tool", {"tool_name": "Edit", "tool_input": {"file_path": f"{d}/src/app.py"}})
    out = write_contract(C(f="src/other.py"))
    check("same-id revision needs check-in", "CHECK-IN" in out and "scope change" in out, out)
    out = write_contract(C(id="C-002"))
    check("next contract waits while previous unverified", "isn't verified PASS" in out, out)
    write_contract(C())
    verify_pass()
    out = write_contract(C(id="C-002"))
    check("after PASS, next low-risk contract auto-approves", "AUTO-APPROVED" in out, out)
    verify_pass()

    out = write_contract(C(id="C-003", f="package.json"))
    check("dependency manifest triggers check-in", "sensitive files: package.json" in out, out)
    out = write_contract(C(id="C-003", f="src/auth/login.py"))
    check("auth path triggers check-in", "sensitive files" in out, out)
    out = write_contract(C(id="C-003", depth="full"))
    check("full depth triggers check-in", "full-depth" in out, out)
    out = write_contract(C(id="C-003", extra="scientific: yes\n"))
    check("scientific triggers check-in", "scientific" in out, out)
    out = write_contract(C(id="C-003", extra="check_in: yes\n"))
    check("Claude can escalate", "flagged" in out, out)
    out = write_contract(C(id="C-003").replace("checks:\n  - python3 -m pytest\n", ""))
    check("no checks triggers check-in", "no runnable checks" in out, out)
    out = write_contract(C(id="C-003", extra="decisions:\n  - OPEN: A) cache in memory B) cache on disk\n"))
    check("open decision triggers check-in", "open decision" in out, out)
    check("pending reasons visible in status", "Check-in because" in subprocess.run(
        ["python3", hook, "status"], capture_output=True, text=True, env=env).stdout)
    out = h("prompt", {"prompt": "approve B"})
    check("'approve B' approves and records the choice", st()["approval_note"] == "approve B" and "approve B" in out)
    verify_pass()
    out = write_contract(C(id="C-004", extra="decisions:\n  - DECIDED: use B (user, C-003)\n"))
    check("decided-only decisions can auto-approve", "AUTO-APPROVED" in out, out)
    verify_pass()

    check("policy.md is protected", '"deny"' in edit(".mcs/policy.md"))
    open(f"{d}/.mcs/policy.md", "w").write("autonomy: tiered\ninterest:\n  - *model*\n")
    out = write_contract(C(id="C-005", f="src/data_model.py"))
    check("interest list triggers check-in", "interest list" in out, out)
    open(f"{d}/.mcs/policy.md", "w").write("autonomy: ask\n")
    out = write_contract(C(id="C-005"))
    check("policy 'ask' disables auto", "always ask" in out, out)
    open(f"{d}/.mcs/policy.md", "w").write("autonomy: tiered\nauto_max_files: 1\n")
    out = write_contract(C(id="C-005").replace("  - src/app.py\n", "  - src/app.py\n  - src/b.py\n"))
    check("auto_max_files respected", "2 files (auto limit 1)" in out, out)


if __name__ == "__main__":
    main()
