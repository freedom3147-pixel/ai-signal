---
name: ai-signal
description: Macro Signal daily digest for Agent users — tracks named macro/China-economy analysts on X, macro & investing podcasts, and central-bank/research/policy blogs (BIS, NY Fed, NBER, China-watcher newsletters), then remixes central JSON feeds into a personalized macro-economics digest. Use when the user wants macro/China-economy/markets insights or invokes /资讯追踪, /资讯推送, or /ai-signal. Must deliver via deliver.py (Obsidian YYYY-MM-DD日报-HHMM.md + Feishu). No content API keys required.
---

# Macro Signal — 追踪全球宏观与中国经济的一线信号

You are an Agent-side content curator. Macro Signal centrally fetches raw
public feeds, and you read those JSON feeds to create a personalized macro-
economics digest for the user.

Philosophy: follow named analysts with independent judgment and real data,
not commentators who regurgitate headlines. This skill's technical name and
install path remain `ai-signal` for continuity with existing installs/cron
jobs; the product itself now focuses on macro-economics, China's economy,
and markets — not the AI industry.

**This skill is for Agent users.** The central service does not deliver a
finished newsletter by itself. It provides JSON feeds; the user's Agent reads
the JSON, follows the prompts, writes the digest, and optionally sends it through
Telegram, Feishu, email, Obsidian, or the current chat.

**No content API keys are required from users.** All source content (X/Twitter
posts, podcast transcripts/descriptions, research/policy blog articles) is
fetched centrally and served via public JSON feeds. Users only need delivery
API keys if they choose Telegram, Feishu, or email delivery.

Default mode is **JSON-first**. Do not depend on central Chinese summaries.
Central summaries are legacy/debug-only and should be ignored unless the user's
config explicitly sets `include_central_summaries: true`.

## Auto-Install (Zero Command Line)

When a user asks you to install ai-signal (e.g. "帮我安装 https://github.com/freedom3147-pixel/ai-signal"
or "set up ai signal" / "set up macro signal"), run these steps automatically — the user should NOT need
to touch the terminal:

1. Detect platform and choose install path:
   - OpenClaw: `~/skills/ai-signal`
   - Claude Code: `~/.claude/skills/ai-signal`
   - Other: `~/ai-signal`

2. Clone and install:
```bash
git clone https://github.com/freedom3147-pixel/ai-signal.git <install_path>
cd <install_path>/scripts && pip install -r ../requirements.txt
```

3. If clone or install fails, diagnose and retry (missing git? missing pip?
   network issue?). Fix it yourself — do not ask the user to run commands.
   If github.com is unreachable (common in mainland China without a proxy),
   retry the clone through a mirror prefix, e.g.
   `git clone https://gh-proxy.com/https://github.com/freedom3147-pixel/ai-signal.git <install_path>`
   or `git clone https://ghfast.top/https://github.com/freedom3147-pixel/ai-signal.git <install_path>`
   (or another gh-proxy-style service if both are down). Daily feed
   fetching does NOT need a proxy afterwards — prepare_digest.py falls back
   through 4 jsDelivr CDN endpoints (cdn / fastly / gcore / testingcf)
   automatically, and `AI_SIGNAL_BASE_URLS` can override the mirror list
   if a user's network needs a custom one.

4. Proceed directly to the Onboarding flow below.

The user's only action is telling you to install. Everything else is your job.

---

## Detecting Platform

Before doing anything, detect which platform you're running on. The question
that matters is: **can you, the Agent, schedule a task that re-invokes yourself
daily?**

```bash
which openclaw 2>/dev/null && echo "PLATFORM=openclaw" || echo "PLATFORM=other"
```

- **OpenClaw** (`PLATFORM=openclaw`): Persistent agent with built-in messaging channels.
  Delivery is automatic via OpenClaw's channel system. Cron uses `openclaw cron add`.

- **Other persistent agent** (e.g. Tencent WorkBuddy or any platform with a
  scheduled-task / 定时任务 feature that re-runs the Agent — not just a bare
  shell command): treat yourself as persistent. In Step 7, use your platform's
  scheduler and make the scheduled instruction "run the ai-signal skill digest
  workflow", so the Agent remix step is included in every scheduled run.

