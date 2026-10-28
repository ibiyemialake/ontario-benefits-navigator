# Ontario Benefits Navigator

I'm a new immigrant to Canada, and working out what I could apply for was harder
than it should be. The information is public, but it's spread across canada.ca and
ontario.ca, and every page assumes you already know the program's name. I didn't. I
just knew what had changed in my life.

So you start there: "we just moved to Ontario with two kids" or "I got laid off". It
asks a couple of follow-up questions, then tells you which programs probably fit,
each with a link to the official page. English or French.

## How it works

`ingest` pulls the official pages for 7 programs, finds each page's French version
by itself, chunks everything and stores it in a local Chroma index with the fetch date.

The agent is a Claude tool-use loop with three tools: search the pages, ask one
follow-up question (max 3), or answer. Every program in the answer has to cite the
chunks it came from.

Before you see anything, a checker flags made-up citations and numbers that aren't
in the sources, and a second Claude call judges whether each explanation is actually
supported. Anything rated unsupported gets held back.

## The evals

The part I'm proudest of. 6 scenarios in English and French, each listing the
programs that should come up and ones that shouldn't (someone pregnant in Montreal
should *not* get pointed to EI maternity, Quebec runs its own). A simulated person
answers follow-ups from a fixed set of facts, so runs are comparable.

Latest run (Oct 2026, Claude Sonnet 5.5):

| recall | false positives | invented citations | right language | fully grounded |
|---|---|---|---|---|
| 1.00 | 0 | 0 | 6/6 | 0.33 |

Right programs every time, no made-up citations. Grounding is the weak spot: only a
third are fully supported, the rest are "partial", core right but a detail stretched, like "if you or your partner
have been working, you may qualify" when each parent needs their own 600 hours.

## Stack

Python, Claude (Anthropic SDK), ChromaDB, requests + BeautifulSoup. Embeddings are
`paraphrase-multilingual-MiniLM-L12-v2` because Chroma's default is English-only, so
French questions weren't finding French text. Programs and scenarios live in YAML,
so adding a program doesn't mean touching code.

## Running it

    python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...
    python -m navigator.ingest      # fetches the pages + French versions, ~2 min
    python main.py                  # try: "I'm having a baby in March"
    python -m evals.run_evals       # run all scenarios

Re-run `ingest` every month or so. Amounts change (the Ontario Child Benefit page
showed two different yearly maximums while I was building this), and every answer
shows when its sources were checked.

On an Intel Mac torch stops at 2.2.2, which is why `transformers` is pinned.

## Limits

General information, not eligibility decisions. Federal and Ontario only; Quebec and
other provinces get flagged. Only as current as the last ingest.

## What's next

- Get grounding above 0.33, one prompt change at a time with an eval run after each.
- ~20 scenarios with awkward cases: quitting vs. laid off, self-employed parents,
  work permits.
- More programs: Canada Dental Care Plan, Canada Workers Benefit, Ontario Trillium
  Benefit, OSAP.
- A simple Streamlit chat page.
- Follow-up questions after the answer. Right now it's one-shot. <!-- noticed in code, check -->
- Re-ingest only pages that changed instead of rebuilding the index. <!-- noticed in code, check -->
