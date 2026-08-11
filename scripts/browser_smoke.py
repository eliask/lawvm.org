#!/usr/bin/env python3
"""Run browser-level smoke checks against a locally served built site."""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = os.environ.get("LAWVM_SITE_URL", "http://127.0.0.1:8765")
SCREENSHOT_DIR = Path(os.environ.get("LAWVM_SCREENSHOT_DIR", "/tmp/lawvm-browser-smoke"))
CHROMIUM_PATH = os.environ.get("LAWVM_CHROMIUM_PATH")


def check_page(page, path: str, width: int, height: int) -> None:
    failures: list[str] = []
    page.set_viewport_size({"width": width, "height": height})
    page.on("console", lambda message: failures.append(f"console {message.type}: {message.text}") if message.type == "error" else None)
    page.on("pageerror", lambda error: failures.append(f"pageerror: {error}"))
    response = page.goto(f"{BASE_URL}{path}", wait_until="networkidle")
    assert response and response.ok, f"{path}: HTTP {response.status if response else 'none'}"
    assert page.locator("h1").count() == 1, f"{path}: expected one h1"
    assert page.locator("h1").is_visible(), f"{path}: h1 is not visible"
    dimensions = page.evaluate(
        """() => ({
          viewport: document.documentElement.clientWidth,
          content: document.documentElement.scrollWidth
        })"""
    )
    offenders = page.evaluate(
        """() => Array.from(document.querySelectorAll('*')).flatMap((element) => {
          const rect = element.getBoundingClientRect();
          if (rect.right <= document.documentElement.clientWidth + 1 && rect.left >= -1) return [];
          return [{
            tag: element.tagName.toLowerCase(),
            className: String(element.className || '').slice(0, 80),
            text: String(element.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 100),
            left: Math.round(rect.left),
            right: Math.round(rect.right)
          }];
        }).slice(-8)"""
    )
    assert dimensions["content"] <= dimensions["viewport"] + 1, (
        f"{path}: horizontal overflow {dimensions['content']} > {dimensions['viewport']}; {offenders}"
    )
    assert not failures, f"{path}: {'; '.join(failures)}"


