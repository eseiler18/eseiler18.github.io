#!/usr/bin/env bash
# Compile the PDF CV (cv/resume.typ) from dist/cv/data.json (produced by `astro build`).
#
#   bash scripts/build_cv.sh            # public versions -> dist/cv/ (published with the site)
#   bash scripts/build_cv.sh --private  # + phone from cv/private.yaml -> cv/out/ (never published)
#
# cv/private.yaml (git-ignored) contains e.g.:   phone: "+41 00 000 00 00"
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f dist/cv/data.json ] || npx astro build

out=dist/cv
args=()
if [ "${1:-}" = "--private" ]; then
  out=cv/out
  if [ -f cv/private.yaml ]; then
    phone=$(sed -n 's/^phone:[[:space:]]*//p' cv/private.yaml | tr -d '"'"'")
    [ -n "$phone" ] && args+=(--input "phone=$phone")
  fi
fi
mkdir -p "$out"

for pair in resume:Emilien_Seiler_CV; do
  src=${pair%%:*}
  name=${pair##*:}
  typst compile --root . --font-path cv/fonts --ignore-system-fonts \
    --input data=/dist/cv/data.json "${args[@]+"${args[@]}"}" "cv/$src.typ" "$out/$name.pdf"
  echo "built $out/$name.pdf"
done
