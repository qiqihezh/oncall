from __future__ import annotations

import re

from bs4 import BeautifulSoup


SPACE_PATTERN = re.compile(r"\s+")


def parse_html(raw_html: str) -> tuple[str, str]:
    soup = BeautifulSoup(raw_html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = _extract_title(soup)
    text = SPACE_PATTERN.sub(" ", soup.get_text(" ")).strip()
    return title, text


def _extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(" ", strip=True)

    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(" ", strip=True)

    return "Untitled SOP"
