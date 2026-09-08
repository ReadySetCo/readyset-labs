# Git convention — strategy-os (two Claude chats edit this repo in parallel)

Two sessions work on `rsstrategytool.html`: the **main product chat** and the **Stately chat**.
Local repo only (no remote). Rules for BOTH chats:

1. **Before editing**: run `git status` + `git log --oneline -3`. If there are uncommitted changes you didn't make, STOP and tell Felipe — the other chat is mid-edit.
2. **After each coherent change**: commit immediately. Message prefix says who: `main:` or `stately:` — e.g. `stately: performance-by-period module`, `main: casting radar card`.
3. Never rewrite history (no amend/rebase on existing commits) — the other chat may have read them.
4. The file is ~5K lines; prefer surgical edits and re-read the region you touch before editing (the other chat may have moved it).
5. Shared state notes still go to `Clients/Stately/STATELY-WORKING-DOC.md` (Stately) — git is for code history, the doc is for meaning.

6. **Sync con Labs (desde 2026-09-07):** este repo vive también como carpeta `strategy-os/` dentro de `ReadySetCo/readyset-labs` (main), a pedido de Fede. El working copy del día a día sigue siendo ESTA carpeta local; al cierre de cada tanda de trabajo, el chat que cerró sincroniza a Labs: en el clone `Work/readyset-labs/`, `git fetch sos && git merge -X subtree=strategy-os/ sos/main && git push`. El remote `sos` apunta a esta carpeta local.

7. **Deploy a Vercel (desde 2026-09-08):** producción vive en **https://strategy-os-theta.vercel.app** (proyecto `strategy-os`, team RS/readysetllc, Vercel Authentication ON — solo miembros del team). El deploy se alimenta del repo espejo `felipemgarrido-wq/strategy-os-deploy` (main → auto-deploy). Para shippear una versión: `cp rsstrategytool.html "../../strategy-os-deploy/index.html" && git -C ../../strategy-os-deploy commit -am "deploy: <qué cambió>" && git -C ../../strategy-os-deploy push`. Regla de oro para usuarios: compartir SOLO la URL de producción (los preview URLs tienen otro origen → localStorage vacío) y exportar el 🏷 tag pack como backup periódico.