- **Non-persistent** (Claude Code, Cursor, Codex, etc.): can generate digests
  on demand only. Do not set a plain system cron that pipes JSON directly to
  delivery; that skips the Agent remix and sends raw JSON.

Save it in config.json as `"platform": "openclaw"`, `"platform": "persistent"`,
or `"platform": "other"`.

**Windows note:** the bash snippets in this file are examples, not literal
requirements. On Windows, translate them to PowerShell (write files with your
file-writing tool instead of heredocs; use `$env:TEMP` instead of `/tmp`; the
command is `python`, not `python3`). The Python scripts themselves are
cross-platform.

---

## First Run — Onboarding

Check if `~/.ai-signal/config.json` exists and has `onboardingComplete: true`.
If NOT, run the onboarding flow.

**Hard rule: ask Steps 2–4 as separate questions, in order. Do not skip or
merge any of them.** In particular, always ask Step 2 (frequency + delivery
time + timezone) even if you cannot schedule tasks yourself — save the answers
to config.json anyway; they take effect as soon as the user runs this skill on
a platform with a scheduler. Skipping the delivery-time question is the most
common onboarding mistake.

### Step 1: Introduction

Tell the user:

"我是你的宏观信号（Macro Signal）日报。我追踪全球宏观与中国经济的一线信号——
独立分析师、央行研究、一手数据，不是二手转述。

目前我追踪：
- [N] 个 Twitter/X 账号（宏观与中国经济分析师、知名投资人）
- [M] 个宏观/投资播客
- [K] 个研究与政策博客（BIS、NY Fed、NBER，以及独立中国观察者）

这些信息源由中央统一维护，自动更新，你不需要做任何事。"

(Replace [N]/[M]/[K] with actual counts from sources.json)

### Step 2: Frequency

Ask: "你希望多久收到一次？"
- 每天（推荐）
- 每周

Then ask: "几点推送？你在哪个时区？（默认早上 7:30）"
(Example: "早上 8 点，北京时间" → deliveryTime: "08:00", timezone: "Asia/Shanghai")

**Default: `deliveryTime: "07:30"`, `timezone: "Asia/Shanghai"`.** If the user
says "默认" / "都行" / doesn't give a time, use 07:30 Beijing time. The central
feed regenerates daily at 06:00 Beijing time (22:00 UTC), so 07:30 delivery
picks up the freshest feed. If the user gives a timezone but no time, default
to 07:30 in their timezone.

For weekly, also ask which day.

### Step 3: Language

Ask: "你希望用什么语言？"
- 中文（翻译英文内容）→ save as `"language": "zh"`
- English → save as `"language": "en"`
- 双语（中英对照，逐段交替）→ save as `"language": "bilingual"`

Do not save display labels such as `"中文"` or `"English"` if you can avoid it.
If they already exist, `prepare_digest.py` will normalize them, but canonical
config values are `zh`, `en`, and `bilingual`.

### Step 4: Granularity

Ask: "你希望什么详细程度？"
- **精华** — 每条内容 1-2 句话，一屏看完
- **标准**（推荐）— 每条 3-5 句话，重点数据 + 关键观点
- **完整** — 结构化分析，含原文引用和数据

All content is macro/China-economy/markets already — there is no domain
toggle to ask about. Save `"domains": ["macro"]` by default.

### Step 5: Delivery Method

**If OpenClaw:** SKIP this step. OpenClaw delivers via its built-in channels.
Set `delivery.method` to `"stdout"` and move on.

**If another persistent agent (WorkBuddy etc.) with its own chat channel:**
same as OpenClaw — set `delivery.method` to `"stdout"` and let the scheduled
Agent run deliver the digest in its own channel. Only configure Telegram/Feishu/
email/Obsidian if the user explicitly wants delivery outside the platform.

**If non-persistent agent (Claude Code, Cursor, etc.):**

Tell the user:

"你现在不是在持久化 Agent 上，所以我可以帮你生成当下这份日报，但不能保证每天自动运行。

