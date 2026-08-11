#!/usr/bin/env python3
"""Generate the public assurance status page from its machine-readable registry."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "assets" / "data" / "assurance-claims.json"
TEMPLATE = ROOT / "_fragments" / "assurance-status.tpl"
OUTPUT = ROOT / "_site" / "assurance" / "status" / "index.html"

REQUIRED_CLAIM_FIELDS = {
    "claim_id",
    "title",
    "statement",
    "scope",
    "mechanisms",
    "deployment",
    "assumptions",
    "specification_paths",
    "implementation_paths",
    "test_paths",
    "allowed_wording",
    "forbidden_wording",
    "known_limits",
}


def e(value: object) -> str:
    return escape(str(value), quote=True)


def list_html(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{e(item)}</li>" for item in items) + "</ul>"


def path_list(title: str, paths: list[str]) -> str:
    values = "".join(f"<li><code>{e(path)}</code></li>" for path in paths)
    return f"<div><h4>{e(title)}</h4><ul>{values}</ul></div>"


def mechanism_tag(value: str) -> str:
    css_class = "tag"
    if value in {"observe_only", "model_proved"}:
        css_class += " tag-amber"
    elif value in {"independently_checked", "externally_adjudicated"}:
        css_class += " tag-green"
    elif value in {"typed", "property_tested", "corpus_demonstrated"}:
        css_class += " tag-accent"
    return f'<span class="{css_class}">{e(value.replace("_", " "))}</span>'


def claim_html(claim: dict[str, object]) -> str:
    missing = REQUIRED_CLAIM_FIELDS - claim.keys()
    if missing:
        raise ValueError(f"{claim.get('claim_id', '<unknown>')} missing fields: {sorted(missing)}")
    mechanisms = claim["mechanisms"]
    if not isinstance(mechanisms, list):
        raise TypeError(f"{claim['claim_id']}: mechanisms must be a list")
    claim_id = str(claim["claim_id"])
    anchor = claim_id.lower().replace(".", "-")
    tags = "".join(mechanism_tag(str(item)) for item in mechanisms)
    evidence = "".join(
        [
            path_list("Specifications", list(claim["specification_paths"])),
            path_list("Implementation", list(claim["implementation_paths"])),
            path_list("Tests", list(claim["test_paths"])),
        ]
    )
    return f"""            <article class="assurance-claim" id="{e(anchor)}">
                <div class="tag-list">{tags}</div>
                <p class="as-of">{e(claim_id)}</p>
                <h3>{e(claim['title'])}</h3>
                <p>{e(claim['statement'])}</p>
                <div class="status-list">
                    <dl class="status-row"><dt>Scope</dt><dd>{e(claim['scope'])}</dd></dl>
                    <dl class="status-row"><dt>Deployment</dt><dd>{e(claim['deployment'])}</dd></dl>
                    <dl class="status-row"><dt>Allowed wording</dt><dd>{e(claim['allowed_wording'])}</dd></dl>
                    <dl class="status-row"><dt>Forbidden wording</dt><dd>{e(claim['forbidden_wording'])}</dd></dl>
                </div>
                <details class="claim-details">
                    <summary>Assumptions, evidence paths, and known limits</summary>
                    <div class="claim-detail-grid">
                        <div><h4>Assumptions</h4>{list_html(list(claim['assumptions']))}</div>
                        <div><h4>Known limits</h4>{list_html(list(claim['known_limits']))}</div>
                    </div>
                    <div class="claim-path-grid">{evidence}</div>
                </details>
            </article>"""


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if registry.get("schema") != "lawvm.assurance-claim-registry.v1":
        raise ValueError("unexpected assurance registry schema")
    claims = registry.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValueError("assurance registry must contain claims")
    ids = [str(claim.get("claim_id")) for claim in claims]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate assurance claim_id")

    snapshot = (
        '<div class="meta-strip">'
        f'<span>Snapshot: {e(registry["snapshot_date"])}</span>'
        '<span>Public code: moving development surface</span>'
        f'<span>Release-bound: {"yes" if registry["release_bound"] else "no"}</span>'
        "</div>"
    )
    vocabulary = "\n".join(
        f'            <div class="content-card"><h3>{e(key.replace("_", " "))}</h3><p>{e(value)}</p></div>'
        for key, value in registry["mechanism_vocabulary"].items()
    )
    outcomes = "\n".join(
        f'<div class="content-card"><h3>{e(key.replace("_", " "))}</h3><p>{e(value)}</p></div>'
        for key, value in registry["outcome_vocabulary"].items()
    )
    registry_gaps = "\n".join(
        f'<dl class="status-row"><dt>{e(key.replace("_", " "))}</dt><dd>{e(value)}</dd></dl>'
        for key, value in registry["registry_gaps"].items()
    )
    replacements = {
        "@@HEAD_END@@": (ROOT / "_fragments" / "head-end.html").read_text(encoding="utf-8").rstrip(),
        "@@NAV_CONTENT@@": (ROOT / "_fragments" / "nav-content.html").read_text(encoding="utf-8").rstrip(),
        "@@THEME_TOGGLE@@": (ROOT / "_fragments" / "theme-toggle.html").read_text(encoding="utf-8").rstrip(),
        "@@FOOTER@@": (ROOT / "_fragments" / "footer.html").read_text(encoding="utf-8").rstrip(),
        "@@SNAPSHOT@@": snapshot,
        "@@CLAIMS@@": "\n".join(claim_html(claim) for claim in claims),
        "@@VOCABULARY@@": vocabulary,
        "@@OUTCOMES@@": outcomes,
        "@@REGISTRY_GAPS@@": registry_gaps,
    }
    result = TEMPLATE.read_text(encoding="utf-8")
    for marker, value in replacements.items():
        result = result.replace(marker, value)
    if "@@" in result:
        raise ValueError("unexpanded assurance status template marker")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(result, encoding="utf-8")
    print(f"Generated {OUTPUT.relative_to(ROOT)} from {len(claims)} assurance claims")


if __name__ == "__main__":
    main()
