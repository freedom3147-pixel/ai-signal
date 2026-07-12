# Central summary generation

`scripts/generate_summaries.py` is the central LLM cache layer. It is a
legacy/debug path — the documented user flow (see `SKILL.md`) has the Agent
read `feeds/*.json` directly and remix a digest itself, so most users never
need this.

It reads:

- `feeds/feed-x.json`
- `feeds/feed-podcasts.json`
- `config/summary.json`

It writes:

- Markdown summaries under `content/summaries/`
- A machine-readable index at `feeds/feed-summaries.json`

## Profiles

Summary profiles live in `config/summary.json`.

Examples:

- `zh_short`: short Chinese briefs
- `zh_standard`: standard Chinese briefs
- `zh_deep`: longer Chinese briefs
- `en_standard`: standard English briefs
- `bilingual_short`: short bilingual briefs

Users can choose a profile later. The central repo only has to generate the
preconfigured profiles once per new item.

## Run locally

Check planned work without calling the LLM:

```bash
python scripts/generate_summaries.py --dry-run --limit 1
```

Generate one Chinese standard item per content type:

```bash
set DEEPSEEK_API_KEY=your_deepseek_key_here
set ARK_API_KEY=your_ark_key_here
python scripts/generate_summaries.py --profile zh_standard --limit 1
```

On PowerShell:

```powershell
$env:DEEPSEEK_API_KEY = "your_deepseek_key_here"
$env:ARK_API_KEY = "your_ark_key_here"
python scripts/generate_summaries.py --profile zh_standard --limit 1
```

For GitHub Actions, save the keys as repository secrets named
`DEEPSEEK_API_KEY` and `ARK_API_KEY`.

The default setup uses DeepSeek for podcast summaries and Ark/Doubao for X
summaries. You can override each content type with `x_llm` or `podcasts_llm`
in `config/summary.json`.

## Notes

- Full podcast transcripts are used as temporary input only.
- The script stores small Markdown summaries, not full transcripts.
- Existing summaries are reused when the source text, model, and profile config
  have not changed.
- `httpx` is called with `trust_env=False` to avoid local proxy environment
  variables breaking Ark requests.