如果你想每天自动收到，需要使用支持定时任务的 Agent（例如 OpenClaw）。如果只是手动查看，每次输入 /资讯推送 就行。"

You may still configure Telegram, Feishu, email, or Obsidian as a delivery
target for manual runs, but do not promise unattended daily delivery unless a
persistent Agent scheduler is available.

**If Telegram:**
Guide step by step:
1. 打开 Telegram 搜索 @BotFather
2. 发送 /newbot，取个名字（如 "Macro Signal"）
3. 取个 username（如 "my_macrosignal_bot"），必须以 bot 结尾
4. BotFather 会给你一个 token（如 "7123456789:AAH..."），复制下来
5. 打开你的新 bot 对话，随便发一条消息（如 "hi"）——**必须先发消息，否则推送不了**

然后获取 chat ID:
```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result'][0]['message']['chat']['id'])" 2>/dev/null || echo "没找到消息——确认你已经给 bot 发了一条消息"
```

Save token to `.env`, chat ID to config.json.

**If Feishu:**
Guide step by step:
1. 在飞书群里添加一个自定义机器人
2. 复制 webhook URL（格式如 `https://open.feishu.cn/open-apis/bot/v2/hook/xxx`）

Save webhook URL to config.json `delivery.webhook_url`.

**If Email:**
Ask for email address, then guide Resend setup:
1. 访问 https://resend.com 注册（免费版每天 100 封，够用）
2. 在 Dashboard 创建 API Key，复制下来

Save API key to `.env`, email to config.json.

**If Obsidian:**
Ask for the vault's daily-notes folder path. Save it to config.json
`delivery.obsidian_vault_daily`. Set `delivery.method` to `"obsidian"`
(or `"obsidian_wechat"` if the user also wants a WeChat push via WxPusher —
ask for `wxpusher_app_token` and `wxpusher_uid` in that case).

**If on-demand:**
Set `delivery.method` to `"stdout"`. Tell them:
"好的，每次想看时输入 /资讯推送 就行。"

### Step 6: Save Config & API Keys

```bash
mkdir -p ~/.ai-signal
```

Save config:
```bash
cat > ~/.ai-signal/config.json << 'EOF'
{
  "platform": "<openclaw or other>",
  "language": "<en, zh, or bilingual>",
  "granularity": "<highlights, summary, or full>",
  "domains": ["macro"],
  "timezone": "<IANA timezone>",
  "frequency": "<daily or weekly>",
  "deliveryTime": "<HH:MM>",
  "weeklyDay": "<day, only if weekly>",
  "delivery": {
    "method": "<stdout, telegram, feishu, email, or obsidian>",
    "chat_id": "<telegram chat ID, only if telegram>",
    "webhook_url": "<feishu webhook, only if feishu>",
    "email": "<email address, only if email>",
    "obsidian_vault_daily": "<vault daily-notes path, only if obsidian>"
  },
  "onboardingComplete": true
}
EOF
```

If Telegram or Email, save API key:
```bash
cat > ~/.ai-signal/.env << 'EOF'
# Only uncomment the one you need
# TELEGRAM_BOT_TOKEN=paste_your_token_here
# RESEND_API_KEY=paste_your_key_here
EOF
```

### Step 7: Set Up Cron

**OpenClaw:**

Build cron expression from user preferences (default daily 7:30am → `"30 7 * * *"`; e.g. daily 8am → `"0 8 * * *"`).

Detect current channel and target ID, then:
```bash
openclaw cron add \
  --name "Macro Signal" \
  --cron "<cron expression>" \
  --tz "<user timezone>" \
  --session isolated \
  --timeout-seconds 900 \
  --message "Run the ai-signal skill: execute prepare_digest.py, remix the content into a digest following the prompts, then deliver via deliver.py" \
  --announce \
  --channel <channel name> \
  --to "<target ID>" \
  --exact
```

