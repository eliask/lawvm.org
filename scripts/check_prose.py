#!/usr/bin/env python3
"""Reject recurring prose defects in the deployable LawVM site."""

from __future__ import annotations

from collections import Counter
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
BANNED_PATTERNS = {
    "canned importance claim": re.compile(r"\b(?:why )?this matters\b", re.IGNORECASE),
    "canned contrast": re.compile(r"\b(?:not merely|not just|more than just|not developer trivia)\b", re.IGNORECASE),
    "throat clearing": re.compile(
        r"\b(?:it is important to note|it should be noted|needless to say|at its core|in today['’]s)\b",
        re.IGNORECASE,
    ),
    "generic reassurance": re.compile(r"\b(?:you['’]re not alone|we can do better together)\b", re.IGNORECASE),
    "nervous preface": re.compile(
        r"\b(?:uncomfortable truth|this may sound (?:harsh|controversial)|controversial,? but)\b",
        re.IGNORECASE,
    ),
    "promotional filler": re.compile(
        r"\b(?:delve|tapestry|testament to|game[- ]chang\w*|cutting[- ]edge|seamless(?:ly)?|"
        r"unlock(?:ing)? (?:the|new)|transformative|revolutionary)\b",
        re.IGNORECASE,
    ),
    "unearned quality adjective": re.compile(r"\b(?:robust|holistic|comprehensive|crucial|vital|important)\b", re.IGNORECASE),
    "self-certifying adjective": re.compile(r"\b(?:honest|honestly)\b", re.IGNORECASE),
    "generic value adjective": re.compile(r"\buseful\b", re.IGNORECASE),
}
TEXT_ASSET_SUFFIXES = {".json", ".js", ".txt", ".xml", ".svg"}
RENDERED_JSON_FILES = {
    "assurance-demo.json",
    "evidence.json",
    "interactive-replay-explainer.json",
}
NEGATION = re.compile(
    r"\b(?:does not|do not|is not|are not|cannot|can not|must not|should not|will not|not|no)\b",
    re.IGNORECASE,
)
NEGATIVE_LIST = re.compile(
    r"\b(?:does not|do not|is not|are not|cannot|can not|not|no)\b"
    r"[^.!?]{0,220}(?:,\s+[^,.!?]+){2,}",
    re.IGNORECASE,
)


class ProseParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.buffers: list[tuple[str, str, list[str]]] = []
        self.blocks: list[tuple[str, str]] = []
        self.metadata: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(tag)
        if tag in {"p", "h1", "h2", "h3", "li", "dt", "dd", "td", "th", "title"}:
            self.buffers.append((tag, tag, []))
        values = dict(attrs)
        classes = set(str(values.get("class", "")).split())
        for prose_class in ("claim-boundary", "callout"):
            if tag == "div" and prose_class in classes:
                self.buffers.append((tag, prose_class, []))
        if tag == "meta" and values.get("content"):
            self.metadata.append(str(values["content"]))

    def handle_endtag(self, tag: str) -> None:
        if self.buffers and self.buffers[-1][0] == tag:
            _, block_tag, parts = self.buffers.pop()
            text = re.sub(r"\s+", " ", "".join(parts)).strip()
            if text:
                self.blocks.append((block_tag, text))
        if tag in self.stack:
            reverse_index = self.stack[::-1].index(tag)
            del self.stack[len(self.stack) - reverse_index - 1 :]

    def handle_data(self, data: str) -> None:
        if "script" in self.stack or "style" in self.stack:
            return
        for _, _, parts in self.buffers:
            parts.append(data)


def normalized_words(text: str) -> list[str]:
    return re.findall(r"[\w’'-]+", text, flags=re.UNICODE)


def check_patterns(label: str, text: str, errors: list[str]) -> None:
    for reason, pattern in BANNED_PATTERNS.items():
        match = pattern.search(unescape(text))
        if match:
            errors.append(f"{label}: {reason}: {match.group(0)!r}")


