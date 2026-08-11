#!/usr/bin/env python3
"""Apply release-wide accessibility and metadata invariants to built HTML."""

from __future__ import annotations

from html import escape, unescape
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
STANDALONE: set[Path] = set()
DEFAULT_OG_IMAGE = "https://lawvm.org/assets/og/lawvm-evidence.png"
DEFAULT_OG_ALT = "LawVM — Verify changes to the law"


def capture(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError(f"missing metadata matching {pattern}")
    return unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()


def ensure_social_metadata(text: str) -> str:
    """Complete social metadata while preserving explicit page-specific cards."""

    title = capture(r'<meta\s+property="og:title"\s+content="([^"]+)"', text)
    description = capture(r'<meta\s+property="og:description"\s+content="([^"]+)"', text)
    additions: list[str] = []

    if 'property="og:image"' not in text:
        additions.extend(
            [
                f'<meta property="og:image" content="{DEFAULT_OG_IMAGE}">',
                '<meta property="og:image:width" content="1200">',
                '<meta property="og:image:height" content="630">',
                f'<meta property="og:image:alt" content="{escape(DEFAULT_OG_ALT, quote=True)}">',
            ]
        )
        image = DEFAULT_OG_IMAGE
    else:
        image = capture(r'<meta\s+property="og:image"\s+content="([^"]+)"', text)

    if 'name="twitter:card"' in text:
        text = re.sub(
            r'(<meta\s+name="twitter:card"\s+content=")[^"]+("\s*/?>)',
            r'\1summary_large_image\2',
            text,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        additions.append('<meta name="twitter:card" content="summary_large_image">')
    if 'name="twitter:title"' not in text:
        additions.append(f'<meta name="twitter:title" content="{escape(title, quote=True)}">')
    if 'name="twitter:description"' not in text:
        additions.append(f'<meta name="twitter:description" content="{escape(description, quote=True)}">')
    if 'name="twitter:image"' not in text:
        additions.append(f'<meta name="twitter:image" content="{escape(image, quote=True)}">')

    if additions:
        if "</head>" not in text:
            raise ValueError("missing head end while adding social metadata")
        block = "\n    " + "\n    ".join(additions) + "\n"
        text = text.replace("</head>", block + "</head>", 1)
    return text


def finalize(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if path not in STANDALONE:
        if 'class="skip-link"' not in text:
            text, count = re.subn(
                r"(<body(?:\s[^>]*)?>)",
                r'\1\n<a class="skip-link" href="#main-content">Skip to main content</a>',
                text,
                count=1,
                flags=re.IGNORECASE,
            )
            if count != 1:
                raise ValueError(f"{path}: expected one body")
        main_match = re.search(r"<main(?P<attrs>[^>]*)>", text, flags=re.IGNORECASE)
        if not main_match:
            raise ValueError(f"{path}: missing main")
        attrs = main_match.group("attrs")
        if not re.search(r'\bid=["\']main-content["\']', attrs, flags=re.IGNORECASE):
            if re.search(r"\bid=", attrs, flags=re.IGNORECASE):
                raise ValueError(f"{path}: main has an unexpected id")
            replacement = '<main id="main-content"' + attrs + ">"
            text = text[: main_match.start()] + replacement + text[main_match.end() :]

    text = ensure_social_metadata(text)

    if 'type="application/ld+json"' not in text:
        title = capture(r"<title>(.*?)</title>", text)
        description = capture(r'<meta\s+name="description"\s+content="([^"]+)"', text)
        canonical = capture(r'<link\s+rel="canonical"\s+href="([^"]+)"', text)
        document = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "description": description,
            "url": canonical,
            "isPartOf": {"@type": "WebSite", "name": "LawVM", "url": "https://lawvm.org/"},
        }
        block = '<script type="application/ld+json">\n' + json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n</script>\n"
        if "</head>" not in text:
            raise ValueError(f"{path}: missing head end")
        text = text.replace("</head>", block + "</head>", 1)

    path.write_text(text, encoding="utf-8")


def main() -> None:
    pages = sorted(SITE.rglob("*.html"))
    for page in pages:
        finalize(page)
    print(f"Finalized accessibility and structured metadata for {len(pages)} HTML pages")


if __name__ == "__main__":
    main()
