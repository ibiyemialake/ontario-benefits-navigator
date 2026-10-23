# Ontario Benefits Navigator

Start from what changed in your life, not from a program name. The navigator asks
a few follow-up questions, searches official canada.ca and ontario.ca pages, and
answers in English or French with a source link for every program.

    "I just lost my job" ──► agent asks follow-ups ──► searches official pages (RAG)
                                                            │
       answer with sources ◄── checker holds back anything uncited ◄── final answer

## Setup

    python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...
    python -m navigator.ingest      # fetches ~10 pages + French versions, ~2 min
    python main.py                  # try: "I'm having a baby in March"
    python -m evals.run_evals       # score all 6 scenarios

Re-run `ingest` monthly. Amounts change (the Ontario Child Benefit page showed
two different yearly maximums in recent versions), and each answer shows the
date its sources were checked.

## What carries over from the job copilot

| Job copilot | Navigator |
|---|---|
| Evidence bank with IDs | Official page chunks with IDs |
| Bullets must cite evidence IDs | Programs must cite chunk IDs |
| Judge + number check | Same, plus "did it cite something it never retrieved?" |
| 20 postings + known gaps | 6 scenarios + known right programs |

New here: a real **agent** (Claude chooses between searching, asking a follow-up,
and answering), **multilingual retrieval**, and **web ingestion**.

## Files

| File | What it does |
|---|---|
| `data/sources.yaml` | The programs and official pages. Add programs here. |
| `navigator/ingest.py` | Fetches pages, finds the French version, chunks, indexes |
| `navigator/search.py` | Multilingual search, filtered by language |
| `navigator/agent.py` | Tool-use loop: search / ask_user / final_answer |
| `navigator/verify.py` | Citation, grounding, number and language checks |
| `evals/scenarios.yaml` | Test situations with the correct programs |

## Build plan (weeks 10–15)

**Week 10 — Run it.** Ingest, try 5 situations of your own, read every answer
critically. Look at what got chunked: `index/` is a normal Chroma database.

**Week 11 — Ground truth.** Review `scenarios.yaml` (ideally with someone who
knows these programs), then add to reach ~20 scenarios: edge cases like quitting
vs. being laid off, self-employed parents, someone on a work permit.

**Week 12 — Baseline and improve.** Run evals, write down the numbers, then change
one thing at a time (chunk size, k, the system prompt) and rerun. Keep the table.

**Week 13 — Widen coverage.** Add programs (Canada Dental Care Plan, Canada
Workers Benefit, Ontario Trillium Benefit, OSAP) and a fourth life event.
Re-run evals to make sure nothing regressed.

**Week 14 — Web UI.** A simple Streamlit chat page.

**Week 15 — Ship.** Short demo video, LinkedIn post with your eval table,
CV bullet.

## Limits (say these out loud in interviews, they show judgment)

- General information, not eligibility decisions.
- Federal + Ontario only. Quebec and other provinces are flagged as not covered.
- Only as current as the last ingest.
