"""Checks an answer against what the agent actually retrieved.
Same idea as the job copilot: cited evidence only, plus a number check."""
import re

from .llm import ask_json
from .sources import load_programs

JUDGE_SYSTEM = """You audit a benefits answer. Given a STATEMENT about a government
program and the OFFICIAL TEXT it cites, decide:
- "supported": everything stated is in the official text
- "partial": the core is supported but something is stretched, added, or overconfident
- "unsupported": a key fact (rule, amount, deadline, eligibility) is not in the text
The text may be in English or French. Return JSON: {"verdict": "...", "problem": "..."}"""

THOUSANDS = re.compile(r"(?<=\d)[,\s\u00a0\u202f](?=\d{3}(?!\d))")
NUM = re.compile(r"\d+")


def numbers(text: str) -> set[str]:
    return set(NUM.findall(THOUSANDS.sub("", text)))


def verify(answer: dict, trace: dict, judge: bool = True) -> dict:
    programs = load_programs()
    retrieved = trace["retrieved"]
    checks = []

    for p in answer["programs"]:
        cited = p["sources"]
        fake = [c for c in cited if c not in retrieved]
        real_text = "\n\n".join(retrieved[c]["text"] for c in cited if c in retrieved)
        claim = f"{p['why']} {p['next_step']}"
        check = {
            "program_id": p["program_id"],
            "fit": p["fit"],
            "known_program": p["program_id"] in programs,
            "invented_citations": fake,
            "unbacked_numbers": sorted(numbers(claim) - numbers(real_text)) if real_text else [],
            "wrong_language_sources": [c for c in cited if c in retrieved
                                       and f"-{answer['language']}-" not in c],
        }
        if not real_text:
            check.update(verdict="unsupported", problem="no valid citations")
        elif judge:
            check.update(ask_json(JUDGE_SYSTEM, f"STATEMENT: {claim}\n\nOFFICIAL TEXT:\n{real_text}"))
        else:
            check.update(verdict="not_judged", problem="")
        if check["unbacked_numbers"] and check["verdict"] == "supported":
            check.update(verdict="partial",
                         problem=f"numbers not in sources: {check['unbacked_numbers']}")
        checks.append(check)

    n = len(checks) or 1
    return {
        "checks": checks,
        "grounded": round(sum(c["verdict"] == "supported" for c in checks) / n, 2),
        "invented_citations": sum(len(c["invented_citations"]) for c in checks),
        "unknown_programs": [c["program_id"] for c in checks if not c["known_program"]],
        "questions_asked": len(trace["questions"]),
    }