def main() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        "/",
        "/about/",
        "/about/project-status/",
        "/docs/",
        "/evidence/",
        "/essays/",
        "/finland/",
        "/explore/",
        "/jurisdictions/",
        "/pilots/",
        "/assessment/",
        "/assurance/",
        "/assurance/limits/",
        "/assurance/dossier/",
        "/assurance/verification/",
        "/assurance/review/",
        "/assurance/brief/",
        "/solutions/",
        "/solutions/consolidation-assurance/",
        "/solutions/multilingual-legislation/",
        "/solutions/source-readiness/",
        "/solutions/drafting-publication-ci/",
        "/solutions/legal-data-conformance/",
        "/technology/ecosystem/",
        "/cases/estonia-audiitors-95-2/",
        "/cases/reported-qa-candidates/",
        "/fi/lainsaadannon-kieliversioiden-eheys/",
        "/fi/sv-lagstiftningskonformitet/",
    ]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=CHROMIUM_PATH or None)
        page = browser.new_page()
        for path in paths:
            check_page(page, path, 1440, 1000)
            check_page(page, path, 390, 844)

        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{BASE_URL}/assessment/", wait_until="networkidle")
        page.locator("#assessment-jurisdiction").fill("Example jurisdiction")
        page.locator("#assessment-institution-role").fill("Example publisher / assurance lead")
        page.locator("#assessment-source-contact").fill("Source systems owner")
        page.locator("#assessment-decision-owner").fill("Publication decision owner")
        page.locator("#assessment-data-boundary").fill("Public links only")
        page.locator('input[name="objective"][value="multilingual"]').check()
        page.locator('input[name="authority"][value="authoritative"]').check()
        page.locator('input[name="format"][value="xml"]').check()
        for value in ("originals", "amendments", "versions", "dates", "links", "identifiers"):
            page.locator(f'input[name="evidence"][value="{value}"]').check()
        page.locator('input[name="languages"][value="multiple"]').check()
        page.locator('input[name="reviewer"]').check()
        page.get_by_role("button", name="Generate first-pass assessment").click()
        result = page.locator("#assessment-result")
        assert result.is_visible(), "assessment: result did not become visible"
        assert page.locator("#result-title").evaluate("element => document.activeElement === element")
        assert "Parallel-expression review tranche" in page.locator("#result-title").inner_text()
        assert page.locator("#result-next-action").get_attribute("href") == "/pilots#multilingual"
        assert page.locator("#email-assessment").get_attribute("href").startswith("mailto:hello@lawvm.org")
        assert "Publication%20decision%20owner" in page.locator("#email-assessment").get_attribute("href")
        assert "Non-public%20material" in page.locator("#email-assessment").get_attribute("href")
        theme = page.locator(".theme-toggle")
        theme.click()
        assert theme.get_attribute("aria-pressed") == "true"
        assert page.locator("html").get_attribute("data-theme") == "dark"

        page.goto(f"{BASE_URL}/assurance/dossier/", wait_until="networkidle")
        dossier_outcome = page.locator("#dossier-outcome")
        assert "established within scope" in dossier_outcome.inner_text().lower()
        assert page.locator(".account-segment:visible").count() == 3
        assert "synthetic:source:a" in page.locator("#root-details").inner_text()
        scenario_expectations = {
            "Missing effective moment": "blocked",
            "Observed write outside the bound target": "invalid",
            "Committed artifact unavailable": "uncheckable",
        }
        for label, expected in scenario_expectations.items():
            page.get_by_role("button", name=label, exact=True).click()
            assert dossier_outcome.inner_text().strip().lower() == expected
        assert page.locator("#dossier-panel .status-row").count() >= 9
        assert "required artifact unavailable" in page.locator("#checker-details").inner_text().lower()
        assert page.locator(".account-segment:visible").count() == 1
        assert "uncheckable" in page.locator("#dossier-wording").inner_text().lower()

        page.goto(f"{BASE_URL}/evidence/", wait_until="networkidle")
        assert page.locator(".ledger-record").count() == 4
        page.locator("#ledger-jurisdiction").select_option("ee")
        assert page.locator(".ledger-record").count() == 1
        assert "EE-2025-AUDIIT-95-2-1" in page.locator(".ledger-record").inner_text()
        page.locator("#ledger-jurisdiction").select_option("")
        page.locator("#ledger-type").select_option("aggregate_candidate_count")
        assert page.locator(".ledger-record").count() == 1
        assert "22 reported candidate records" in page.locator(".ledger-record").inner_text()
        page.locator("#ledger-type").select_option("public_candidate_packet")
        assert page.locator(".ledger-record").count() == 2
        assert "NZ-REPORTED-CROSS-REFERENCES-2026-06" in " ".join(page.locator(".ledger-record").all_inner_texts())

        page.goto(f"{BASE_URL}/assessment/?frontend=jp", wait_until="networkidle")
        assert "Japan" in page.locator("#frontend-context").inner_text()
        assert page.locator("#assessment-jurisdiction").input_value() == "Japan"
        page.goto(f"{BASE_URL}/pilots/?frontend=ch#frontend", wait_until="networkidle")
        assert "Switzerland" in page.locator("#frontend-context").inner_text()
        assert "Switzerland" in page.locator("#pilot-email").get_attribute("href")

        page.goto(f"{BASE_URL}/about/project-status/", wait_until="networkidle")
        status_text = page.locator("main").inner_text().lower()
        for phrase in ("beta-stage", "pre-1.0", "profile-specific"):
            assert phrase in status_text, f"project status: missing {phrase}"
        assert "legal authority and broader correctness require separate institutional and evidential support" in status_text

        page.goto(f"{BASE_URL}/solutions/source-readiness/", wait_until="networkidle")
        source_text = page.locator("main").inner_text().lower()
        assert "ocr supplies candidate text and locators" in source_text
        assert "a bounded source-readiness pilot can produce this documentary evidence package" in source_text

        for route in ("/finland/", "/explore/"):
            page.goto(f"{BASE_URL}{route}", wait_until="networkidle")
            finnish_link = page.locator('a[href*="statute-timeline-manifest-fi-all-no-amendments.json"]')
            assert finnish_link.count() == 1
            assert finnish_link.get_attribute("href").endswith("#ui_lang=en")

        for href in (
            "/assets/briefs/lawvm-fi-sv-kieliversiopilotti.pdf",
            "/assets/briefs/lawvm-fi-sv-sprakversionspilot.pdf",
            "/assets/briefs/lawvm-institutional-assurance.pdf",
        ):
            response = page.request.get(f"{BASE_URL}{href}")
            assert response.ok, f"{href}: HTTP {response.status}"
            assert response.headers.get("content-type", "").startswith("application/pdf")

        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        primary_nav = page.get_by_role("navigation", name="Primary navigation")
        assert primary_nav.get_by_role("link", name="About", exact=True).is_visible()
        public_text = page.locator("body").inner_text()
        for discarded_label in ("Machine-readable registry", "Assurance profile", "Open the frontend starter"):
            assert discarded_label not in public_text
        page.screenshot(path=SCREENSHOT_DIR / "home-desktop.png", full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=SCREENSHOT_DIR / "home-mobile.png", full_page=True)
        page.goto(f"{BASE_URL}/assessment/", wait_until="networkidle")
        page.screenshot(path=SCREENSHOT_DIR / "assessment-mobile.png", full_page=True)
        page.goto(f"{BASE_URL}/solutions/source-readiness/", wait_until="networkidle")
        page.screenshot(path=SCREENSHOT_DIR / "source-readiness-mobile.png", full_page=True)
        page.goto(f"{BASE_URL}/cases/reported-qa-candidates/", wait_until="networkidle")
        page.screenshot(path=SCREENSHOT_DIR / "reported-qa-candidates-mobile.png", full_page=True)
        page.goto(f"{BASE_URL}/jurisdictions/", wait_until="networkidle")
        page.screenshot(path=SCREENSHOT_DIR / "jurisdictions-mobile.png", full_page=True)
        assert "Assurance profile" not in page.locator("body").inner_text()
        page.goto(f"{BASE_URL}/assurance/", wait_until="networkidle")
        page.screenshot(path=SCREENSHOT_DIR / "assurance-mobile.png", full_page=True)
        browser.close()

    print(f"Browser smoke complete: {len(paths)} routes at desktop and mobile widths")


if __name__ == "__main__":
    main()
