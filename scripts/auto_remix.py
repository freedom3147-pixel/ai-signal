"""Auto-remix Macro Signal digest via DeepSeek (for scheduled local runs).

Reads ~/.ai-signal/payload/payload.json produced by prepare_digest.py,
calls DeepSeek with the same prompts/output_contract the Agent uses,
prints the digest markdown to stdout.

Usage:
    python prepare_digest.py
    python auto_remix.py > digest.md
    python deliver.py --file digest.md --mark-delivered-file ...
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

USER_DIR = Path.home() / ".ai-signal"
ENV_PATH = USER_DIR / ".env"
PAYLOAD_PATH = USER_DIR / "payload" / "payload.json"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


def configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def load_env():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text("utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


def build_system_prompt(payload: dict) -> str:
    contract = payload.get("output_contract") or {}
    parts = [
        contract.get("role", "You are the user's Agent-side Macro Signal digest writer."),
        "",
        "## Source of Truth",
        contract.get("source_of_truth", "Use only the JSON fields in this payload."),
        "",
    ]
    lang = contract.get("language") or {}
    parts.extend(
        [
            "## Language Rules",
            f"- Target: {lang.get('target', 'Simplified Chinese')}",
            f"- Rule: {lang.get('final_digest_rule', '')}",
            f"- Forbidden: {lang.get('forbidden', '')}",
            "",
            "## Content Rules",
        ]
    )
    for rule in contract.get("content_rules") or []:
        parts.append(f"- {rule}")

    prompts = payload.get("prompts") or {}
    if prompts:
        parts.append("")
        parts.append("## Remix Prompts")
        for name, body in prompts.items():
            parts.append(f"\n### {name}\n{body}")

    parts.extend(
        [
            "",
            "## Extra Constraints for Automated Runs",
            "- Follow digest_intro format exactly (title, X/Podcasts/Blogs sections, item IDs).",
            "- Skip personal jokes, political bait, and non-macro posts.",
            "- Do not wrap the final digest in a Markdown code fence.",
            "- If all content sections are empty, output exactly: 今天暂无更新，明天再看！",
        ]
    )
    return "\n".join(parts)


def build_user_content(payload: dict) -> str:
    data = {
        "x": payload.get("x") or [],
        "podcasts": payload.get("podcasts") or [],
        "articles": payload.get("articles") or [],
        "stats": payload.get("stats") or {},
    }
    tweet_count = sum(len(a.get("tweets") or []) for a in data["x"])
    if tweet_count == 0 and not data["podcasts"] and not data["articles"]:
        return (
            "今天的 payload 里没有新的推文、播客或博客文章。"
            "请只输出：今天暂无更新，明天再看！"
        )
    return (
        "请根据以上规则和以下 JSON 数据，生成今天的宏观信号日报：\n\n"
        + json.dumps(data, ensure_ascii=False, indent=2)
    )


def call_deepseek(api_key: str, system_prompt: str, user_content: str) -> str:
    resp = httpx.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.2,
            "max_tokens": 4096,
        },
        timeout=180,
    )
    if not resp.is_success:
        raise RuntimeError(f"DeepSeek HTTP {resp.status_code}: {resp.text[:400]}")
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    if not content or not str(content).strip():
        raise RuntimeError("DeepSeek returned empty content")
    return str(content).strip()


def main():
    configure_stdio()
    load_env()
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("❌ 未找到 DEEPSEEK_API_KEY（请写入 ~/.ai-signal/.env）", file=sys.stderr)
        sys.exit(1)

    if not PAYLOAD_PATH.exists():
        print(f"❌ 找不到 {PAYLOAD_PATH}，请先运行 prepare_digest.py", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(PAYLOAD_PATH.read_text("utf-8-sig"))
    system_prompt = build_system_prompt(payload)
    user_content = build_user_content(payload)

    print("🤖 正在调用 DeepSeek 生成日报...", file=sys.stderr)
    try:
        digest = call_deepseek(api_key, system_prompt, user_content)
    except Exception as exc:
        print(f"❌ API 调用失败: {exc}", file=sys.stderr)
        sys.exit(1)

    print(digest)


if __name__ == "__main__":
    main()
