#!/usr/bin/env bash
set -Eeuo pipefail

SRCDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SRCDIR"

rm -rf _site
mkdir _site

# Copy static assets
cp -r assets _site/

# Copy all non-HTML static files preserving directory structure. HTML is copied
# below after fragment substitution, so source fragments and generated output
# are excluded here.
find . -type f \
    -not -path './.*' \
    -not -path './.git/*' \
    -not -path './_site/*' \
    -not -path './_fragments/*' \
    -not -path './briefs-src/*' \
    -not -name '*.html' \
    -not -name 'TODO.md' \
    -not -name 'build.sh' \
    -not -path './scripts/*' \
    -not -path './assets/*' | while read -r f; do
    dest="_site/${f#./}"
    mkdir -p "$(dirname "$dest")"
    cp "$f" "$dest"
done

# Copy all HTML files. Non-index pages are emitted as directory indexes so
# extensionless URLs like /finland and /articles/truth-surfaces work on plain
# static hosting without custom rewrites.
find . -name '*.html' -not -path './_site/*' -not -path './_fragments/*' | while read -r f; do
    rel="${f#./}"
    if [ "$(basename "$rel")" = "index.html" ]; then
        out="_site/$rel"
    else
        out="_site/${rel%.html}/index.html"
    fi
    mkdir -p "$(dirname "$out")"
    cp "$f" "$out"
done

# Fragment substitution
for frag in _fragments/*.html; do
    [ -f "$frag" ] || continue
    name="$(basename "$frag" .html)"
    marker="<!-- #include $name -->"
    find _site -name '*.html' | while read -r page; do
        if grep -q "$marker" "$page"; then
            sed -i "/$marker/{
                r $frag
                d
            }" "$page"
        fi
    done
done

# Generate the assurance status page from the same registry published as JSON.
python3 scripts/generate_assurance_status.py

# Normalize release-wide landmarks, skip navigation, and fallback structured data.
python3 scripts/finalize_html.py

# Assert: no unsubstituted includes remain
if grep -rn '<!-- #include ' _site/ 2>/dev/null; then
    echo "FAIL: unsubstituted <!-- #include --> markers remain in _site/" >&2
    exit 1
fi

for required in \
    _site/index.html \
    _site/finland/index.html \
    _site/architecture/index.html \
    _site/docs/getting-started/index.html \
    _site/explore/index.html \
    _site/evidence/index.html \
    _site/jurisdictions/index.html \
    _site/pilots/index.html \
    _site/assessment/index.html \
    _site/assurance/index.html \
    _site/assurance/status/index.html \
    _site/assurance/limits/index.html \
    _site/assurance/dossier/index.html \
    _site/assurance/verification/index.html \
    _site/assurance/review/index.html \
    _site/assurance/brief/index.html \
    _site/solutions/index.html \
    _site/solutions/consolidation-assurance/index.html \
    _site/solutions/drafting-publication-ci/index.html \
    _site/solutions/legal-data-conformance/index.html \
    _site/solutions/multilingual-legislation/index.html \
    _site/solutions/source-readiness/index.html \
    _site/solutions/source-recovery/index.html \
    _site/fi/lainsaadannon-kieliversioiden-eheys/index.html \
    _site/fi/sv-lagstiftningskonformitet/index.html \
    _site/technology/ecosystem/index.html \
    _site/assets/data/frontends.json \
    _site/assets/data/evidence.json \
    _site/assets/data/public-snapshot.json \
    _site/assets/data/assurance-claims.json \
    _site/assets/data/assurance-demo.json \
    _site/assets/data/verification-map.json \
    _site/assets/data/review-protocol.json \
    _site/assets/js/assurance-dossier.js \
    _site/assets/js/evidence-ledger.js \
    _site/assets/js/frontend-context.js \
    _site/assets/briefs/lawvm-fi-sv-kieliversiopilotti.pdf \
    _site/assets/briefs/lawvm-fi-sv-sprakversionspilot.pdf \
    _site/assets/briefs/lawvm-institutional-assurance.pdf \
    _site/assets/og/lawvm-evidence.png \
    _site/articles/truth-surfaces/index.html \
    _site/favicon.svg \
    _site/sitemap.xml; do
    if [ ! -f "$required" ]; then
        echo "FAIL: missing required build artifact: $required" >&2
        exit 1
    fi
done

if find _site -name '.*' -print -quit | grep -q .; then
    echo "FAIL: private dotfile copied into _site/" >&2
    find _site -name '.*' -print >&2
    exit 1
fi

python3 scripts/check_site.py

echo "Build complete: _site/"
