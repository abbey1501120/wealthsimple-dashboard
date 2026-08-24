#!/usr/bin/env python3
"""Run this once, locally, to log in to Wealthsimple and save a session.

Wealthsimple's login flow requires a 2FA/TOTP code, which can't be answered
from an unattended job, so this step is interactive and run by hand. The
session is stored in your OS keyring (macOS Keychain / GNOME Keyring /
Windows Credential Manager) rather than a plaintext file, and
ws_gains_chart.py reads it from there on every later local run without
prompting again.

The saved session refreshes itself until it eventually expires, at which
point re-run this script.

The session grants read access to your Wealthsimple account data — treat it
like a password. It never touches disk as plaintext locally; it's only
printed once at the end of this script, for you to paste into a GitHub
Actions secret if you want CI automation (see README).
"""

import getpass
import sys

import keyring
from ws_api import OTPRequiredException, WealthsimpleAPI

KEYRING_SERVICE = "wealthsimple-dashboard"
KEYRING_KEY = "ws_session"

# Read-only scope: cannot place trades or move money.
SCOPE = "invest.read trade.read tax.read"


def persist_session(session_json: str, _username: str) -> None:
    keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, session_json)


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

    print(f"Session saved to your OS keyring (service={KEYRING_SERVICE!r}).")
    print()
    print("Only needed for GitHub Actions automation: paste the line below")
    print("into the WS_SESSION repo secret. Treat it like a password.")
    print()
    print(keyring.get_password(KEYRING_SERVICE, KEYRING_KEY))
    return 0


if __name__ == "__main__":
    sys.exit(main())
