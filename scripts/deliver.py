"""Subscriber-side: deliver digest text via Telegram / Feishu / email.

Reads delivery config from ~/.ai-signal/config.json and API keys from
~/.ai-signal/.env

Usage:
    echo "digest text" | python scripts/deliver.py
    python scripts/deliver.py --message "digest text"
    python scripts/deliver.py --file /path/to/digest.md
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

SCRIPT_DIR = Path(__file__).parent
USER_DIR = Path.home() / ".ai-signal"
CONFIG_PATH = USER_DIR / "config.json"
ENV_PATH = USER_DIR / ".env"

TELEGRAM_MAX_LEN = 4000


def configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def log(msg):
    print(msg, file=sys.stderr)


def load_env():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text("utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


def split_message(text, max_len=TELEGRAM_MAX_LEN):
    chunks = []
    while len(text) > max_len:
        split_at = text.rfind("\n", 0, max_len)
        if split_at < max_len * 0.3:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text.strip():
        chunks.append(text)
    return chunks


def send_telegram(text, bot_token, chat_id):
    for chunk in split_message(text):
        resp = httpx.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": chunk,
                  "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=30,
        )
        if not resp.is_success:
            err = resp.json()
            if "can't parse" in err.get("description", ""):
                httpx.post(f"https://api.telegram.org/bot{bot_token}/sendMessage",
                           json={"chat_id": chat_id, "text": chunk,
                                 "disable_web_page_preview": True}, timeout=30)
            else:
                log(f"❌ Telegram: {err.get('description', resp.text)}")
                return False
        import time; time.sleep(0.3)
    return True


def send_feishu(text, webhook_url):
    """Push text to a Feishu/Lark custom bot webhook. Split long digests."""
    # Custom bot text messages are safest under ~20KB per request.
    max_len = 18000
    chunks = split_message(text, max_len=max_len) or [text]
    import time

    for i, chunk in enumerate(chunks):
        prefix = f"[{i + 1}/{len(chunks)}]\n" if len(chunks) > 1 else ""
        resp = httpx.post(
            webhook_url,
            json={"msg_type": "text", "content": {"text": prefix + chunk}},
            timeout=30,
        )
        if not resp.is_success:
            log(f"❌ Feishu HTTP {resp.status_code}: {resp.text[:200]}")
            return False
        r = resp.json()
        if not (r.get("code") == 0 or r.get("StatusCode") == 0):
            log(f"❌ Feishu: {r}")
            return False
        if i < len(chunks) - 1:
            time.sleep(0.4)
    return True


def send_email(text, api_key, to_email):
    from datetime import datetime
    resp = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"from": "Daily Digest <digest@resend.dev>", "to": [to_email],
              "subject": f"Daily Digest — {datetime.now().strftime('%Y-%m-%d')}",
              "text": text},
        timeout=30,
    )
    return resp.is_success


def deliver_obsidian(text, vault_daily):
    """Write digest as a new note: YYYY-MM-DD日报-HHMM.md."""
    from datetime import datetime

    daily_dir = Path(vault_daily).expanduser()
    daily_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    day = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M")
    filepath = daily_dir / f"{day}日报-{time_str}.md"

    # Avoid overwrite if two digests land in the same minute.
    if filepath.exists():
        filepath = daily_dir / f"{day}日报-{time_str}-{now.strftime('%S')}.md"

    body = text.lstrip()
    if not body.startswith("---"):
        body = (
            f"---\n"
            f"date: {day}\n"
            f"time: {now.strftime('%H:%M')}\n"
            f"tags:\n"
            f"  - 宏观信号\n"
            f"  - 每日简报\n"
            f"status: 已完成\n"
            f"---\n\n"
            f"{body}"
        )

    filepath.write_text(body, encoding="utf-8")
    log(f"✅ Wrote Obsidian daily: {filepath}")
    return True


def send_wxpusher(text, app_token, uid):
    """Push markdown summary to WeChat via WxPusher."""
    content = text
    if len(content) > 4000:
        content = content[:3900] + "\n\n...(全文已写入 Obsidian 日报)"
    resp = httpx.post(
        "https://wxpusher.zjiecode.com/api/send/message",
        json={
            "appToken": app_token,
            "content": content,
            "contentType": 3,
            "uids": [uid],
        },
        timeout=30,
    )
    if not resp.is_success:
        log(f"❌ WxPusher HTTP {resp.status_code}: {resp.text[:200]}")
        return False
    data = resp.json()
    if data.get("success") or data.get("code") == 1000:
        return True
    log(f"❌ WxPusher: {data}")
    return False


def mark_delivered(mark_file):
    if not mark_file:
        return
    import subprocess
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "mark_delivered.py"), "--file", mark_file],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode == 0:
        log("✅ Marked digest as delivered")
    else:
        log(f"⚠️ Could not mark delivered: {result.stderr or result.stdout}")


def main():
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", "-m", type=str)
    parser.add_argument("--file", "-f", type=str)
    parser.add_argument("--mark-delivered-file", type=str,
                        help="Path to delivery-mark.json; marked only after successful delivery")
    args = parser.parse_args()

    if args.message:
        text = args.message
    elif args.file:
        text = Path(args.file).read_text("utf-8")
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        log("No input. Use --message, --file, or pipe stdin.")
        sys.exit(1)

    if not text.strip():
        log("Empty digest, skipping.")
        return

    load_env()

    config = {}
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text("utf-8-sig"))

    delivery = config.get("delivery", {"method": "stdout"})
    method = delivery.get("method", "stdout")

    if method == "telegram":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = delivery.get("chat_id", "")
        if not token or not chat_id:
            log("❌ Set TELEGRAM_BOT_TOKEN in ~/.ai-signal/.env and chat_id in config.json")
            sys.exit(1)
        ok = send_telegram(text, token, chat_id)
        log("✅ Sent to Telegram" if ok else "❌ Telegram failed")
        if ok:
            mark_delivered(args.mark_delivered_file)

    elif method == "feishu":
        webhook = delivery.get("webhook_url", os.environ.get("FEISHU_WEBHOOK_URL", ""))
        if not webhook:
            log("❌ Set webhook_url in config.json delivery section")
            sys.exit(1)
        ok = send_feishu(text, webhook)
        log("✅ Sent to Feishu" if ok else "❌ Feishu failed")
        if ok:
            mark_delivered(args.mark_delivered_file)

    elif method == "email":
        api_key = os.environ.get("RESEND_API_KEY", "")
        email = delivery.get("email", "")
        if not api_key or not email:
            log("❌ Set RESEND_API_KEY in .env and email in config.json")
            sys.exit(1)
        ok = send_email(text, api_key, email)
        log("✅ Sent to email" if ok else "❌ Email failed")
        if ok:
            mark_delivered(args.mark_delivered_file)

    elif method in ("obsidian", "obsidian_wechat", "obsidian_feishu"):
        vault_daily = delivery.get(
            "obsidian_vault_daily",
            r"D:\我的研究库\daily",
        )
        ok = deliver_obsidian(text, vault_daily)
        if method == "obsidian_wechat":
            app_token = os.environ.get(
                "WXPUSHER_APP_TOKEN",
                delivery.get("wxpusher_app_token", ""),
            )
            uid = delivery.get(
                "wxpusher_uid",
                os.environ.get("WXPUSHER_UID", ""),
            )
            if not app_token or not uid:
                log("⚠️ Obsidian written, but WxPusher token/uid missing — skip WeChat")
            else:
                wx_ok = send_wxpusher(text, app_token, uid)
                log("✅ Sent to WeChat (WxPusher)" if wx_ok else "❌ WeChat push failed")
                ok = ok and wx_ok
        elif method == "obsidian_feishu":
            webhook = delivery.get("webhook_url", os.environ.get("FEISHU_WEBHOOK_URL", ""))
            if not webhook:
                log("⚠️ Obsidian written, but Feishu webhook missing — skip Feishu")
            else:
                feishu_ok = send_feishu(text, webhook)
                log("✅ Sent to Feishu" if feishu_ok else "❌ Feishu push failed")
                ok = ok and feishu_ok
        if ok:
            mark_delivered(args.mark_delivered_file)
        else:
            print(text)
            sys.exit(1)

    else:
        print(text)
        mark_delivered(args.mark_delivered_file)


if __name__ == "__main__":
    main()