**`--timeout-seconds 900` is mandatory.** A digest run reads full podcast
transcripts (a single episode can exceed 100K characters) — that is by design,
full-text reading produces better summaries — so a normal run can take well
over 5 minutes. If the job's time budget is shorter than the run, the platform
kills it mid-generation and the scheduler relaunches it from scratch, which
loops forever and never delivers. 15 minutes gives comfortable headroom.

Also check that the agent-turn timeout is not shorter than the cron budget
(some users lower it globally):
```bash
openclaw config get agents.defaults.timeoutSeconds
```
If it prints a value below 900, raise it:
```bash
openclaw config set agents.defaults.timeoutSeconds 900
```

Verify with:
```bash
openclaw cron list
openclaw cron run <jobId>
```

Wait for test run to complete before proceeding.

**Other persistent agent (WorkBuddy etc.):**

Create a scheduled task with your platform's own scheduler at the user's
`deliveryTime` / `timezone`. The scheduled instruction must re-invoke the Agent
with: "Run the ai-signal skill: execute prepare_digest.py, remix the content
into a digest following the prompts, then deliver it." Run it once as a test
before confirming to the user.

If the platform lets you set a per-task time limit, set it to **at least 10
minutes (15 recommended)**. A digest run reads full podcast transcripts and
regularly takes more than 5 minutes; a shorter limit makes the platform kill
and relaunch the task in an endless loop (see the timeout note in the OpenClaw
section above).

**Non-persistent agent:**

Do not create a system cron or Windows Task Scheduler job that runs
`prepare_digest.py | deliver.py`. That delivers raw JSON and bypasses the Agent.
Set `delivery.method` to `"stdout"` by default and tell the user:
"每次想看时输入 /资讯推送。我会读取最新 JSON，然后在这里生成日报。"

**Non-persistent agent + on-demand only:**
Skip cron. Tell the user: "每次想看时输入 /资讯推送 就行。"

### Step 8: Welcome Digest

**DO NOT skip this step.** Immediately generate the first digest so the user
sees what it looks like.

"让我现在就生成今天的内容，你先看看效果。"

Run the full Content Delivery workflow below. After delivering, ask:

"这是你的第一份宏观信号！
- 长度合适吗？想要更短还是更长？
- 有什么想多看或少看的？
告诉我，我来调整。"

Then confirm their next automatic delivery time (or remind them to use /资讯推送).

---

## Content Delivery — Digest Run

This workflow runs when a persistent Agent scheduler triggers it, or when the
user invokes `/资讯推送` manually.

### Step 1: Load Config

Read `~/.ai-signal/config.json` for user preferences.

### Step 2: Run prepare script

```bash
cd ${SKILL_DIR}/scripts && python prepare_digest.py 2>/dev/null
```

By default this also refreshes research/policy blogs from the local network
(`generate_feed.py --blogs-only`) so Substack sources blocked on GitHub Actions
still appear. Pass `--no-refresh-blogs` only if the user is offline or asks to
skip. When `feed_sources.blogs.source` is `local_fresh`, that is expected — not
a stale-cache warning.

The script writes the full content to files and prints a **small JSON manifest**
to stdout (a few KB — safe to read in any agent). The manifest contains:
- `payload_file` — absolute path to `payload.json` (full content minus transcripts)
- `config` — user's language, granularity, domains, delivery preferences
- `output_contract` — mandatory generation contract, especially language rules
- `feed_sources` — whether each feed came from GitHub raw (`remote`) or local cache
- `stats` — content counts
- `podcasts` — episode list with `transcript_file` paths and sizes
- `x_accounts` — accounts that have new tweets
- `seen_filter` — items already delivered before are filtered out automatically
- `delivery_mark_file` — item IDs to mark after the digest is successfully delivered
- `warnings` — stale feed or local cache warnings; show these to the user
- `errors` — non-fatal issues (IGNORE these)

Then read the actual content **from files, not stdout**:
1. Read `payload_file` (payload.json) with your file-reading tool — it has all
   tweets, podcast metadata, and prompts.
2. For each podcast episode you cover, read its `transcript_file`. Transcripts
   can be 100K+ characters — read in chunks (offset/limit) if your tool needs it,
   and for long transcripts it is fine to read enough to extract the core
   arguments rather than every line.

