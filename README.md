# wealthsimple-dashboard

Personal dashboard over a Wealthsimple non-registered (cash/taxable) account.
Read-and-analyze only — no trade execution, no moving money.

See `CLAUDE.md` for the full project brief (data source decision, API
reference, guardrails, next steps).

## Quick start

```bash
pip install -r requirements.txt
python bootstrap_ws_session.py   # run once, interactively, handles 2FA
python ws_gains_chart.py         # writes gains_by_stock.csv / .png
```

`ws_session.json` (created by `bootstrap_ws_session.py`) grants read access
to your Wealthsimple account data — never commit it. It's already in
`.gitignore`.

## GitHub Actions automation (optional)

`.github/workflows/daily-gains.yml` runs the pull daily (and on-demand via
"Run workflow") and commits the refreshed `gains_by_stock.csv` /
`gains_by_stock.png` back to the repo.

**Security tradeoff, per CLAUDE.md:** this puts a token that can *read* all
your Wealthsimple financial data into GitHub's cloud as a repo secret. For a
purely personal tool, a local cron job is the safer home — only enable this
if you're consciously OK with that tradeoff. Read-only scope limits blast
radius but doesn't eliminate it.

Setup:

1. Run `bootstrap_ws_session.py` locally once.
2. Add the contents of the resulting `ws_session.json` as a repo secret
   named `WS_SESSION` (Settings → Secrets and variables → Actions).
3. *(Optional, for auto session-refresh)* Wealthsimple's session tokens can
   rotate on use. If they do, the workflow needs to write the new session
   back to the `WS_SESSION` secret itself, or a later run may start failing.
   The default `GITHUB_TOKEN` cannot manage repo secrets, so this step is
   opt-in: create a token scoped only to manage this repo's Actions secrets
   (a fine-grained PAT with "Secrets: write" access limited to this one
   repo is the least-privileged option) and add it as a secret named
   `SECRETS_PAT`. Without it, if the session ever stops working, just
   re-run `bootstrap_ws_session.py` locally and update the `WS_SESSION`
   secret by hand.
