"""Standalone sanity check for TWITTER_COOKIES before wiring it into GitHub Secrets.

Loads ~/.ai-signal/.env (same format/loader as deliver.py) and tries one real
twscrape search against a public account. Never prints the cookie value itself —
only pass/fail + sanitized error text — so its output is safe to paste anywhere.

Usage:
    python scripts/test_twitter_cookies.py [--handle karpathy]
"""

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
USER_DIR = Path.home() / ".ai-signal"
ENV_PATH = USER_DIR / ".env"


def load_env():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text("utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


def redact(text):
    text = re.sub(r"auth_token=[^;\s\"]+", "auth_token=***", text)
    text = re.sub(r"ct0=[^;\s\"]+", "ct0=***", text)
    return text


async def main():
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--handle", default="karpathy",
                        help="Public X handle to test-search (default: karpathy)")
    args = parser.parse_args()

    cookies = os.environ.get("TWITTER_COOKIES", "")
    if not cookies:
        print(f"FAIL: TWITTER_COOKIES not found. Checked env var and {ENV_PATH}")
        print("      Add a line to that file: TWITTER_COOKIES=auth_token=xxx; ct0=yyy")
        sys.exit(1)
    if "auth_token=" not in cookies or "ct0=" not in cookies:
        print("FAIL: TWITTER_COOKIES is set but missing 'auth_token=' or 'ct0=' — check the format.")
        sys.exit(1)

    try:
        from twscrape import API, gather
    except ImportError:
        print("FAIL: twscrape not installed. Run: pip install -r requirements-central.txt")
        sys.exit(1)

    db_path = str(SCRIPT_DIR / "twitter_accounts.db")
    Path(db_path).unlink(missing_ok=True)  # start clean each test run
    api = API(db_path)
    await api.pool.add_account_cookies("probe", cookies)
    await api.pool.set_active("probe", True)

    print(f"Testing: search from:{args.handle} ...")
    try:
        tweets = await gather(api.search(f"from:{args.handle}", limit=5))
    except Exception as e:
        print(f"FAIL: request raised an exception: {redact(str(e))}")
        sys.exit(1)

    if not tweets:
        print("WARN: request succeeded but returned 0 tweets — cookies may still be valid; "
              "the account might just have no recent posts, or the search got soft-filtered.")
        sys.exit(2)

    print(f"OK: fetched {len(tweets)} tweet(s) from @{args.handle}. Cookies are working.")
    for t in tweets[:3]:
        preview = (t.rawContent or "")[:60].replace("\n", " ")
        print(f"  - {t.date} | {preview!r}")


if __name__ == "__main__":
    asyncio.run(main())
