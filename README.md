# wealthsimple-dashboard

Personal dashboard over a Wealthsimple non-registered (cash/taxable) account.
Read-and-analyze only — no trade execution, no moving money.

See `CLAUDE.md` for the full project brief (data source decision, API
reference, guardrails, next steps).

**Security tradeoff, per CLAUDE.md:** running this on GitHub puts a token
that can *read* all your Wealthsimple financial data into GitHub's cloud as
a repo secret. For a purely personal tool, a local cron job is the safer
home — only use the GitHub Actions path below if you're consciously OK with
that tradeoff. Read-only scope limits blast radius but doesn't eliminate it.

## Option A: entirely on GitHub, no local install

Everything runs on GitHub-hosted runners — nothing to clone or install on
your own machine.

1. Create a fine-grained GitHub PAT scoped to *only this repo*, with
   **Secrets: write** permission (Settings → Developer settings → Personal
   access tokens → Fine-grained tokens). Add it as a repo secret named
   `SECRETS_PAT` (Settings → Secrets and variables → Actions).
2. Go to **Actions → Bootstrap Wealthsimple session (one-time) → Run
   workflow**. Enter your email and password (leave the 2FA field blank the
   first time) and run it.
3. Wealthsimple almost always requires a 2FA code, so this first run will
   fail with `OTP_REQUIRED`. Get a fresh code from your authenticator and
   run the workflow again with the `ws_otp` field filled in — do this
   promptly, since the code expires in seconds.
4. Once it succeeds, the `WS_SESSION` secret is populated. From then on,
   **Actions → Daily Wealthsimple gains pull** runs automatically every day
   (or trigger it manually with "Run workflow") and commits
   `gains_by_stock.csv` / `gains_by_stock.png` back to the repo, where they
   can be viewed directly on github.com.

Workflow inputs (email, password, OTP) are masked in the run logs. They're
used once to log in and are never written anywhere; only the resulting
session token is persisted, as the `WS_SESSION` secret.

## Option B: run it locally instead

```bash
pip install -r requirements.txt
python bootstrap_ws_session.py   # run once, interactively, handles 2FA
python ws_gains_chart.py         # writes gains_by_stock.csv / .png
```

The session (created by `bootstrap_ws_session.py`) grants read access to
your Wealthsimple account data — treat it like a password. Locally it's
stored in your OS keyring (macOS Keychain / GNOME Keyring / Windows
Credential Manager), never as a plaintext file. Your Wealthsimple
email/password themselves are never stored anywhere by these scripts — you
type them by hand each time you (re-)run `bootstrap_ws_session.py`; keep
them in your own password manager as usual.

You can also use this local session to seed the `WS_SESSION` secret by hand
(paste the value it prints) instead of going through Option A's bootstrap
workflow — see `.github/workflows/daily-gains.yml`'s comments for details.
