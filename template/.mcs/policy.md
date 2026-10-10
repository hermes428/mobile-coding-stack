# Autonomy policy — yours to edit (on GitHub or through an approved contract that lists this file)
# Claude cannot change this file on its own. The hook reads it to decide auto vs check-in.

# tiered = low-risk contracts auto-approve; ask = every contract waits for "approve"
autonomy: tiered

# Max files a contract can touch and still auto-approve
auto_max_files: 3

# Extra sensitive paths (always check-in). Built-ins already cover secrets, auth,
# migrations, SQL, dependency manifests and lockfiles, Docker, CI, and infra.
sensitive:
  - none

# Paths that are always editable without a contract and don't need verification:
# live records another session maintains (a log, notes, data). Stack files can't be ungated.
ungated:
  - none

# Areas you always want to weigh in on, even when low risk (globs match anywhere)
interest:
  - none
