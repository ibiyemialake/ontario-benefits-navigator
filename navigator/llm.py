"""Same wrapper as the job copilot, plus a plain-text helper."""
import json
import os

from anthropic import Anthropic

MODEL = os.getenv("NAVIGATOR_MODEL", "claude-sonnet-5-5")
client = Anthropic()


def ask_text(system: str, user: str, max_tokens: int = 500) -> str:
    resp = client.messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                                  messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def ask_json(system: str, user: str, max_tokens: int = 800) -> dict:
    text = ask_text(system + "\n\nRespond with valid JSON only. No prose, no markdown fences.",
                    user, max_tokens)
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)
