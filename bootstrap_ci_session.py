#!/usr/bin/env python3
"""Non-interactive login used only by the bootstrap-session GitHub Actions
workflow. Not meant to be run locally — use bootstrap_ws_session.py there.

Reads WS_EMAIL / WS_PASSWORD / WS_OTP from the environment, logs in, and
writes the resulting session to ws_session_out.json in the current
directory for the workflow to pick up and push into the WS_SESSION secret.
"""

import os
import sys

from ws_api import OTPRequiredException, WealthsimpleAPI

OUT_FILE = "ws_session_out.json"
SCOPE = "invest.read trade.read tax.read"


def persist_session(session_json: str, _username: str) -> None:
    with open(OUT_FILE, "w") as f:
        f.write(session_json)


def main() -> int:
    username = os.environ["WS_EMAIL"]
    password = os.environ["WS_PASSWORD"]
    otp = os.environ.get("WS_OTP") or None

    try:
        WealthsimpleAPI.login(
            username,
            password,
            otp_answer=otp,
            persist_session_fct=persist_session,
            scope=SCOPE,
        )
    except OTPRequiredException:
        print(
            "OTP_REQUIRED: get a fresh 2FA code and re-run this workflow "
            "with the ws_otp input filled in."
        )
        return 2

    print("LOGIN_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
