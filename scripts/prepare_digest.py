"""Subscriber-side: fetch central feeds + user config, output JSON for LLM.

Pulls feed-x.json and feed-podcasts.json from the central GitHub repo,
combines with the user's local config and prompt preferences,
and outputs a single JSON blob to stdout for the LLM to process.

Usage:
    python scripts/prepare_digest.py

Output: JSON to stdout (the LLM reads this and generates the digest)
"""

import json
import os
import sys
from pathlib import Path

import httpx

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent

RAW_BASE = "https://raw.githubusercontent.com/Benboerba620/ai-signal/main"
FEED_BASE = f"{RAW_BASE}/feeds"
FEED_X_URL = f"{FEED_BASE}/feed-x.json"
FEED_PODCASTS_URL = f"{FEED_BASE}/feed-podcasts.json"
FEED_ARXIV_URL = f"{FEED_BASE}/feed-arxiv.json"
FEED_SUMMARIES_URL = f"{FEED_BASE}/feed-summaries.json"

PROMPTS_BASE = "https://raw.githubusercontent.com/Benboerba620/ai-signal/main/prompts"
PROMPT_FILES = [
    "summarize-podcast.md",
    "summarize-tweets.md",
    "summarize-papers.md",
    "digest-intro.md",
]

USER_DIR = Path.home() / ".ai-signal"
CONFIG_PATH = USER_DIR / "config.json"


def configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def clean_text(text):
    return "".join(ch for ch in text if not 0xD800 <= ord(ch) <= 0xDFFF)


def clean_data(value):
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, list):
        return [clean_data(item) for item in value]
    if isinstance(value, dict):
        return {clean_data(k): clean_data(v) for k, v in value.items()}
    return value


def fetch_json(url):
    try:
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        text = resp.content.decode("utf-8", errors="replace")
        return clean_data(json.loads(clean_text(text)))
    except Exception:
        return None


def fetch_text(url):
    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        return clean_text(resp.content.decode("utf-8", errors="replace"))
    except Exception:
        return None


def load_local_json(filename):
    path = ROOT_DIR / "feeds" / filename
    if not path.exists():
        return None
    try:
        return clean_data(json.loads(clean_text(path.read_text("utf-8", errors="replace"))))
    except Exception:
        return None


def load_local_text(path_text):
    path = ROOT_DIR / path_text
    if not path.exists():
        return None
    try:
        return clean_text(path.read_text("utf-8", errors="replace"))
    except Exception:
        return None


def fetch_feed(url, filename, content_key=None):
    remote = fetch_json(url)
    local = load_local_json(filename)
    if remote and (not content_key or remote.get(content_key)):
        return remote
    return local or remote


def choose_summary_profile(config):
    explicit = config.get("summary_profile")
    if explicit:
        return explicit

    language = config.get("language", "en")
    granularity = config.get("granularity", "summary")

    if language == "zh":
        if granularity in ("highlights", "short"):
            return "zh_short"
        if granularity in ("full", "deep"):
            return "zh_deep"
        return "zh_standard"
    if language == "bilingual":
        return "bilingual_short"
    return "en_standard"


def wants_central_summaries(config):
    value = config.get("include_central_summaries", False)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return False


def filter_summary_items(items, domains):
    if not domains:
        return items
    return [item for item in items if item.get("domain", "ai") in domains]


def attach_summary_text(items):
    results = []
    for item in items:
        summary_path = item.get("summary_path")
        enriched = dict(item)
        if summary_path:
            text = fetch_text(f"{RAW_BASE}/{summary_path}") or load_local_text(summary_path)
            if text:
                enriched["summary_text"] = text
        results.append(enriched)
    return results


