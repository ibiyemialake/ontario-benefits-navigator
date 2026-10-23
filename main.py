"""Interactive navigator.  Usage:  python main.py
Type your situation in English or French."""
from navigator.agent import run
from navigator.sources import load_programs
from navigator.verify import verify

LABELS = {
    "en": {"likely": "Likely fits", "possible": "Might fit", "unlikely": "Probably not",
           "next": "Next step", "src": "Sources", "fetched": "checked",
           "nc": "What I can't help with", "disc": "This is general information, not a "
           "decision. The government decides eligibility when you apply."},
    "fr": {"likely": "Correspond probablement", "possible": "Pourrait correspondre",
           "unlikely": "Probablement pas", "next": "Prochaine étape", "src": "Sources",
           "fetched": "vérifié le", "nc": "Ce que je ne couvre pas", "disc": "Ceci est de "
           "l'information générale, pas une décision. Le gouvernement détermine "
           "l'admissibilité lorsque vous présentez une demande."},
}
ORDER = {"likely": 0, "possible": 1, "unlikely": 2}


def render(answer: dict, trace: dict) -> str:
    lang = answer["language"]
    L, programs = LABELS[lang], load_programs()
    out = [answer["summary"], ""]
    for p in sorted(answer["programs"], key=lambda p: ORDER[p["fit"]]):
        name = programs.get(p["program_id"], {}).get(f"name_{lang}", p["program_id"])
        out += [f"■ {name} — {L[p['fit']]}", f"  {p['why']}", f"  {L['next']}: {p['next_step']}"]
        urls = {(trace["retrieved"][c]["url"], trace["retrieved"][c]["fetched"])
                for c in p["sources"] if c in trace["retrieved"]}
        out += [f"  {L['src']}: {u} ({L['fetched']} {d})" for u, d in sorted(urls)]
        out.append("")
    out += [f"{L['nc']}: {answer['not_covered']}", "", L["disc"]]
    return "\n".join(out)


if __name__ == "__main__":
    opening = input("What's changed in your life? / Qu'est-ce qui a changé dans votre vie?\n> ")
    answer, trace = run(opening, answer_fn=lambda q: input(f"\n{q}\n> "))
    report = verify(answer, trace)
    # Never show a program whose explanation the checker couldn't back with real sources.
    blocked = {c["program_id"] for c in report["checks"] if c["verdict"] == "unsupported"}
    shown = dict(answer, programs=[p for p in answer["programs"] if p["program_id"] not in blocked])
    print("\n" + render(shown, trace))
    print(f"\n[check] grounded={report['grounded']}  invented_citations="
          f"{report['invented_citations']}  questions={report['questions_asked']}"
          + (f"  held_back={sorted(blocked)}" if blocked else ""))
