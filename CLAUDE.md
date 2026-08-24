# Wealthsimple Personal Trading Dashboard — Project Brief

> Handoff doc for continuing this build in Claude Code. Drop this at the repo
> root (Claude Code reads `CLAUDE.md` automatically). Rename if you prefer.

## Goal

A personal dashboard over my **Wealthsimple non-registered (cash/taxable)**
account. First feature built: a chart of **every stock I've traded and its
realized gain/loss, sorted descending** (biggest winners at top, losers at
bottom). More widgets to come.

Read-and-analyze only. No trade execution, no moving money.

## Data source decision (important context)

Options evaluated, and why we landed where we did:

- **`ws-api`** (github.com/gboudreau/ws-api-python) — unofficial Python library
  wrapping Wealthsimple's internal GraphQL API. **This is what the current code
  uses.** Free, direct, full control. Default scope is READ-ONLY
  (`invest.read trade.read tax.read`) so it cannot trade or move money.
  Unofficial = a gray area; keep usage read-only and low-frequency (a daily
  pull is fine, not every few minutes).
- **SnapTrade Personal API** — the *sanctioned* route (OAuth-based, free for
  personal use, and explicitly supports connecting brokerage data to Claude).
  Was blocked at time of writing because SnapTrade's **Wealthsimple connector
  was under maintenance**. If it comes back, port the same script structure to
  SnapTrade's Personal API — cleaner because no credentials are handed to a
  library. Docs: docs.snaptrade.com
- **Perplexity Finance** — connects WS via **Plaid** (not SnapTrade), read-only.
  Good for conversational Q&A but gives no raw API to build custom charts, so
  not usable for this dashboard.

**Key technical insight:** Wealthsimple computes realized gain/loss *per
security* on its own backend. So we do NOT reconstruct cost basis (no FIFO /
average-cost math). One call to `get_identity_realized_returns` returns a
`securityBreakdown` of `{ security.stock.symbol, totalValue.amount }` per stock.
Sort descending, plot. Done.

## Current code

Two scripts (Python 3.10+):

### `bootstrap_ws_session.py` (run ONCE, locally)
Interactive login that handles the 2FA/TOTP prompt and saves the session to
`ws_session.json`. Separate step because a 2FA code can't be typed in an
unattended job. The saved session refreshes itself until it eventually expires,
at which point re-run this.

### `ws_gains_chart.py` (the dashboard feature)
- Loads session from `ws_session.json` (or `WS_SESSION` env var for CI)
- Auto-detects the non-registered account (WS labels it `cash` internally;
  prints all accounts so the match can be corrected)
- Calls `get_identity_realized_returns(currency="CAD", account_ids=[id])`
- Writes `gains_by_stock.csv` (symbol, name, gain) and `gains_by_stock.png`
  (horizontal bar chart, green = gain, red = loss)

Install: `pip install ws-api matplotlib keyring`

## ws-api methods reference (verified against installed library)

- `WealthsimpleAPI.login(username, password, otp_answer=None, persist_session_fct=None, scope="invest.read trade.read tax.read")`
- `WealthsimpleAPI.from_token(session, persist_session_fct=None, username=None)`
- `WSAPISession.from_json(str)` / `session.to_json()` — serialize the session
- `ws.get_accounts(open_only=True)` → accounts with `id`, `description`, `unified_account_type`
- `ws.get_identity_realized_returns(currency, account_ids=None, start_date=None, first=None)`
  → `{ totalValue, securityBreakdown: { edges: [{ node: { security.stock.symbol, totalValue.amount }}] } }`
- `ws.get_activities(account_id, how_many=50, load_all=False, start_date=None, end_date=None)`
  → per-transaction feed; `type` includes `DIY_BUY` / `DIY_SELL`; fields include
  `assetSymbol`, `assetQuantity`, `amount`, `occurredAt`, `securityId`, `realizedPnl`
- `ws.get_identity_positions(security_ids, currency)` → open positions w/ `unrealizedReturns`
- `ws.get_account_unrealized_pnl(account_id, currency, combined=True)`
- `ws.get_dividends(currency, account_ids=None, ...)`
- `ws.security_id_to_symbol(security_id)`

## Next steps / open items

1. **Unrealized gains** — realized-returns only covers *sold* positions. Add
   open holdings via `get_identity_positions` / `get_account_unrealized_pnl`
   for the full picture (second series or second chart).
2. **Full dashboard** — turn the CSV into a multi-widget local HTML page
   (gains chart + positions + dividends + activity feed).
3. **GitHub Actions automation** — DONE, see `.github/workflows/daily-gains.yml`.
   Runs daily + on-demand, reads the session from the `WS_SESSION` repo
   secret, commits the refreshed CSV/PNG back to the repo.
   - **Session refresh problem:** handled opt-in — if a `SECRETS_PAT` repo
     secret (scoped to manage this repo's Actions secrets) is present, the
     workflow writes the refreshed session back to `WS_SESSION` after each
     run. Without it, re-bootstrap locally and update the secret by hand if
     the session ever stops working. See README for setup.
   - **Security tradeoff (decide consciously):** running on GitHub puts a
     token that can *read* all WS financial data into GitHub's cloud. For a
     purely personal tool, a local cron job is the safer home. Read-only scope
     limits blast radius but doesn't eliminate it.
4. **Optional port to SnapTrade Personal API** once its WS connector is live —
   sanctioned path, no credentials handed to a library.

## Guardrails

- Keep it **read-only**. Don't add trade-execution scopes.
- Keep pull frequency low (daily is plenty).
- Treat `ws_session.json` / `WS_SESSION` like a password.
- This is unofficial access to Wealthsimple; their terms govern. Re-check the
  client agreement before relying on it long-term.