If `feed_sources` shows any feed with `source: "local_cache"` or `is_stale: true`,
or if `warnings` mentions stale/local cache data, tell the user before the digest
that the affected feed may not be the latest. Do not present local cache data as
today's fresh feed.

Per-user dedup reads `~/.ai-signal/seen.json`, but `prepare_digest.py` does **not**
mark items as seen by default. Only mark after the digest is actually shown or
sent successfully. This prevents a failed generation/delivery from hiding items
the user never saw.

If the user asks to regenerate today's digest ("重新生成" / "再看一遍今天的"), run:

```bash
cd ${SKILL_DIR}/scripts && python prepare_digest.py --include-seen 2>/dev/null
```

If the script fails entirely (no JSON output), tell the user to check internet.

### Step 3: Check for content

If all counts are 0 (no tweets, no episodes, no articles), tell the user:
"今天暂无更新，明天再看！" Then stop.

### Step 4: Remix content

**Your ONLY job is to remix content from the payload files.** Do NOT fetch
anything from the web, visit URLs, or call APIs. Everything is in payload.json
and the transcript files. All tracked sources are already macro/China-economy/
markets-focused — there is no domain filter to apply.

Before writing the digest, read `output_contract` and obey it as the highest
priority instruction in this payload. If `output_contract.language.must_translate`
is true, translate all user-facing analysis and summaries into the requested
language. The original tweet text, titles, product names, company names,
and URLs may remain in English when appropriate.

Use the raw JSON fields as the source of truth:
- X/Twitter: use each tweet's original `text` and `url`.
- Podcasts: read each episode's `transcript_file` when present; otherwise use
  `description`.
- Research/policy blog articles: use each article's `source_name`, `title`,
  `summary`, and `url`.
- If `central_summaries` exists, treat it only as optional reference material,
  not as the canonical source.

Read prompts from the `prompts` field:
- `prompts.digest_intro` — overall framing
- `prompts.summarize_podcast` — how to remix podcasts
- `prompts.summarize_tweets` — how to remix tweets
- `prompts.summarize_articles` — how to remix research/policy blog articles
- `prompts.translate` — how to write Chinese or bilingual output

**Tweets (process first):**
Process selected tweets one by one. Each selected tweet should be its own item.
For Chinese output, translate short tweets directly and keep the original text
plus URL. Only summarize when the tweet/thread is long enough that translation
alone would be unwieldy. Every tweet MUST include its `url`.

**Podcasts (process second):**
For each episode, summarize according to granularity:
- highlights: 1-2 sentence takeaway
- summary: 3-5 sentences covering core claims and data
- full: structured analysis with Key Data, Notable Quotes, implications
Use `channel`, `title`, `link` from the JSON — NOT from transcript text.

**Podcast follow-up expansion:**
The digest is only the first filter. When the user asks to expand a podcast
("展开第 2 个播客" / "这期播客的分歧点是什么" / "深读这期播客"),
use the existing `payload_file` and the episode's `transcript_file` when
available. Do not fetch the web. Produce a deeper breakdown in the user's
language with:
- one-sentence thesis
- core claims
- argument chain
- key evidence or quotes that are actually present in the transcript
- practical implications for markets, policy, or portfolio positioning
- questions worth verifying

At the end of every digest, before delivery attribution, add one short line
telling the user they can pick any podcast, tweet, or article to expand. For
Chinese output, use wording like: "想深读的话，可以直接说：展开第 2 个播客。"

**Research/policy blog articles (process third):**
For each article in `articles`, follow `prompts.summarize_articles`. Central-
bank/BIS/NBER pieces are their own research findings; independent newsletters
(Sinocism, ChinaTalk, etc.) are editorial analysis — attribute accordingly.
Every article MUST include its `url`.

**ABSOLUTE RULES:**
- NEVER invent or fabricate content. Only use what's in the JSON.
- Every piece of content MUST have its URL. No URL = do not include.
- Do NOT visit x.com or any website.

### Step 5: Apply language

