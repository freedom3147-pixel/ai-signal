# Central summary generation

`scripts/generate_summaries.py` is the central LLM cache layer.

It reads:

- `feeds/feed-podcasts.json`
- `feeds/feed-arxiv.json`
- `config/summary.json`

It writes:

- Markdown summaries under `content/summaries/`
- A machine-readable index at `feeds/feed-summaries.json`

## Profiles

Summary profiles live in `config/summary.json`.

Examples:

- `zh_short`: short Chinese podcast briefs, no paper summaries
- `zh_standard`: standard Chinese podcast and paper briefs
- `zh_deep`: longer Chinese podcast and paper briefs
- `en_standard`: standard English briefs
- `bilingual_short`: short bilingual podcast briefs

Users can choose a profile later. The central repo only has to generate the
preconfigured profiles once per new item.

Podcast and paper length can be controlled separately with
`podcast_target_chars` and `paper_target_chars`. This keeps podcast briefs rich
while preventing arXiv abstract summaries from becoming artificially long.

## Run locally

Check planned work without calling the LLM:

```bash
python scripts/generate_summaries.py --dry-run --limit 1
```

Generate one Chinese standard item per content type:

```bash
set ARK_API_KEY=your_key_here
python scripts/generate_summaries.py --profile zh_standard --limit 1
```

On PowerShell:

```powershell
$env:ARK_API_KEY = "your_key_here"
python scripts/generate_summaries.py --profile zh_standard --limit 1
```

For GitHub Actions, save the key as a repository secret named `ARK_API_KEY`.

## Notes

- Full podcast transcripts are used as temporary input only.
- The script stores small Markdown summaries, not full transcripts.
- Existing summaries are reused when the source text, model, and profile config
  have not changed.
- `httpx` is called with `trust_env=False` to avoid local proxy environment
  variables breaking Ark requests.
