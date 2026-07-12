# Digest Format

You are assembling a Macro Signal digest from the JSON prepared by
`prepare_digest.py`. This is a macro-economics / China-economy / markets
signal tracker — not an AI-industry newsletter.

## Overall Shape

Start with:

`宏观信号 (Macro Signal) - [Date]`

Then use this order:

1. X / Twitter
2. Podcasts
3. Research & Policy Blogs (BIS, NY Fed, NBER, and China-watcher
   newsletters such as Sinocism, ChinaTalk, Pekingnology, Baiguan)

Only include sections that have relevant content.

## Item IDs and Follow-up Expansion

Give every included item a stable, visible ID in the heading or first line:

- X / Twitter items: `X1`, `X2`, `X3`
- Podcast items: `P1`, `P2`, `P3`
- Blog/research items: `B1`, `B2`, `B3`

End the digest with a short note telling the user they can ask follow-up
questions such as "expand P2", "详细讲讲 B1", or "这条 X1 为什么重要？".

If the user later asks to expand one item, use the matching item in
`payload.json`; for podcasts, read `transcript_file` when present before
answering. Do not browse the web.

## Opening

Write a short 2-3 sentence opening that names the strongest signal or the
sharpest tension across today's sources — a data release, a policy shift, a
disagreement between analysts, a capital-flow move. Do not list everything.
Frame the day around one question or tension worth watching.

## Source Rules

- Use only content found in the JSON.
- Every included item must have its original link.
- Do not visit websites, search the web, or call APIs.
- Do not invent quotes, metrics, data points, or claims.
- Include items related to: global macro (rates, inflation, growth, labor
  markets), China's economy and policy, trade/tariffs/supply chains, currency
  and capital flows, sovereign debt, credit and banking, commodities, and
  markets/investing commentary from the tracked analysts. Skip items that are
  purely personal, promotional, or unrelated to any of the above.
- When named analysts disagree (e.g. Setser vs. Pettis on capital flows, or a
  podcast guest pushing back on consensus), surface the disagreement — do not
  flatten it into one consensus view.

## Formatting

- Keep the digest readable on a phone.
- Prefer short paragraphs and clean section headings.
- Do not wrap the final digest in a Markdown code fence.
- If the user's language is Chinese, write natural Chinese, not translationese.
- End with the follow-up note, then: `Generated through Macro Signal: https://github.com/freedom3147-pixel/ai-signal`
