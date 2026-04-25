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
    -not -path './.git/*' \
    -not -path './_site/*' \
    -not -path './_fragments/*' \
    -not -name '*.html' \
    -not -name 'TODO.md' \
    -not -name 'build.sh' \
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
    _site/articles/truth-surfaces/index.html \
    _site/favicon.svg \
    _site/sitemap.xml; do
    if [ ! -f "$required" ]; then
        echo "FAIL: missing required build artifact: $required" >&2
        exit 1
    fi
done

echo "Build complete: _site/"
