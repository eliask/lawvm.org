<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Assurance Claim Status &mdash; LawVM</title>
    <meta name="description" content="Registry-generated LawVM assurance claims with exact scope, mechanisms, deployment boundary, assumptions, evidence paths, permitted wording, and limitations.">
    <link rel="canonical" href="https://lawvm.org/assurance/status">
    <meta property="og:title" content="Assurance claim status — LawVM">
    <meta property="og:description" content="No scalar proof score: inspect each bounded mechanism, scope, deployment state, and non-claim.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://lawvm.org/assurance/status">
    <meta property="og:site_name" content="LawVM">
    <link rel="stylesheet" href="/assets/css/style.css">
@@HEAD_END@@
</head>
<body>
<header><div class="wrap"><a class="logo" href="/">LawVM</a><nav aria-label="Primary navigation">
@@NAV_CONTENT@@
@@THEME_TOGGLE@@
</nav></div></header>
<main id="main-content">
    <section class="wrap-wide page-heading">
        <p class="section-kicker">Generated from the public claim registry</p>
        <h1>Assurance claim status</h1>
        <p class="lead">Each record separates the property, scope, mechanism, deployment boundary, assumptions, permitted wording, and known limit. There is no single proof score or jurisdiction-wide verified badge.</p>
        @@SNAPSHOT@@
        <div class="page-actions"><a class="button button-primary" href="/assets/data/assurance-claims.json">Download the registry JSON</a><a class="button" href="/assurance/limits">Read the trust boundary</a></div>
    </section>
    <section class="section-block"><div class="wrap-wide">
        <p class="section-kicker">Current bounded records</p><h2>Mechanisms, not marketing grades</h2>
        <div class="assurance-claim-list">
@@CLAIMS@@
        </div>
    </div></section>
    <section class="section-block"><div class="wrap-wide">
        <p class="section-kicker">Vocabulary</p><h2>Orthogonal mechanism labels</h2>
        <p class="section-intro">A record can be typed and property-tested without being independently checked or uniformly production-blocking.</p>
        <div class="card-grid">
@@VOCABULARY@@
        </div>
    </div></section>
    <section class="section-block"><div class="wrap-wide">
        <p class="section-kicker">Outcome vocabulary</p><h2>Missing proof and contradiction are different states</h2>
        <div class="card-grid">
@@OUTCOMES@@
        </div>
    </div></section>
    <section class="section-block"><div class="wrap-wide">
        <p class="section-kicker">Registry incompleteness</p><h2>What this first registry still does not carry</h2>
        <p class="section-intro">These gaps stay machine-readable instead of being filled with invented commands, owners, witnesses, or release claims.</p>
        <div class="status-list">
@@REGISTRY_GAPS@@
        </div>
        <div class="claim-boundary"><strong>Path boundary:</strong> specification, implementation, and test entries are repository-relative evidence locators reviewed on the snapshot date. The public repository is a moving development surface, so the listed paths are not a frozen release or exact reproduction set. This registry is not a release certificate, stable public schema, or external audit.</div>
    </div></section>
</main>
@@FOOTER@@
</body>
</html>