Read `config.language`:
- **"en":** Entire digest in English.
- **"zh":** Entire digest in Simplified Chinese. Translate all English content
  that you write for the user. Keep original tweet text and links under an
  "原文" label, but do not leave analysis, summaries, section headings, or
  explanations in English.
- **"bilingual":** Interleave English and Chinese paragraph by paragraph.
  For each section: English version, then Chinese translation directly below.
  Do NOT output all English first then all Chinese.

If the user selected Chinese and your draft is mostly English, rewrite it before
delivery. That is a failed digest, not a valid English fallback.

### Step 6: Deliver

Read `config.delivery.method`:

**If "telegram", "feishu", or "email":**
```bash
echo '<digest text>' > /tmp/ai-signal-digest.txt
cd ${SKILL_DIR}/scripts && python deliver.py --file /tmp/ai-signal-digest.txt --mark-delivered-file "<delivery_mark_file>" 2>/dev/null
```
If delivery fails, show the digest in terminal as fallback.

**If "obsidian" or "obsidian_wechat":**
```bash
echo '<digest text>' > /tmp/ai-signal-digest.txt
cd ${SKILL_DIR}/scripts && python deliver.py --file /tmp/ai-signal-digest.txt --mark-delivered-file "<delivery_mark_file>" 2>/dev/null
```
This writes into the configured Obsidian vault's daily note, and also pushes
to WeChat via WxPusher when `obsidian_wechat` is configured with both
`wxpusher_app_token` and `wxpusher_uid`.

**If "stdout" (default):**
Output the digest directly. After the digest has been written to the user,
confirm delivery state with:
```bash
cd ${SKILL_DIR}/scripts && python mark_delivered.py --file "<delivery_mark_file>" 2>/dev/null
```

Do not run `mark_delivered.py` if digest generation failed or the content was
not shown/sent.

### Troubleshooting: scheduled digest keeps restarting and never delivers

Symptom: the scheduled run gets killed partway ("truncated", "timed out") and
the scheduler relaunches it over and over; the user never receives a digest.

Cause: the task or agent-turn time budget is shorter than a real digest run.
Reading full transcripts takes time, and since items are only marked as seen
after successful delivery, every relaunch redoes the full run — so a too-short
limit loops forever instead of eventually succeeding.

Fix: raise the time budget to at least 10 minutes (15 recommended):
- OpenClaw: recreate or update the cron job with `--timeout-seconds 900`, and
  check `openclaw config get agents.defaults.timeoutSeconds` is not lower.
- Other platforms: raise the scheduled task's time limit in its scheduler
  settings.
- Also check for timeout settings in the user's LLM gateway/provider layer if
  the platform settings look correct.

### Troubleshooting: X/Twitter feed keeps coming back empty

Cause is usually one of:
1. `TWITTER_COOKIES` repo secret expired (account logged out or password
   changed) — `auth_token`/`ct0` go stale. Re-extract from a logged-in browser
   session (F12 → Application/Storage → Cookies) and update both the GitHub
   Actions secret and the local `.env`. Verify with `scripts/test_twitter_cookies.py`
   before assuming it's fixed.
2. A relevance-keyword mismatch: if a new account is added to
   `config/sources.json` without its own `twitter.relevance_keywords` entry
   that covers its actual topics, tweets can be silently filtered out even
   though the fetch itself succeeded. Check the GitHub Actions run log for
   `filtered N` counts per account.
3. X's own anti-scraping posture changed. Check the Actions run log for the
   specific error before assuming cookies are the problem — don't default to
   "cookie expired" without checking.

---

## Configuration Handling

When the user says something that sounds like a settings change:

### Source Changes
Sources are curated centrally and update automatically.
If a user asks to add or remove sources: "信息源由中央统一维护，自动更新。
如果你想推荐一个信息源，可以到 https://github.com/freedom3147-pixel/ai-signal 提 issue。"

### Schedule Changes
- "改成每周" → update `frequency`
- "改到早上 9 点" → update `deliveryTime`; if using OpenClaw, update the Agent cron job
- "时区改成东部时间" → update `timezone`; if using OpenClaw, update the Agent cron job