def check_negative_stack(label: str, text: str, errors: list[str]) -> None:
    negations = NEGATION.findall(text)
    if len(negations) > 2:
        errors.append(
            f"{label}: prose stacks {len(negations)} negative boundaries; state the usable claim "
            f"and next evidence: {text[:120]!r}"
        )
    if NEGATIVE_LIST.search(text):
        errors.append(
            f"{label}: prose uses a negative laundry list; state the positive scope and next evidence: "
            f"{text[:120]!r}"
        )


def json_strings(value: object, path: str = "$") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, list):
        result: list[tuple[str, str]] = []
        for index, item in enumerate(value):
            result.extend(json_strings(item, f"{path}[{index}]"))
        return result
    if isinstance(value, dict):
        result = []
        for key, item in value.items():
            result.extend(json_strings(item, f"{path}.{key}"))
        return result
    return []


def check_html(path: Path, errors: list[str]) -> None:
    relative = path.relative_to(SITE)
    parser = ProseParser()
    parser.feed(path.read_text(encoding="utf-8"))
    for index, (tag, text) in enumerate(parser.blocks, start=1):
        check_patterns(f"{relative}:{tag}[{index}]", text, errors)
        if tag in {"h1", "h2", "h3"} and NEGATION.search(text):
            errors.append(f"{relative}:{tag}[{index}]: negative heading hides the usable claim: {text!r}")
        if tag in {"p", "claim-boundary", "callout", "li", "dd", "td", "th"}:
            word_count = len(normalized_words(text))
            if tag in {"p", "claim-boundary", "callout"} and word_count > 120:
                errors.append(f"{relative}: paragraph has {word_count} words (limit 120): {text[:100]!r}")
            if tag in {"p", "claim-boundary", "callout"} and text.count("—") > 2:
                errors.append(f"{relative}: paragraph overuses em dashes: {text[:100]!r}")
            check_negative_stack(f"{relative}:{tag}[{index}]", text, errors)
    for index, text in enumerate(parser.metadata, start=1):
        check_patterns(f"{relative}:meta[{index}]", text, errors)

    paragraphs = [
        re.sub(r"\W+", " ", text.casefold()).strip()
        for tag, text in parser.blocks
        if tag == "p" and len(normalized_words(text)) >= 12 and not text.startswith("source_identity=")
    ]
    for duplicate, count in Counter(paragraphs).items():
        if count > 1:
            errors.append(f"{relative}: duplicated paragraph appears {count} times: {duplicate[:100]!r}")


def main() -> int:
    errors: list[str] = []
    for path in sorted(SITE.rglob("*.html")):
        check_html(path, errors)
    for path in sorted(SITE.rglob("*")):
        if path.is_file() and path.suffix.lower() in TEXT_ASSET_SUFFIXES:
            try:
                check_patterns(str(path.relative_to(SITE)), path.read_text(encoding="utf-8"), errors)
            except UnicodeDecodeError:
                continue
        if path.is_file() and path.name in RENDERED_JSON_FILES:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            for json_path, value in json_strings(payload):
                label = f"{path.relative_to(SITE)}:{json_path}"
                check_patterns(label, value, errors)
                check_negative_stack(label, value, errors)
    for path in sorted((ROOT / "briefs-src").glob("*.md")):
        relative = str(path.relative_to(ROOT))
        source = path.read_text(encoding="utf-8")
        check_patterns(relative, source, errors)
        for index, block in enumerate(re.split(r"\n\s*\n", source), start=1):
            prose = re.sub(r"^[-|#>]+\s*", "", block.strip(), flags=re.MULTILINE)
            prose = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", prose)
            prose = re.sub(r"\s+", " ", prose).strip()
            if prose:
                check_negative_stack(f"{relative}:block[{index}]", prose, errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(
        "Prose CI complete: no banned filler, negative-heading/list stacks, wall paragraphs, "
        "repeated paragraphs, or em-dash clusters"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
