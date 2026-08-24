#!/usr/bin/env python3
"""Run this once, locally, to log in to Wealthsimple and save a session file.

Wealthsimple's login flow requires a 2FA/TOTP code, which can't be answered
from an unattended job, so this step is interactive and run by hand. It
writes ws_session.json, which ws_gains_chart.py then reads on every later
run (locally or in CI) without prompting again.

The saved session refreshes itself until it eventually expires, at which
point re-run this script.

Treat ws_session.json like a password: it grants read access to your
Wealthsimple account data. Never commit it to git.
"""

import getpass
import sys

from ws_api import OTPRequiredException, WealthsimpleAPI

SESSION_FILE = "ws_session.json"

# Read-only scope: cannot place trades or move money.
SCOPE = "invest.read trade.read tax.read"


def persist_session(session_json: str, _username: str) -> None:
    with open(SESSION_FILE, "w") as f:
        f.write(session_json)


def main() -> int:
    username = input("Wealthsimple email: ").strip()
    password = getpass.getpass("Wealthsimple password: ")

    try:
        WealthsimpleAPI.login(
            username,
            password,
            persist_session_fct=persist_session,
            scope=SCOPE,
        )
    except OTPRequiredException:
        otp = input("2FA code: ").strip()
        WealthsimpleAPI.login(
            username,
            password,
            otp_answer=otp,
            persist_session_fct=persist_session,
            scope=SCOPE,
        )

    print(f"Session saved to {SESSION_FILE}. Keep this file secret.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
