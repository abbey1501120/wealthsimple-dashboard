#!/usr/bin/env python3
"""Chart realized gain/loss per stock for the Wealthsimple non-registered account.

Wealthsimple computes realized gain/loss per security on its own backend, so
this does not reconstruct cost basis (no FIFO / average-cost math) — it just
reads get_identity_realized_returns, sorts descending, and plots it.

Session loading:
  - Locally: reads ws_session.json (written by bootstrap_ws_session.py).
  - In CI: set the WS_SESSION env var to the same JSON instead.

Outputs:
  - gains_by_stock.csv  (symbol, name, gain)
  - gains_by_stock.png  (horizontal bar chart, green = gain, red = loss)
"""

import csv
import os
import sys

import matplotlib.pyplot as plt
from ws_api import WealthsimpleAPI, WSAPISession

SESSION_FILE = "ws_session.json"
CURRENCY = "CAD"
CSV_OUT = "gains_by_stock.csv"
CHART_OUT = "gains_by_stock.png"

# Wealthsimple's internal unified_account_type for a non-registered
# (cash/taxable) investing account.
NON_REGISTERED_ACCOUNT_TYPE = "cash"


def load_session_json() -> str:
    env_session = os.environ.get("WS_SESSION")
    if env_session:
        return env_session
    with open(SESSION_FILE) as f:
        return f.read()


def persist_session(session_json: str, _username: str) -> None:
    # Always write the (possibly refreshed) session locally. Locally this
    # updates ws_session.json in place; in CI it produces a fresh
    # ws_session.json in the ephemeral runner workspace that the workflow
    # can compare against the WS_SESSION secret and re-upload if it changed.
    with open(SESSION_FILE, "w") as f:
        f.write(session_json)


def find_non_registered_account(accounts: list[dict]) -> dict:
    print("Accounts on this identity:")
    for acct in accounts:
        print(f"  id={acct['id']}  type={acct.get('unified_account_type')}  "
              f"description={acct.get('description')!r}")

    for acct in accounts:
        if acct.get("unified_account_type") == NON_REGISTERED_ACCOUNT_TYPE:
            return acct

    raise SystemExit(
        f"No account with unified_account_type={NON_REGISTERED_ACCOUNT_TYPE!r} found. "
        "Check the list above and hardcode the account id if the label differs."
    )


def fetch_realized_gains(ws: WealthsimpleAPI, account_id: str) -> list[dict]:
    result = ws.get_identity_realized_returns(currency=CURRENCY, account_ids=[account_id])
    edges = result.get("securityBreakdown", {}).get("edges", [])

    rows = []
    for edge in edges:
        node = edge["node"]
        stock = node.get("security", {}).get("stock", {})
        symbol = stock.get("symbol", "?")
        name = stock.get("name", symbol)
        gain = float(node["totalValue"]["amount"])
        rows.append({"symbol": symbol, "name": name, "gain": gain})

    rows.sort(key=lambda r: r["gain"], reverse=True)
    return rows


def write_csv(rows: list[dict]) -> None:
    with open(CSV_OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["symbol", "name", "gain"])
        writer.writeheader()
        writer.writerows(rows)


def write_chart(rows: list[dict]) -> None:
    symbols = [r["symbol"] for r in rows]
    gains = [r["gain"] for r in rows]
    colors = ["#2e7d32" if g >= 0 else "#c62828" for g in gains]

    height = max(4, 0.35 * len(rows))
    fig, ax = plt.subplots(figsize=(10, height))
    ax.barh(symbols, gains, color=colors)
    ax.invert_yaxis()  # biggest winner at top
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel(f"Realized gain/loss ({CURRENCY})")
    ax.set_title("Realized gain/loss by stock — Wealthsimple non-registered account")
    fig.tight_layout()
    fig.savefig(CHART_OUT, dpi=150)


def main() -> int:
    session = WSAPISession.from_json(load_session_json())
    ws = WealthsimpleAPI.from_token(session, persist_session_fct=persist_session)

    accounts = ws.get_accounts(open_only=True)
    account = find_non_registered_account(accounts)

    rows = fetch_realized_gains(ws, account["id"])
    if not rows:
        print("No realized gains/losses returned for this account.")
        return 0

    write_csv(rows)
    write_chart(rows)
    print(f"Wrote {CSV_OUT} and {CHART_OUT} ({len(rows)} stocks).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
