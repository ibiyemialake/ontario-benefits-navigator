"""Fetch each official page (English + its French version), split into chunks,
and index them with program, language, URL and fetch date.

Usage:  python -m navigator.ingest
Re-run monthly: amounts and rules change.
"""
import datetime
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .search import get_collection
from .sources import load_programs

HEADERS = {"User-Agent": "benefits-navigator-learning-project"}
BLOCKS = ["h1", "h2", "h3", "h4", "p", "li", "dt", "dd", "td"]


def find_french_url(soup: BeautifulSoup, page_url: str) -> str | None:
    tag = (soup.find("link", attrs={"hreflang": "fr"})
           or soup.find("a", attrs={"hreflang": "fr"})
           or soup.find("a", attrs={"lang": "fr"})
           or soup.find("a", string=re.compile(r"^\s*Français\s*$")))
    return urljoin(page_url, tag["href"]) if tag and tag.get("href") else None


def extract(html: str, page_url: str) -> tuple[str, list[tuple[str, str]], str | None]:
    """Return (page title, [(section heading, text)], french url)."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else ""
    fr_url = find_french_url(soup, page_url)
    main = soup.find("main") or soup.body
    for junk in main.find_all(["script", "style", "nav", "aside", "form"]):
        junk.decompose()

    sections, heading, buf = [], title, []
    for el in main.find_all(BLOCKS):
        if el.name in ("p", "li") and el.find_parent(["li", "td", "dd"]):
            continue  # nested; its parent already holds this text
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        if el.name in ("h1", "h2", "h3", "h4"):
            if buf:
                sections.append((heading, "\n".join(buf)))
            heading, buf = text, []
        else:
            buf.append(text)
    if buf:
        sections.append((heading, "\n".join(buf)))
    return title, sections, fr_url


def chunk(title: str, sections: list[tuple[str, str]], size: int = 1200) -> list[str]:
    """Split sections into ~size-char chunks, each prefixed with page + section
    so a chunk makes sense on its own."""
    chunks = []
    for heading, body in sections:
        cur = ""
        for line in body.split("\n"):
            if cur and len(cur) + len(line) > size:
                chunks.append(f"{title} — {heading}\n{cur}")
                cur = ""
            cur = f"{cur}\n{line}".strip()
        if cur:
            chunks.append(f"{title} — {heading}\n{cur}")
    return chunks


def ingest():
    col = get_collection(reset=True)
    today = datetime.date.today().isoformat()
    total = 0
    for pid, prog in load_programs().items():
        counts = {"en": 0, "fr": 0}
        for en_url in prog["urls"]:
            queue = [("en", en_url)]
            while queue:
                lang, url = queue.pop(0)
                try:
                    html = requests.get(url, headers=HEADERS, timeout=30)
                    html.raise_for_status()
                except Exception as e:
                    print(f"  ! {pid} {lang} {url}: {e}")
                    continue
                title, sections, fr_url = extract(html.text, url)
                if lang == "en":
                    if fr_url:
                        queue.append(("fr", fr_url))
                    else:
                        print(f"  ! no French link found on {url}")
                docs = chunk(title, sections)
                ids = [f"{pid}-{lang}-{counts[lang] + n}" for n in range(len(docs))]
                counts[lang] += len(docs)
                if docs:
                    col.add(ids=ids, documents=docs, metadatas=[
                        {"program_id": pid, "level": prog["level"], "lang": lang,
                         "url": url, "title": title, "fetched": today} for _ in docs])
                time.sleep(1)  # be polite to government servers
        print(f"{pid:24} en={counts['en']:3}  fr={counts['fr']:3}")
        total += counts["en"] + counts["fr"]
    print(f"\nIndexed {total} chunks on {today}.")


if __name__ == "__main__":
    ingest()
