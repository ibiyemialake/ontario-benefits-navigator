"""The agent: Claude decides when to search, when to ask a follow-up question,
and when it knows enough to answer. Every claim must cite chunk ids it retrieved."""
from typing import Callable

from . import llm
from .search import search
from .sources import load_programs

MAX_STEPS = 15
MAX_QUESTIONS = 3

TOOLS = [
    {
        "name": "search_official_sources",
        "description": "Search official canada.ca and ontario.ca pages. Returns chunks with "
                       "chunk_id, program_id, url and text. Search in the user's language.",
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string"},
            "lang": {"type": "string", "enum": ["en", "fr"]}},
            "required": ["query", "lang"]},
    },
    {
        "name": "ask_user",
        "description": "Ask the person ONE short follow-up question, only when the answer "
                       "would change which programs fit. Returns their reply.",
        "input_schema": {"type": "object", "properties": {"question": {"type": "string"}},
                         "required": ["question"]},
    },
    {
        "name": "final_answer",
        "description": "Give the final answer. Call once, at the end.",
        "input_schema": {"type": "object", "properties": {
            "language": {"type": "string", "enum": ["en", "fr"]},
            "summary": {"type": "string", "description": "1–2 sentences, user's language"},
            "programs": {"type": "array", "items": {"type": "object", "properties": {
                "program_id": {"type": "string"},
                "fit": {"type": "string", "enum": ["likely", "possible", "unlikely"]},
                "why": {"type": "string"},
                "next_step": {"type": "string"},
                "sources": {"type": "array", "items": {"type": "string"},
                            "description": "chunk_ids that support why and next_step"}},
                "required": ["program_id", "fit", "why", "next_step", "sources"]}},
            "not_covered": {"type": "string",
                            "description": "What this tool can't answer for them, plainly"}},
            "required": ["language", "summary", "programs", "not_covered"]},
    },
]


def system_prompt() -> str:
    catalog = "\n".join(f"- {p['id']} ({p['level']}): {p['name_en']} / {p['name_fr']} "
                        f"— life events: {', '.join(p['life_events'])}"
                        for p in load_programs().values())
    return f"""You help people in Ontario find federal and Ontario government programs
that fit a change in their life (lost a job, having a baby, moved to Ontario).

Programs in your knowledge base:
{catalog}

How to work:
1. Read the person's situation. If a detail would change which programs fit
   (province, children, how they left a job, immigration status), ask with ask_user.
   At most {MAX_QUESTIONS} questions; never ask what they already told you.
2. Search the official sources for every program that might fit. Search in the
   person's language.
3. Call final_answer. Rules for it:
   - Use ONLY facts from chunks you retrieved. Cite their chunk_ids in "sources".
   - Never invent amounts, dates, hour thresholds or rules. If a number isn't in a
     chunk, leave it out.
   - Never say someone IS eligible. Use fit: likely / possible / unlikely, and say
     the government makes the final decision.
   - Include a program as "unlikely" only when explaining why matters
     (e.g. Quebec runs its own parental benefits).
   - Write summary, why, next_step and not_covered in the person's language
     (French if they wrote in French).
   - not_covered: say plainly what's outside your sources (other provinces,
     municipal programs, tax advice).
If the person seems to be in urgent need (no money for food or rent), put Ontario
Works first if your sources support it."""


def run(opening: str, answer_fn: Callable[[str], str]) -> tuple[dict, dict]:
    """Returns (final_answer, trace). trace records what was retrieved and asked,
    so verify.py can check citations against it."""
    messages = [{"role": "user", "content": opening}]
    trace = {"retrieved": {}, "questions": [], "searches": []}

    for _ in range(MAX_STEPS):
        resp = llm.client.messages.create(model=llm.MODEL, max_tokens=3000,
                                          system=system_prompt(), tools=TOOLS,
                                          messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        calls = [b for b in resp.content if b.type == "tool_use"]
        if not calls:
            messages.append({"role": "user", "content": "Please continue using the tools, "
                             "and finish with final_answer."})
            continue

        results = []
        for call in calls:
            if call.name == "final_answer":
                return call.input, trace
            if call.name == "search_official_sources":
                hits = search(call.input["query"], call.input["lang"])
                trace["searches"].append(call.input)
                for h in hits:
                    trace["retrieved"][h["chunk_id"]] = h
                content = "\n\n".join(f"[{h['chunk_id']}] ({h['program_id']}, {h['url']})\n"
                                      f"{h['text']}" for h in hits) or "No results."
            elif call.name == "ask_user":
                if len(trace["questions"]) >= MAX_QUESTIONS:
                    content = "Question limit reached. Answer with what you have."
                else:
                    reply = answer_fn(call.input["question"])
                    trace["questions"].append({"q": call.input["question"], "a": reply})
                    content = reply
            else:
                content = f"Unknown tool {call.name}"
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": content})
        messages.append({"role": "user", "content": results})

    raise RuntimeError("Agent did not finish within the step limit.")
