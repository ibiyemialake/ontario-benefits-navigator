"""Run every scenario end to end and score it.

Metrics per scenario:
  recall       share of expected programs the agent listed as likely/possible
  false_pos    must_not programs it listed as likely/possible (should be none)
  grounded     share of program explanations the judge rates fully supported
  invented     citations to chunks it never retrieved (should be 0)
  lang_ok      answer language matches the person's, and sources are in that language
  questions    follow-ups asked (fewer is better, if recall holds)

Usage:  python -m evals.run_evals            (all)
        python -m evals.run_evals baby_fr    (one)
"""
import json
import sys
from pathlib import Path

import yaml

from navigator.agent import run
from navigator.llm import ask_text
from navigator.verify import verify


def simulated_person(persona: str, lang: str):
    lang_name = "French" if lang == "fr" else "English"
    def answer(question: str) -> str:
        return ask_text(
            f"You are a person asking about government benefits. Facts about you: {persona}\n"
            f"Answer the question in one short sentence in {lang_name}. Use only these facts. "
            f"If they don't cover it, say you're not sure.", question, max_tokens=100)
    return answer


def score(case: dict) -> dict:
    answer, trace = run(case["opening"], simulated_person(case["persona"], case["lang"]))
    report = verify(answer, trace)
    listed = {p["program_id"] for p in answer["programs"] if p["fit"] in ("likely", "possible")}
    expected, must_not = set(case["expected"]), set(case.get("must_not", []))
    wrong_lang = sum(len(c["wrong_language_sources"]) for c in report["checks"])
    return {
        "id": case["id"],
        "recall": round(len(listed & expected) / len(expected), 2),
        "missed": sorted(expected - listed),
        "false_pos": sorted(listed & must_not),
        "grounded": report["grounded"],
        "invented": report["invented_citations"],
        "lang_ok": answer["language"] == case["lang"] and wrong_lang == 0,
        "questions": report["questions_asked"],
        "_answer": answer, "_report": report, "_trace_questions": trace["questions"],
    }


def main(only: str | None = None):
    cases = yaml.safe_load(Path("evals/scenarios.yaml").read_text(encoding="utf-8"))
    cases = [c for c in cases if not only or c["id"] == only]
    rows = [score(c) for c in cases]

    Path("evals/results").mkdir(exist_ok=True)
    Path("evals/results/latest.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))

    print(f"{'scenario':18} {'recall':>6} {'grounded':>8} {'inv':>4} {'lang':>5} {'q':>2}  issues")
    for r in rows:
        issues = ([f"missed {r['missed']}"] if r["missed"] else []) + \
                 ([f"FALSE POS {r['false_pos']}"] if r["false_pos"] else [])
        print(f"{r['id']:18} {r['recall']:>6} {r['grounded']:>8} {r['invented']:>4} "
              f"{'✓' if r['lang_ok'] else '✗':>5} {r['questions']:>2}  {'; '.join(issues) or '-'}")
    n = len(rows)
    print(f"\nAVG recall {sum(r['recall'] for r in rows)/n:.2f} | "
          f"AVG grounded {sum(r['grounded'] for r in rows)/n:.2f} | "
          f"false positives {sum(len(r['false_pos']) for r in rows)} | "
          f"invented citations {sum(r['invented'] for r in rows)} | "
          f"language {sum(r['lang_ok'] for r in rows)}/{n}")
    print("Full answers saved to evals/results/latest.json")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
