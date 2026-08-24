#!/usr/bin/env python3
"""Chart realized gain/loss per stock for the Wealthsimple non-registered account.

Wealthsimple computes realized gain/loss per security on its own backend, so
this does not reconstruct cost basis (no FIFO / average-cost math) — it just
reads get_identity_realized_returns, sorts descending, and plots it.

Session loading:
  - Locally: reads the session from the OS keyring (written there by
    bootstrap_ws_session.py).
  - In CI: set the WS_SESSION env var to the same session JSON instead —
    there's no OS keyring on a GitHub Actions runner.

Outputs:
  - gains_by_stock.csv  (symbol, name, gain)
  - gains_by_stock.png  (horizontal bar chart, green = gain, red = loss)
"""

import csv
import os
import sys

import keyring
import matplotlib.pyplot as plt
from ws_api import WealthsimpleAPI, WSAPISession

KEYRING_SERVICE = "wealthsimple-dashboard"
KEYRING_KEY = "ws_session"

# Ephemeral hand-off file, used only in CI (see persist_session below).
SESSION_FILE = "ws_session.json"
CURRENCY = "CAD"
CSV_OUT = "gains_by_stock.csv"
CHART_OUT = "gains_by_stock.png"

# get_accounts() doesn't populate unified_account_type in this ws-api
# version (always None), so match on the account id/description instead.
# Wealthsimple can have multiple non-registered accounts (e.g. self-directed
# margin, crypto, a managed custom portfolio) — this targets the
# self-directed trading one specifically.
NON_REGISTERED_ID_PREFIX = "non-registered-"
NON_REGISTERED_DESCRIPTION_HINT = "self-directed"


def in_ci() -> bool:
    return bool(os.environ.get("WS_SESSION"))


def load_session_json() -> str:
    if in_ci():
        return os.environ["WS_SESSION"]

    session = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
    if not session:
        raise SystemExit(
            "No session found in the OS keyring. Run bootstrap_ws_session.py first."
        )
    return session


def persist_session(session_json: str, _username: str) -> None:
    # The session can rotate its tokens on refresh, so always persist the
    # latest copy. Locally that means the OS keyring; in CI there's no
    # keyring, so write it to a local file the workflow can pick up and
    # push back to the WS_SESSION secret.
    if in_ci():
        with open(SESSION_FILE, "w") as f:
            f.write(session_json)
    else:
        keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, session_json)


def find_non_registered_account(accounts: list[dict]) -> dict:
    print("Accounts on this identity:")
    for acct in accounts:
        print(f"  id={acct['id']}  description={acct.get('description')!r}")

    candidates = [
        acct
        for acct in accounts
        if acct["id"].startswith(NON_REGISTERED_ID_PREFIX)
        and NON_REGISTERED_DESCRIPTION_HINT in (acct.get("description") or "").lower()
    ]

    if len(candidates) == 1:
        return candidates[0]

    raise SystemExit(
        f"Expected exactly one non-registered account with "
        f"{NON_REGISTERED_DESCRIPTION_HINT!r} in its description, found "
        f"{len(candidates)}. Check the list above and adjust "
        "NON_REGISTERED_ID_PREFIX / NON_REGISTERED_DESCRIPTION_HINT, or "
        "hardcode the account id, if your account labels differ."
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