def main():
    configure_stdio()
    errors = []

    # 1. User config
    config = {"language": "en", "granularity": "summary", "delivery": {"method": "stdout"}}
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text("utf-8-sig"))
        except Exception as e:
            errors.append(f"Config read error: {e}")

    # 2. Fetch feeds
    feed_x = fetch_feed(FEED_X_URL, "feed-x.json", "x")
    feed_podcasts = fetch_feed(FEED_PODCASTS_URL, "feed-podcasts.json", "podcasts")
    feed_arxiv = fetch_feed(FEED_ARXIV_URL, "feed-arxiv.json", "papers")
    include_central_summaries = wants_central_summaries(config)
    feed_summaries = fetch_feed(FEED_SUMMARIES_URL, "feed-summaries.json", "profiles") if include_central_summaries else None
    if not feed_x:
        errors.append("Could not fetch tweet feed")
    if not feed_podcasts:
        errors.append("Could not fetch podcast feed")
    if not feed_arxiv:
        errors.append("Could not fetch arXiv feed")

    # 3. Load prompts: user custom > remote > local
    prompts = {}
    user_prompts_dir = USER_DIR / "prompts"
    local_prompts_dir = ROOT_DIR / "prompts"

    for filename in PROMPT_FILES:
        key = filename.replace(".md", "").replace("-", "_")
        user_path = user_prompts_dir / filename
        local_path = local_prompts_dir / filename

        if user_path.exists():
            prompts[key] = clean_text(user_path.read_text("utf-8", errors="replace"))
            continue
        remote = fetch_text(f"{PROMPTS_BASE}/{filename}")
        if remote:
            prompts[key] = remote
            continue
        if local_path.exists():
            prompts[key] = clean_text(local_path.read_text("utf-8", errors="replace"))
        else:
            errors.append(f"Could not load prompt: {filename}")

    # 4. Build output
    papers = (feed_arxiv or {}).get("papers", [])
    domains = config.get("domains", ["ai", "invest"])
    summary_profile = choose_summary_profile(config)
    available_summary_profiles = sorted(((feed_summaries or {}).get("profiles") or {}).keys())
    selected_summary = ((feed_summaries or {}).get("profiles") or {}).get(summary_profile)
    if feed_summaries and not selected_summary:
        errors.append(
            f"Summary profile not available: {summary_profile}. "
            f"Available profiles: {', '.join(available_summary_profiles) or 'none'}"
        )

    central_summaries = None
    if selected_summary:
        central_summaries = {
            "profile": summary_profile,
            "available_profiles": available_summary_profiles,
            "language": selected_summary.get("language"),
            "detail": selected_summary.get("detail"),
            "x": attach_summary_text(filter_summary_items(selected_summary.get("x", []), domains)),
            "podcasts": attach_summary_text(filter_summary_items(selected_summary.get("podcasts", []), domains)),
            "papers": attach_summary_text(filter_summary_items(selected_summary.get("papers", []), domains)),
        }

    output = {
        "status": "ok",
        "mode": "json_first",
        "generated_at": (feed_x or {}).get("generated_at") or (feed_podcasts or {}).get("generated_at"),
        "config": {
            "language": config.get("language", "en"),
            "granularity": config.get("granularity", "summary"),
            "include_central_summaries": include_central_summaries,
            "summary_profile": summary_profile,
            "available_summary_profiles": available_summary_profiles,
            "domains": domains,
            "delivery": config.get("delivery", {"method": "stdout"}),
        },
        "central_summaries": central_summaries,
        "podcasts": (feed_podcasts or {}).get("podcasts", []),
        "x": (feed_x or {}).get("x", []),
        "papers": papers,
        "stats": {
            "podcast_episodes": len((feed_podcasts or {}).get("podcasts", [])),
            "podcast_with_transcript": sum(1 for e in (feed_podcasts or {}).get("podcasts", []) if e.get("transcript")),
            "central_x_summaries": len((central_summaries or {}).get("x", [])),
            "central_podcast_summaries": len((central_summaries or {}).get("podcasts", [])),
            "central_paper_summaries": len((central_summaries or {}).get("papers", [])),
            "x_builders": len((feed_x or {}).get("x", [])),
            "total_tweets": sum(len(a.get("tweets", [])) for a in (feed_x or {}).get("x", [])),
            "arxiv_papers": len(papers),
        },
        "prompts": prompts,
        "errors": errors if errors else None,
    }

    sys.stdout.write(json.dumps(clean_data(output), ensure_ascii=True, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
