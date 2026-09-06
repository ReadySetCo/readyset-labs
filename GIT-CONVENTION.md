# Git convention — strategy-os (two Claude chats edit this repo in parallel)

Two sessions work on `rsstrategytool.html`: the **main product chat** and the **Stately chat**.
Local repo only (no remote). Rules for BOTH chats:

1. **Before editing**: run `git status` + `git log --oneline -3`. If there are uncommitted changes you didn't make, STOP and tell Felipe — the other chat is mid-edit.
2. **After each coherent change**: commit immediately. Message prefix says who: `main:` or `stately:` — e.g. `stately: performance-by-period module`, `main: casting radar card`.
3. Never rewrite history (no amend/rebase on existing commits) — the other chat may have read them.
4. The file is ~5K lines; prefer surgical edits and re-read the region you touch before editing (the other chat may have moved it).
5. Shared state notes still go to `Clients/Stately/STATELY-WORKING-DOC.md` (Stately) — git is for code history, the doc is for meaning.
