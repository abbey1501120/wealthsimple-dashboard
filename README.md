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
