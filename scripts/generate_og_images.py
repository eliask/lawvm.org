#!/usr/bin/env python3
"""Generate the small, code-native Open Graph card set."""

from __future__ import annotations

from html import escape
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets" / "og"

CARDS = {
    "lawvm-evidence": {
        "label": "LAWVM",
        "lines": ("Verify changes", "to the law."),
        "subtitle": "Source-linked replay · point-in-time state · explicit residuals",
        "accent": "#0969da",
    },
    "solutions": {
        "label": "LAWVM / SOLUTIONS",
        "lines": ("Legislative assurance", "by question."),
        "subtitle": "Declared sources · bounded checks · reviewable evidence",
        "accent": "#0969da",
    },
    "consolidation-assurance": {
        "label": "LAWVM / CONSOLIDATION",
        "lines": ("Consolidation", "assurance"),
        "subtitle": "Replay amendments · classify disagreements · retain the source path",
        "accent": "#0969da",
    },
    "multilingual-legislation": {
        "label": "LAWVM / OFFICIAL LANGUAGES",
        "lines": ("Parallel-language", "review"),
        "subtitle": "Independent expressions · structural pairing · human review",
        "accent": "#8250df",
    },
    "source-readiness": {
        "label": "LAWVM / SOURCE READINESS",
        "lines": ("Start from the", "sources you have."),
        "subtitle": "Page account · reconstruction evidence · explicit residuals",
        "accent": "#bf8700",
    },
    "drafting-publication-ci": {
        "label": "LAWVM / PUBLICATION QA",
        "lines": ("Drafting & publication", "checks"),
        "subtitle": "Frozen export · declared transition checks · no production writes",
        "accent": "#0969da",
    },
    "legal-data-conformance": {
        "label": "LAWVM / CORPUS CONFORMANCE",
        "lines": ("Legal-data", "conformance"),
        "subtitle": "Identity · versions · dates · links · languages · structure",
        "accent": "#1a7f37",
    },
    "estonia-audiitors-95-2": {
        "label": "LAWVM / CONFIRMED CASE / ESTONIA",
        "lines": ("One reported omission", "was corrected."),
        "subtitle": "Amendment source · replay finding · publisher review · correction",
        "accent": "#1a7f37",
    },
}


def svg_for(card: dict[str, object]) -> str:
    label = escape(str(card["label"]))
    first, second = (escape(str(value)) for value in card["lines"])
    subtitle = escape(str(card["subtitle"]))
    accent = escape(str(card["accent"]), quote=True)
    title = f"{first} {second}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-labelledby="title desc">
  <title id="title">{title}</title>
  <desc id="desc">{subtitle}</desc>
  <rect width="1200" height="630" fill="#0d1117"/>
  <circle cx="1040" cy="90" r="265" fill="{accent}" opacity="0.20"/>
  <circle cx="80" cy="650" r="280" fill="#1a7f37" opacity="0.15"/>
  <text x="80" y="100" fill="#f0f6fc" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="25" font-weight="700" letter-spacing="3">{label}</text>
  <text x="80" y="220" fill="#f0f6fc" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="64" font-weight="700">{first}</text>
  <text x="80" y="296" fill="#f0f6fc" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="64" font-weight="700">{second}</text>
  <text x="82" y="366" fill="#a5afba" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="26">{subtitle}</text>
  <g transform="translate(80 446)" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="20">
    <rect width="240" height="70" rx="9" fill="#161b22" stroke="#30363d"/>
    <text x="30" y="43" fill="#c9d1d9">declared source</text>
    <text x="260" y="43" fill="#8b949e">→</text>
    <rect x="300" width="240" height="70" rx="9" fill="#161b22" stroke="#30363d"/>
    <text x="335" y="43" fill="#c9d1d9">bounded check</text>
    <text x="560" y="43" fill="#8b949e">→</text>
    <rect x="600" width="310" height="70" rx="9" fill="#13251a" stroke="#238636"/>
    <text x="638" y="43" fill="#56d364">reviewable evidence</text>
  </g>
  <text x="80" y="580" fill="#8b949e" font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="20">lawvm.org</text>
</svg>
'''


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for stem, card in CARDS.items():
        svg_path = OUTPUT / f"{stem}.svg"
        png_path = OUTPUT / f"{stem}.png"
        svg_path.write_text(svg_for(card), encoding="utf-8")
        subprocess.run(
            ["convert", str(svg_path), "-strip", "-define", "png:color-type=6", str(png_path)],
            check=True,
        )
    print(f"Generated {len(CARDS)} Open Graph card pairs in {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
