# Working on this project

- The repository is public; `main` is the current, checked research snapshot.
- Start with `.github/README.md` and `docs/paper-preparation/README.md`. The root
  `README.md` is a frozen historical artifact; `READY-TO-RUN.md` records v7 closeout.
- Use a short-lived `codex/...` branch and pull request for a new change.
- Run the relevant offline checks before merging. Do not modify frozen results to make a check pass.
- Keep study stages separate. Preserve failed attempts, labels, grouping, prompts and analysis plans.
- Keep credentials, restricted raw records and review responses out of Git.
- New inference needs its own approved scope and budget. Cleanup and reproduction do not authorize model calls.
- After a merge, remove the finished remote branch. Historical stage tips are preserved under `archive/2026-11-01/...` tags and in Git history.

See [reproduction](REPRODUCING.md), [data access](DATA.md), and [branch history](docs/repository/HISTORY.md).
