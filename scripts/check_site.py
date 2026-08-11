#!/usr/bin/env python3
"""Validate the built static site without third-party dependencies."""

from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
STANDALONE: set[Path] = set()
NOINDEX_ALIAS = {SITE / "solutions" / "source-recovery" / "index.html"}
ASSURANCE_CLAIM_FIELDS = {
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
PUBLIC_TEXT_SUFFIXES = frozenset({".html", ".json", ".js", ".css", ".txt", ".xml", ".svg"})
RETIRED_FINNISH_VIEWER_PATTERN = re.compile(r"finlex[-_\s]+virheet", re.IGNORECASE)
STALE_PUBLIC_EMAIL_PATTERN = re.compile(r"elias\s*(?:@|\bat\b)\s*kunnas\s*\.\s*com", re.IGNORECASE)
STALE_POSITIONING_PATTERN = re.compile(
    r"\b(?:alpha(?:-stage)?(?:\s+research)?\s+preview|research[-\s]+preview)\b",
    re.IGNORECASE,
)
EXPECTED_EVIDENCE_SCHEMA = "lawvm.public-evidence-ledger.v1"
EXPECTED_EVIDENCE_STATUSES = {
    "externally_confirmed_correction",
    "candidate_awaiting_disposition",
    "externally_refuted",
    "lawvm_defect",
    "source_pathology",
    "manual_frontier",
    "blocked",
    "representative_clean_transition",
}
FI_AGGREGATE_CASE_ID = "FI-REPORTED-CANDIDATES-2026-04"
FI_AGGREGATE_REQUIRED_FIELDS = {
    "case_id",
    "record_type",
    "evidence_type",
    "jurisdiction",
    "status",
    "count",
    "reviewability",
    "reported_by",
    "case_url",
    "claim",
    "nonclaims",
}
FI_AGGREGATE_FORBIDDEN_FIELDS = {
    "work",
    "address",
    "base_id",
    "comparison_id",
    "effective_date",
    "disposition_date",
    "source_url",
    "comparison_url",
    "rule_id",
    "compiler_commit",
    "evidence_locator",
    "reproduction_command",
    "source_byte_bundle",
}
REQUIRED_OG_PROPERTIES = {
    "og:title",
    "og:description",
    "og:type",
    "og:url",
    "og:site_name",
    "og:image",
    "og:image:width",
    "og:image:height",
    "og:image:alt",
}
REQUIRED_TWITTER_NAMES = {
    "twitter:card",
    "twitter:title",
    "twitter:description",
    "twitter:image",
}
EXPECTED_SOCIAL_IMAGES = {
    Path("solutions/index.html"): "https://lawvm.org/assets/og/solutions.png",
    Path("solutions/consolidation-assurance/index.html"): "https://lawvm.org/assets/og/consolidation-assurance.png",
    Path("solutions/multilingual-legislation/index.html"): "https://lawvm.org/assets/og/multilingual-legislation.png",
    Path("solutions/source-readiness/index.html"): "https://lawvm.org/assets/og/source-readiness.png",
    Path("solutions/source-recovery/index.html"): "https://lawvm.org/assets/og/source-readiness.png",
    Path("solutions/drafting-publication-ci/index.html"): "https://lawvm.org/assets/og/drafting-publication-ci.png",
    Path("solutions/legal-data-conformance/index.html"): "https://lawvm.org/assets/og/legal-data-conformance.png",
    Path("cases/estonia-audiitors-95-2/index.html"): "https://lawvm.org/assets/og/estonia-audiitors-95-2.png",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: list[str] = []
        self.h1_count = 0
        self.descriptions: list[str | None] = []
        self.canonicals: list[str | None] = []
        self.stylesheets: list[str | None] = []
        self.headers = 0
        self.footers = 0
        self.mains = 0
        self.main_content_ids = 0
        self.skip_links = 0
        self.heading_levels: list[int] = []
        self.noindex = False
        self.meta_properties: dict[str, list[str | None]] = {}
        self.meta_names: dict[str, list[str | None]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if values.get("id"):
            self.ids.append(str(values["id"]))
        if tag == "h1":
            self.h1_count += 1
        if re.fullmatch(r"h[1-6]", tag):
            self.heading_levels.append(int(tag[1]))
        if tag == "meta" and values.get("name") == "description":
            self.descriptions.append(values.get("content"))
        if tag == "meta" and values.get("property"):
            self.meta_properties.setdefault(str(values["property"]), []).append(values.get("content"))
        if tag == "meta" and values.get("name"):
            self.meta_names.setdefault(str(values["name"]), []).append(values.get("content"))
        if tag == "meta" and values.get("name") == "robots" and "noindex" in str(values.get("content", "")):
            self.noindex = True
        if tag == "link" and values.get("rel") == "canonical":
            self.canonicals.append(values.get("href"))
        if tag == "link" and values.get("rel") == "stylesheet":
            self.stylesheets.append(values.get("href"))
        if tag == "header":
            self.headers += 1
        if tag == "footer":
            self.footers += 1
        if tag == "main":
            self.mains += 1
            if values.get("id") == "main-content":
                self.main_content_ids += 1
        if tag == "a" and values.get("class") == "skip-link" and values.get("href") == "#main-content":
            self.skip_links += 1


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def link_exists(page: Path, href: str) -> bool:
    if href.startswith(("#", "http:", "https:", "mailto:", "tel:")):
        return True
    raw_path = urlsplit(href).path
    if not raw_path:
        return True
    target = SITE / raw_path.lstrip("/") if raw_path.startswith("/") else page.parent / raw_path
    return target.exists() or (target / "index.html").exists() or target.with_suffix(".html").exists()


def sitemap_urls() -> set[str]:
    tree = ET.parse(SITE / "sitemap.xml")
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return {str(node.text) for node in tree.findall("s:url/s:loc", namespace) if node.text}


def normalized_public_text(raw: str) -> str:
    """Decode common publication encodings before applying forbidden-token gates."""

    value = raw
    for _ in range(2):
        value = unquote(unescape(value))
    return value.lower()


def validate_public_surface(errors: list[str]) -> None:
    """Reject retired routes and stale personal contact details from deployable output.

    Private planning/audit dotfiles are outside ``_site`` by construction and are
    intentionally not scanned here.  The historical ``finlex_oracle`` benchmark
    label is not the retired ``finlex-virheet`` viewer token and remains allowed.
    """

    if not SITE.is_dir():
        return
    for path in sorted(SITE.rglob("*")):
        relative = path.relative_to(SITE)
        relative_text = normalized_public_text(relative.as_posix())
        if RETIRED_FINNISH_VIEWER_PATTERN.search(relative_text):
            errors.append(f"retired Finnish viewer route/name in deployable path: {relative}")
        if not path.is_file():
            continue
        if path.suffix.lower() not in PUBLIC_TEXT_SUFFIXES:
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"{relative}: deployable text asset is not UTF-8: {exc}")
            continue
        text = normalized_public_text(raw)
        if path.suffix.lower() == ".html":
            # A token split across harmless markup is still visible public text.
            text = re.sub(r"<[^>]*>", " ", text)
        if RETIRED_FINNISH_VIEWER_PATTERN.search(text):
            errors.append(f"retired Finnish viewer route/name in deployable text: {relative}")
        if STALE_PUBLIC_EMAIL_PATTERN.search(text):
            errors.append(f"stale public email remains in deployable text: {relative}")
        if STALE_POSITIONING_PATTERN.search(text):
            errors.append(f"stale alpha/research-preview positioning remains in deployable text: {relative}")


def validate_positioning(errors: list[str]) -> None:
    """Keep maturity and scan-recovery claims on their deliberately separate axes."""

    required_page_phrases = {
        Path("about/project-status/index.html"): (
            "open-source",
            "beta-stage",
            "pre-1.0",
            "profile-specific",
            "legal authority and broader correctness require separate institutional and evidential support",
        ),
        Path("solutions/source-readiness/index.html"): (
            "ocr supplies candidate text and locators",
            "each retain their own evidence and residuals",
            "a bounded source-readiness pilot can produce this documentary evidence package",
            "institutional review govern identity, authority, interpretation, temporal effect, and publication",
        ),
        Path("pilots/index.html"): (
            "free and open-source software",
            "mit license",
            "a pilot agreement separately defines integration, review, support, custody, outputs, service levels, and warranties",
            "no production writes",
        ),
    }
    for relative, phrases in required_page_phrases.items():
        path = SITE / relative
        if not path.is_file():
            errors.append(f"missing positioning surface: {relative}")
            continue
        text = normalized_public_text(path.read_text(encoding="utf-8"))
        text = re.sub(r"<[^>]*>", " ", text)
        text = re.sub(r"\s+", " ", text)
        for phrase in phrases:
            if phrase not in text:
                errors.append(f"{relative}: missing required claim boundary {phrase!r}")

    finnish_manifest = "statute-timeline-manifest-fi-all-no-amendments.json"
    for relative in (Path("finland/index.html"), Path("explore/index.html")):
        raw = (SITE / relative).read_text(encoding="utf-8")
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', raw, flags=re.IGNORECASE)
        explorer_hrefs = [href for href in hrefs if finnish_manifest in href]
        if not explorer_hrefs:
            errors.append(f"{relative}: missing Finnish Explorer link")
        for href in explorer_hrefs:
            if not href.endswith("#ui_lang=en"):
                errors.append(f"{relative}: Finnish Explorer must select English UI: {href}")


def validate_json(errors: list[str]) -> None:
    data_dir = SITE / "assets" / "data"
    for path in sorted(data_dir.glob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"{path.relative_to(SITE)}: invalid JSON: {exc}")

    snapshot = json.loads((data_dir / "public-snapshot.json").read_text(encoding="utf-8"))
    if snapshot.get("schema") != "lawvm.public-site-snapshot.v1":
        errors.append("public-snapshot.json: unexpected schema")
    if not snapshot.get("public_code_status"):
        errors.append("public-snapshot.json: public code status must be explicit")
    for stale_field in (
        "pinned_inspected_core_revision",
        "core_revision_was_clean_at_inspection",
        "core_snapshot_status",
        "public_runnable_core_baseline",
        "public_runnable_baseline_observed_at",
        "website_parent_baseline_commit",
        "website_source_commit",
        "website_source_identity",
        "website_working_tree_clean",
    ):
        if stale_field in snapshot:
            errors.append(f"public-snapshot.json: stale implementation-identity field {stale_field}")
    for name, url in snapshot.get("registries", {}).items():
        target = SITE / str(url).lstrip("/")
        if not target.is_file():
            errors.append(f"public-snapshot.json: missing registry target {name}: {url}")
    benchmark = snapshot.get("benchmark_snapshot", {})
    if benchmark.get("date") != snapshot.get("stable_public_evidence", {}).get("finland_benchmark_snapshot"):
        errors.append("public-snapshot.json: benchmark dates disagree")
    if benchmark.get("headline_mean_text_distance") != "0.23%":
        errors.append("public-snapshot.json: unexpected Finnish replay headline")
    if benchmark.get("provenance") != "project_reported":
        errors.append("public-snapshot.json: benchmark provenance boundary is incomplete")
    if not snapshot.get("known_unavailable_public_artifacts"):
        errors.append("public-snapshot.json: unavailable public artifacts must be explicit")

    frontends = json.loads((data_dir / "frontends.json").read_text(encoding="utf-8"))
    if frontends.get("schema") != "lawvm.frontend-status.v1":
        errors.append("frontends.json: unexpected schema")
    ids = [item.get("id") for item in frontends.get("frontends", [])]
    if len(ids) != len(set(ids)):
        errors.append("frontends.json: duplicate frontend id")
    if frontends.get("measured_at") != snapshot.get("snapshot_date"):
        errors.append("frontends.json: measurement date differs from public snapshot")
    if "measured_core_revision" in frontends:
        errors.append("frontends.json: stale public core revision field")
    profile_values = {
        "typed", "candidate", "observe_only", "pit", "dry_run", "residual",
        "not_claimed", "not_authorized", "externally_adjudicated", "unknown",
    }
    for item in frontends.get("frontends", []):
        for field in (
            "id",
            "name",
            "integration",
            "claim_ceiling",
            "pilot_ready_use",
            "local_need",
            "next_gate",
        ):
            if not item.get(field):
                errors.append(f"frontends.json: {item.get('id', '<unknown>')} missing {field}")
        profile = item.get("assurance_profile", {})
        expected_axes = {
            "source_identity", "effect_accounting", "typed_closure", "admission",
            "mutation_observation", "temporal_state", "independent_trace_check",
            "source_to_operation_entailment", "external_adjudication",
        }
        if set(profile) != expected_axes:
            errors.append(f"frontends.json: {item.get('id', '<unknown>')} has incomplete assurance profile")
        if not set(profile.values()) <= profile_values:
            errors.append(f"frontends.json: {item.get('id', '<unknown>')} uses an unknown profile value")
        if item.get("integration") not in {"integrated", "staging"}:
            errors.append(f"frontends.json: {item.get('id', '<unknown>')} has invalid integration state")
        if "measured_core_revision" in item:
            errors.append(f"frontends.json: {item.get('id', '<unknown>')} exposes stale core revision trivia")
        if item.get("measured_at") != frontends.get("measured_at"):
            errors.append(f"frontends.json: {item.get('id', '<unknown>')} measurement date disagrees")
        cta = item.get("cta", {})
        if set(cta) != {"assessment", "pilot", "contact"} or not all(cta.values()):
            errors.append(f"frontends.json: {item.get('id', '<unknown>')} has incomplete CTA set")

    evidence = json.loads((data_dir / "evidence.json").read_text(encoding="utf-8"))
    if evidence.get("schema") != EXPECTED_EVIDENCE_SCHEMA:
        errors.append("evidence.json: unexpected schema")
    status_vocabulary = evidence.get("status_vocabulary", [])
    status_set = set(status_vocabulary) if isinstance(status_vocabulary, list) else set()
    if (
        not isinstance(status_vocabulary, list)
        or len(status_vocabulary) != len(status_set)
        or status_set != EXPECTED_EVIDENCE_STATUSES
    ):
        errors.append("evidence.json: status vocabulary is incomplete or drifted")
    case_ids = [item.get("case_id") for item in evidence.get("cases", [])]
    if len(case_ids) != len(set(case_ids)):
        errors.append("evidence.json: duplicate case_id")
    for item in evidence.get("cases", []):
        for field in ("case_id", "jurisdiction", "status", "record_type", "evidence_type", "reviewability", "claim", "nonclaims"):
            if not item.get(field):
                errors.append(f"evidence.json: {item.get('case_id', '<unknown>')} missing {field}")
        if item.get("status") not in status_set:
            errors.append(f"evidence.json: {item.get('case_id', '<unknown>')} uses unknown status")

    finland_cases = [item for item in evidence.get("cases", []) if item.get("jurisdiction") == "fi"]
    if len(finland_cases) != 1:
        errors.append("evidence.json: Finland must have exactly one public aggregate record while review is pending")
    else:
        finland = finland_cases[0]
        missing = FI_AGGREGATE_REQUIRED_FIELDS - finland.keys()
        if missing:
            errors.append(f"evidence.json: Finland aggregate record missing {sorted(missing)}")
        forbidden = FI_AGGREGATE_FORBIDDEN_FIELDS & finland.keys()
        if forbidden:
            errors.append(f"evidence.json: Finland aggregate record exposes individual-case fields {sorted(forbidden)}")
        if finland.get("case_id") != FI_AGGREGATE_CASE_ID:
            errors.append("evidence.json: unexpected Finland aggregate case_id")
        if finland.get("record_type") != "aggregate_candidate_count":
            errors.append("evidence.json: Finland record must remain aggregate_candidate_count")
        if finland.get("evidence_type") != "responsibly_withheld_candidate_aggregate":
            errors.append("evidence.json: Finland record must declare withheld aggregate evidence")
        if finland.get("status") != "candidate_awaiting_disposition":
            errors.append("evidence.json: Finland aggregate must remain pending disposition")
        if (
            not isinstance(finland.get("count"), int)
            or isinstance(finland.get("count"), bool)
            or finland.get("count", 0) < 1
        ):
            errors.append("evidence.json: Finland aggregate count must be a positive integer")
        if finland.get("reviewability") != "aggregate_only_individual_packets_not_public":
            errors.append("evidence.json: Finland reviewability must remain aggregate-only")
        if finland.get("case_url") != "/finland":
            errors.append("evidence.json: Finland aggregate must link to /finland")
        nonclaims = finland.get("nonclaims", [])
        if not isinstance(nonclaims, list):
            errors.append("evidence.json: Finland aggregate nonclaims must be a list")
        else:
            nonclaim_text = " ".join(str(value) for value in nonclaims).lower()
            if "not confirmed" not in nonclaim_text:
                errors.append("evidence.json: Finland aggregate must say candidates are unconfirmed")
            if "not a general correctness metric" not in nonclaim_text:
                errors.append("evidence.json: Finland aggregate must disclaim a general correctness metric")

    expected_public_candidate_packets = {
        "NZ-REPORTED-CROSS-REFERENCES-2026-06": ("nz", 3),
        "UK-REPORTED-CURRENT-TEXT-2026": ("uk", 2),
    }
    cases_by_id = {item.get("case_id"): item for item in evidence.get("cases", [])}
    for case_id, (jurisdiction, count) in expected_public_candidate_packets.items():
        item = cases_by_id.get(case_id)
        if not item:
            errors.append(f"evidence.json: missing public candidate packet {case_id}")
            continue
        if item.get("jurisdiction") != jurisdiction or item.get("count") != count:
            errors.append(f"evidence.json: {case_id} jurisdiction/count drifted")
        if item.get("record_type") != "public_candidate_packet" or item.get("status") != "candidate_awaiting_disposition":
            errors.append(f"evidence.json: {case_id} must remain a candidate packet awaiting disposition")
        if item.get("case_url", "").split("#", 1)[0] != "/cases/reported-qa-candidates":
            errors.append(f"evidence.json: {case_id} must link to the public candidate packet")

    stable_evidence = snapshot.get("stable_public_evidence", {})
    if stable_evidence.get("new_zealand_reported_candidates") != 3:
        errors.append("public-snapshot.json: unexpected New Zealand candidate count")
    if stable_evidence.get("united_kingdom_reported_candidates") != 2:
        errors.append("public-snapshot.json: unexpected United Kingdom candidate count")

    assurance = json.loads((data_dir / "assurance-claims.json").read_text(encoding="utf-8"))
    if assurance.get("schema") != "lawvm.assurance-claim-registry.v1":
        errors.append("assurance-claims.json: unexpected schema")
    if assurance.get("snapshot_date") != snapshot.get("snapshot_date"):
        errors.append("assurance-claims.json: snapshot date differs from public snapshot")
    if not assurance.get("public_code_status"):
        errors.append("assurance-claims.json: public code status must be explicit")
    for stale_field in (
        "inspected_core_commit",
        "core_working_tree_clean",
        "core_snapshot_status",
        "public_runnable_core_baseline",
        "website_parent_baseline_commit",
        "website_source_commit",
        "website_source_identity",
        "website_working_tree_clean",
    ):
        if stale_field in assurance:
            errors.append(f"assurance-claims.json: stale implementation-identity field {stale_field}")
    mechanisms = assurance.get("mechanism_vocabulary", {})
    outcomes = assurance.get("outcome_vocabulary", {})
    registry_gaps = assurance.get("registry_gaps", {})
    if not isinstance(registry_gaps, dict) or not registry_gaps or not all(registry_gaps.values()):
        errors.append("assurance-claims.json: registry gaps must be explicit and non-empty")
    claims = assurance.get("claims", [])
    claim_ids = [item.get("claim_id") for item in claims]
    if not claims:
        errors.append("assurance-claims.json: no claims")
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("assurance-claims.json: duplicate claim_id")
    for claim in claims:
        claim_id = claim.get("claim_id", "<unknown>")
        missing = ASSURANCE_CLAIM_FIELDS - claim.keys()
        if missing:
            errors.append(f"assurance-claims.json: {claim_id} missing {sorted(missing)}")
        for field in ("mechanisms", "assumptions", "specification_paths", "implementation_paths", "test_paths", "known_limits"):
            if not isinstance(claim.get(field), list) or not claim.get(field):
                errors.append(f"assurance-claims.json: {claim_id} requires non-empty {field}")
        for mechanism in claim.get("mechanisms", []):
            if mechanism not in mechanisms:
                errors.append(f"assurance-claims.json: {claim_id} uses unknown mechanism {mechanism}")

    demo = json.loads((data_dir / "assurance-demo.json").read_text(encoding="utf-8"))
    if demo.get("schema") != "lawvm.synthetic-assurance-demo.v2":
        errors.append("assurance-demo.json: unexpected schema")
    if demo.get("status") != "synthetic_teaching_fixture_not_certificate":
        errors.append("assurance-demo.json: missing synthetic non-certificate status")
    scenarios = demo.get("scenarios", [])
    scenario_map = {item.get("id"): item.get("outcome") for item in scenarios}
    expected_scenarios = {
        "clean": "established_within_scope",
        "blocked": "blocked",
        "violated": "invalid",
        "uncheckable": "uncheckable",
    }
    if scenario_map != expected_scenarios:
        errors.append(f"assurance-demo.json: unexpected scenario/outcome map {scenario_map}")
    for scenario_id, outcome in scenario_map.items():
        if outcome not in outcomes:
            errors.append(f"assurance-demo.json: {scenario_id} uses unknown outcome {outcome}")
    required_scenario_fields = {
        "source",
        "account",
        "operation",
        "mutation",
        "resolution",
        "temporal",
        "checker",
        "receipt",
        "observation",
        "roots",
        "permitted_wording",
    }
    for scenario in scenarios:
        missing = required_scenario_fields - scenario.keys()
        if missing:
            errors.append(f"assurance-demo.json: {scenario.get('id', '<unknown>')} missing {sorted(missing)}")
        account = scenario.get("account", {})
        required_account_fields = {"declared", "emitted", "rejected", "typed_observation", "unaccounted"}
        if set(account) != required_account_fields:
            errors.append(f"assurance-demo.json: {scenario.get('id', '<unknown>')} has an ambiguous or incomplete account")
        elif any(not isinstance(account[field], int) or account[field] < 0 for field in required_account_fields):
            errors.append(f"assurance-demo.json: {scenario.get('id', '<unknown>')} account values must be non-negative integers")
        elif account["emitted"] + account["rejected"] + account["typed_observation"] + account["unaccounted"] != account["declared"]:
            errors.append(f"assurance-demo.json: {scenario.get('id', '<unknown>')} account does not balance")

    verification = json.loads((data_dir / "verification-map.json").read_text(encoding="utf-8"))
    if verification.get("schema") != "lawvm.public-verification-map.v1":
        errors.append("verification-map.json: unexpected schema")
    if verification.get("snapshot_date") != snapshot.get("snapshot_date"):
        errors.append("verification-map.json: snapshot date differs from public snapshot")
    if "core_revision" in verification:
        errors.append("verification-map.json: stale public core revision field")
    mechanism_ids = [item.get("id") for item in verification.get("mechanisms", [])]
    if not mechanism_ids or len(mechanism_ids) != len(set(mechanism_ids)):
        errors.append("verification-map.json: missing or duplicate mechanism ids")

    review = json.loads((data_dir / "review-protocol.json").read_text(encoding="utf-8"))
    if review.get("schema") != "lawvm.public-claim-review-protocol.v2":
        errors.append("review-protocol.json: unexpected schema")
    if len(review.get("challenge_dimensions", [])) != 8:
        errors.append("review-protocol.json: expected eight challenge dimensions")
    expected_review_dispositions = {"clean", "wording_fix", "evidence_gap", "blocked", "unresolved", "invalid", "uncheckable", "not_claimed"}
    if set(review.get("review_dispositions", [])) != expected_review_dispositions:
        errors.append("review-protocol.json: reviewer dispositions are incomplete or drifted")
    expected_claim_outcomes = {"established_within_scope", "qualified", "blocked", "unresolved", "invalid", "uncheckable", "not_claimed"}
    if set(review.get("public_claim_outcomes", [])) != expected_claim_outcomes:
        errors.append("review-protocol.json: public claim outcomes are incomplete or drifted")


def main() -> int:
    errors: list[str] = []
    if not SITE.is_dir():
        print("FAIL: _site does not exist; run ./build.sh", file=sys.stderr)
        return 1

    pages = sorted(SITE.rglob("*.html"))
    urls = sitemap_urls()
    seen_canonicals: dict[str, Path] = {}

    for page in pages:
        parser = parse_page(page)
        rel = page.relative_to(SITE)
        if parser.h1_count != 1:
            errors.append(f"{rel}: expected one h1, got {parser.h1_count}")
        for previous, current in zip(parser.heading_levels, parser.heading_levels[1:]):
            if current > previous + 1:
                errors.append(f"{rel}: heading level jumps from h{previous} to h{current}")
        if len(parser.descriptions) != 1 or not parser.descriptions[0]:
            errors.append(f"{rel}: expected one non-empty meta description")
        if len(parser.canonicals) != 1 or not parser.canonicals[0]:
            errors.append(f"{rel}: expected one canonical URL")
        for prop in REQUIRED_OG_PROPERTIES:
            values = parser.meta_properties.get(prop, [])
            if len(values) != 1 or not values[0]:
                errors.append(f"{rel}: expected one non-empty {prop} property")
        for name in REQUIRED_TWITTER_NAMES:
            values = parser.meta_names.get(name, [])
            if len(values) != 1 or not values[0]:
                errors.append(f"{rel}: expected one non-empty {name} metadata value")
        if parser.meta_names.get("twitter:card") != ["summary_large_image"]:
            errors.append(f"{rel}: twitter:card must be summary_large_image")
        og_image = parser.meta_properties.get("og:image", [None])[0]
        twitter_image = parser.meta_names.get("twitter:image", [None])[0]
        if og_image and twitter_image and og_image != twitter_image:
            errors.append(f"{rel}: Twitter and Open Graph images disagree")
        if parser.meta_properties.get("og:image:width") != ["1200"]:
            errors.append(f"{rel}: og:image:width must be 1200")
        if parser.meta_properties.get("og:image:height") != ["630"]:
            errors.append(f"{rel}: og:image:height must be 630")
        if og_image and str(og_image).startswith("https://lawvm.org/"):
            image_target = SITE / str(og_image).removeprefix("https://lawvm.org/")
            if not image_target.is_file():
                errors.append(f"{rel}: missing local Open Graph image {og_image}")
        expected_image = EXPECTED_SOCIAL_IMAGES.get(rel)
        if expected_image and og_image != expected_image:
            errors.append(f"{rel}: expected page-specific Open Graph image {expected_image}")
        if len(parser.ids) != len(set(parser.ids)):
            errors.append(f"{rel}: duplicate HTML id")
        if page not in STANDALONE:
            if "/assets/css/style.css" not in parser.stylesheets:
                errors.append(f"{rel}: missing main stylesheet")
            if parser.headers < 1 or parser.footers != 1:
                errors.append(f"{rel}: missing site header/footer")
            if parser.mains != 1 or parser.main_content_ids != 1:
                errors.append(f"{rel}: expected one #main-content landmark")
            if parser.skip_links != 1:
                errors.append(f"{rel}: expected one skip link")
            raw_html = page.read_text(encoding="utf-8")
            blocks = re.findall(r'<script\s+type="application/ld\+json">(.*?)</script>', raw_html, flags=re.DOTALL | re.IGNORECASE)
            if not blocks:
                errors.append(f"{rel}: missing structured data")
            for block in blocks:
                try:
                    json.loads(block)
                except json.JSONDecodeError as exc:
                    errors.append(f"{rel}: invalid structured data JSON: {exc}")
        for href in parser.links:
            if not link_exists(page, href):
                errors.append(f"{rel}: broken internal link {href}")
        if parser.canonicals and parser.canonicals[0]:
            canonical = str(parser.canonicals[0])
            og_urls = parser.meta_properties.get("og:url", [])
            if og_urls != [canonical]:
                errors.append(f"{rel}: og:url must match canonical URL")
            if canonical in seen_canonicals and page not in NOINDEX_ALIAS:
                errors.append(f"{rel}: duplicate canonical also used by {seen_canonicals[canonical].relative_to(SITE)}")
            else:
                seen_canonicals[canonical] = page
            if not parser.noindex and canonical not in urls:
                errors.append(f"{rel}: canonical absent from sitemap: {canonical}")

    validate_json(errors)

    combined_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in pages)
    if "<!-- #include " in combined_text:
        errors.append("unexpanded fragment marker remains")
    validate_public_surface(errors)
    validate_positioning(errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"Site validation complete: {len(pages)} HTML pages, {len(urls)} sitemap URLs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
