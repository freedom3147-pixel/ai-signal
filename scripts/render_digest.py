"""Render prepared AI Signal JSON into a readable Markdown digest.

This is a lightweight formatter for zero-code users and scheduled delivery.
It does not call an LLM. It uses central cached summaries when available and
falls back to raw feed metadata.

Usage:
    python scripts/prepare_digest.py | python scripts/render_digest.py
"""

import json
import re
import sys
from datetime import datetime


def clean_text(text):
    return "".join(ch for ch in text if not 0xD800 <= ord(ch) <= 0xDFFF)


def configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def section_from_summary(text):
    if not text:
        return ""
    marker = "\n## Summary\n"
    if marker in text:
        text = text.split(marker, 1)[1]
    text = re.sub(r"^---\s*", "", text.strip())
    text = re.sub(r"\s*---\s*$", "", text.strip())
    return text.strip()


def short_text(text, limit):
    text = re.sub(r"\s+", " ", clean_text(text or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def render_podcasts(data, lines):
    central = data.get("central_summaries") or {}
    podcasts = central.get("podcasts") or []
    if podcasts:
        lines.append("## 播客精选")
        for item in podcasts:
            title = item.get("title", "Untitled")
            url = item.get("source_url", "")
            channel = item.get("channel", "")
            lines.append(f"### {channel} - {title}" if channel else f"### {title}")
            if url:
                lines.append(f"原文：{url}")
            summary = section_from_summary(item.get("summary_text", ""))
            lines.append(summary or "中央摘要暂不可用。")
            lines.append("")
        return

    raw = data.get("podcasts") or []
    if raw:
        lines.append("## 播客更新")
        for item in raw[:5]:
            title = item.get("title", "Untitled")
            channel = item.get("channel", "")
            url = item.get("link", "")
            desc = short_text(item.get("description", ""), 260)
            lines.append(f"- {channel} - {title}")
            if desc:
                lines.append(f"  {desc}")
            if url:
                lines.append(f"  {url}")
        lines.append("")


def render_tweets(data, lines):
    central = data.get("central_summaries") or {}
    x_by_id = {str(item.get("tweet_id") or item.get("id")): item for item in central.get("x", [])}
    accounts = data.get("x") or []
    total_tweets = sum(len(account.get("tweets", [])) for account in accounts)
    if total_tweets:
        lines.append("## X / Twitter 逐条摘要")
        for account in accounts:
            name = account.get("name") or account.get("handle") or "Unknown"
            handle = account.get("handle", "")
            for tweet in account.get("tweets", []):
                tweet_id = str(tweet.get("id", ""))
                item = x_by_id.get(tweet_id, {})
                url = item.get("source_url") or tweet.get("url", "")
                lines.append(f"### {name}" + (f" (@{handle})" if handle else ""))
                summary = section_from_summary(item.get("summary_text", ""))
                if summary:
                    lines.append(summary)
                elif item.get("status") == "error":
                    lines.append(f"摘要生成失败：{item.get('error', 'unknown error')}")
                else:
                    lines.append("中央摘要暂不可用，先推送原文。")
                original = item.get("original_text") or tweet.get("text", "")
                lines.append("")
                lines.append("原文：")
                lines.append(f"> {original.replace(chr(10), chr(10) + '> ')}")
                metrics = []
                likes = item.get("like_count", tweet.get("like_count", 0))
                reposts = item.get("retweet_count", tweet.get("retweet_count", 0))
                if likes:
                    metrics.append(f"{likes} likes")
                if reposts:
                    metrics.append(f"{reposts} reposts")
                if metrics:
                    lines.append(f"互动：{', '.join(metrics)}")
                if url:
                    lines.append(f"链接：{url}")
                lines.append("")
        return

    active = [account for account in accounts if account.get("tweets")]
    if not active:
        return
    lines.append("## X / Twitter")
    for account in active[:8]:
        name = account.get("name") or account.get("handle")
        lines.append(f"### {name}")
        for tweet in account.get("tweets", [])[:2]:
            text = short_text(tweet.get("text", ""), 260)
            url = tweet.get("url", "")
            metrics = []
            if tweet.get("like_count"):
                metrics.append(f"{tweet.get('like_count')} likes")
            if tweet.get("retweet_count"):
                metrics.append(f"{tweet.get('retweet_count')} reposts")
            suffix = f" ({', '.join(metrics)})" if metrics else ""
            lines.append(f"- {text}{suffix}")
            if url:
                lines.append(f"  {url}")
        lines.append("")


def render_papers(data, lines):
    central = data.get("central_summaries") or {}
    central_papers = central.get("papers") or []
    if central_papers:
        lines.append("## 论文精选")
        for item in central_papers[:8]:
            title = item.get("title", "Untitled")
            url = item.get("source_url", "")
            lines.append(f"### {title}")
            if url:
                lines.append(f"arXiv：{url}")
            summary = section_from_summary(item.get("summary_text", ""))
            lines.append(summary or "中央论文摘要暂不可用。")
            lines.append("")
        return

    papers = data.get("papers") or []
    if papers:
        lines.append("## arXiv 新论文")
        for paper in papers[:8]:
            title = paper.get("title", "Untitled")
            abstract = short_text(paper.get("abstract", ""), 280)
            url = paper.get("abs_url", "")
            lines.append(f"- {title}")
            if abstract:
                lines.append(f"  {abstract}")
            if url:
                lines.append(f"  {url}")
        lines.append("")


def main():
    configure_stdio()
    raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("No input JSON")
    data = json.loads(raw)
    cfg = data.get("config") or {}
    stats = data.get("stats") or {}
    now = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# AI Signal 日报 - {now}",
        "",
        f"版本：{cfg.get('summary_profile', 'raw')} | 语言：{cfg.get('language', 'en')} | 详细度：{cfg.get('granularity', 'summary')}",
        "",
        (
            f"今日内容：播客 {stats.get('podcast_episodes', 0)} 条，"
            f"中央推文摘要 {stats.get('central_x_summaries', 0)} 条，"
            f"中央播客摘要 {stats.get('central_podcast_summaries', 0)} 条，"
            f"推文 {stats.get('total_tweets', 0)} 条，"
            f"论文 {stats.get('arxiv_papers', 0)} 篇。"
        ),
        "",
    ]

    if data.get("errors"):
        lines.append("> 非致命提示：" + "; ".join(data["errors"]))
        lines.append("")

    render_podcasts(data, lines)
    render_tweets(data, lines)
    render_papers(data, lines)

    if len(lines) <= 7:
        lines.append("今天暂时没有可展示的新内容。")

    sys.stdout.write(clean_text("\n".join(line.rstrip() for line in lines)).strip() + "\n")


if __name__ == "__main__":
    main()
