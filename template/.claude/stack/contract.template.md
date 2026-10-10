# Contract template — copy to .mcs/contract.md (keep it under one phone screen)
# Lists use "  - item". Hooks read: allowed_files, forbidden_files, checks, depth, scientific, decisions, check_in.
# The hook decides auto vs check-in from these fields. You can escalate (check_in: yes), never downgrade.
id: C-001
stack_version: 1.0.0
depth: fast            # fast | full
objective: One sentence describing the single smallest next task.
non_goals:
  - What this contract deliberately does not do
allowed_files:
  - src/example.py
  - tests/test_example.py
forbidden_files:
  - .env
acceptance_criteria:
  - AC1: observable behavior that must be true
checks:
  - pytest -q tests/test_example.py
scientific: no         # yes when units, calibration, models, or statistical meaning are affected
decisions:
  - none               # "OPEN: A) ... B) ..." for real judgment calls; "DECIDED: <choice> (user, C-00N)" once settled
check_in: no           # yes if the user should see this even though it looks low risk
assumptions:
  - Anything unverified the plan relies on
risks:
  - Main way this could go wrong
stop_conditions:
  - New facts invalidate the plan
  - A change outside allowed_files is needed