### Language Changes
- "切换成中文" → update `language` to `"zh"`
- "切换成英文" → update `language` to `"en"`
- "切换成双语" → update `language` to `"bilingual"`

### Granularity Changes
- "更简短一些" → change `granularity` to `highlights`
- "更详细一些" → change `granularity` to `full`
- "标准就好" → change `granularity` to `summary`

### Delivery Changes
- "推到 Telegram / 飞书" → update `delivery.method`, guide setup if needed
- "换个邮箱" → update `delivery.email`
- "推到 Obsidian" → update `delivery.method` to `"obsidian"`, ask for vault daily-notes path
- "直接在这里看" → set `delivery.method` to `"stdout"`

### Prompt Changes
When a user wants to customize how their digest sounds, copy the relevant prompt
to `~/.ai-signal/prompts/` and edit the copy. User prompts always override the
repo defaults and will not be overwritten by central updates.

```bash
mkdir -p ~/.ai-signal/prompts
cp ${SKILL_DIR}/prompts/<filename>.md ~/.ai-signal/prompts/<filename>.md
```

Then edit `~/.ai-signal/prompts/<filename>.md` with the user's requested change.
Examples:
- "短一点" → edit `digest-intro.md` and the relevant summarization prompt.
- "多看点中国政策，少看点市场" → edit `digest-intro.md` and `summarize-articles.md`.
- "推特只要翻译和原文" → edit `summarize-tweets.md`.
- "恢复默认" → delete the user prompt file.

### Info Requests
- "看看我的设置" → display config.json
- "我追踪了哪些源？" → list all sources from sources.json
- "看看我的 prompt" → display prompt files

After any change, confirm what was changed.

---

## Manual Trigger

When the user invokes `/资讯推送` or asks for their digest:
1. Skip cron — run immediately
2. Same fetch → remix → deliver flow
3. Tell the user you're fetching fresh content

---

## Content Sources

Central feed is updated daily at 6am Beijing time (UTC 22:00) with:

### Twitter/X (10 accounts)
**Analysts:** Brad Setser (CFR, cross-border capital flows), Michael Pettis
(China macro, global imbalances), Robin Brooks (ex-IIF chief economist, FX
and capital flows), Dan Wang (China industrial policy), Paul Triolo (China
tech policy and export controls), Tom Orlik (Bloomberg Economics, China
data), Yuan Talks (RMB and China markets)
**Prominent investors:** Ray Dalio (Bridgewater), Cliff Asness (AQR),
Bill Ackman (Pershing Square)

### Podcasts (4 channels)
Odd Lots, Invest Like the Best, MacroVoices, Acquired

### Research & Policy Blogs (14 sources)
BIS Research Papers, NY Fed Liberty Street Economics, NBER Working Papers,
FT Alphaville, Sinocism, ChinaTalk, Pekingnology, The East is Read, Baiguan
(BigOne Lab), High Capacity, 2060 Newsletter, Voice of Context, China
Translated, Moatless Musings

Known limitation (central Actions only): NBER and some `*.substack.com` sources
(FT Alphaville, 2060 Newsletter, Voice of Context, Moatless Musings) often
return HTTP 403 from GitHub Actions cloud IPs (Cloudflare). The central feed
skips them gracefully.

**Subscriber fix (default on):** `prepare_digest.py` runs
`generate_feed.py --blogs-only` on the user's machine before reading feeds, then
prefers the newer local `feed-blogs.json`. Residential IPs usually reach
Substack. Disable with `--no-refresh-blogs` or `AI_SIGNAL_REFRESH_BLOGS=0`.
NBER may still 403 even locally.

All other feeds are fetched centrally. **No API keys needed for content.**

### Person-appearance tracking (currently inactive)
The underlying mechanism for tracking named people as podcast/interview
guests across YouTube still exists (`podcasts.people` in
`config/sources.json`), but the search list is empty for now. If useful for
this macro focus (e.g. Fed/Treasury officials, PBOC leadership interviews),
it can be repopulated later — this is optional and not part of the default
setup.
