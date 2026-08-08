#!/usr/bin/env bash
# DSP AI Indicator — Enterprise Audit Package Generator v1.0.0
# One-command regenerate: docs + source + configs + workflows + ZIPs + validation.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PKG_NAME="DSP_AI_INDICATOR_AUDIT_PACKAGE"
PKG_ROOT="${SCRIPT_DIR}/${PKG_NAME}"
TEMPLATES="${SCRIPT_DIR}/templates"
SIZE_LIMIT_MB=350
GENERATED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
SKIP_ZIP="${SKIP_ZIP:-0}"

EXCLUDE_DIRS_REGEX='/(node_modules|\.next|\.git|coverage|dist|build|out|\.cache|\.turbo|playwright-report|test-results|logs|tmp|temp|\.idea|\.vscode|\.venv|venv|__pycache__|\.mypy_cache|\.pytest_cache|\.ruff_cache|htmlcov|\.tox|\.nox)(/|$)'
EXCLUDE_FILES_REGEX='\.(log|cache|tsbuildinfo|pyc|pyo)$|/(Thumbs\.db|\.DS_Store|\.coverage|coverage\.xml|coverage\.json)$|\.egg-info(/|$)'

banner() { echo ""; echo "=== $* ==="; }

should_exclude() {
  local p="$1"
  [[ "$p" =~ $EXCLUDE_DIRS_REGEX ]] && return 0
  [[ "$p" =~ $EXCLUDE_FILES_REGEX ]] && return 0
  return 1
}

copy_tree_filtered() {
  local src="$1" dest="$2"
  local count=0
  if [[ ! -d "$src" ]]; then
    echo "  skip (missing): $src"
    echo 0
    return 0
  fi
  mkdir -p "$dest"
  while IFS= read -r -d '' f; do
    if should_exclude "$f"; then continue; fi
    local rel="${f#"$src"/}"
    mkdir -p "$(dirname "$dest/$rel")"
    cp -p "$f" "$dest/$rel"
    count=$((count + 1))
  done < <(find "$src" -type f -print0 2>/dev/null)
  echo "$count"
}

copy_file_safe() {
  local src="$1" dest_dir="$2" dest_name="${3:-}"
  if [[ ! -f "$src" ]]; then return 1; fi
  mkdir -p "$dest_dir"
  if [[ -n "$dest_name" ]]; then
    cp -p "$src" "$dest_dir/$dest_name"
  else
    cp -p "$src" "$dest_dir/"
  fi
  return 0
}

dir_size_bytes() {
  local p="$1"
  if [[ ! -e "$p" ]]; then echo 0; return; fi
  du -sb "$p" 2>/dev/null | awk '{print $1}'
}

format_size() {
  local b="$1"
  if (( b >= 1073741824 )); then awk -v b="$b" 'BEGIN{printf "%.2f GB", b/1073741824}'; return; fi
  if (( b >= 1048576 )); then awk -v b="$b" 'BEGIN{printf "%.2f MB", b/1048576}'; return; fi
  if (( b >= 1024 )); then awk -v b="$b" 'BEGIN{printf "%.2f KB", b/1024}'; return; fi
  echo "${b} B"
}

make_zip() {
  local folder="$1" zip_path="$2"
  rm -f "$zip_path"
  if [[ ! -d "$folder" ]]; then return 1; fi
  (cd "$folder" && zip -qr "$zip_path" .)
}

banner "DSP Enterprise Audit Package Generator v1.0.0"
echo "RepoRoot : $REPO_ROOT"
echo "Package  : $PKG_ROOT"

banner "Preparing package directories"
rm -rf "${PKG_ROOT}/source" "${PKG_ROOT}/configs" "${PKG_ROOT}/workflows" \
  "${PKG_ROOT}/docs/design" "${PKG_ROOT}/docs/governance" "${PKG_ROOT}/docs/research" \
  "${PKG_ROOT}/docs/releases" "${PKG_ROOT}/docs/reviews" "${PKG_ROOT}/docs/project" \
  "${PKG_ROOT}/docs/root"
mkdir -p \
  "${PKG_ROOT}/docs/root" "${PKG_ROOT}/docs/project" \
  "${PKG_ROOT}/docs/design" "${PKG_ROOT}/docs/governance" \
  "${PKG_ROOT}/docs/research" "${PKG_ROOT}/docs/releases" "${PKG_ROOT}/docs/reviews" \
  "${PKG_ROOT}/source/web" "${PKG_ROOT}/source/packages" \
  "${PKG_ROOT}/configs/root" "${PKG_ROOT}/configs/web" \
  "${PKG_ROOT}/workflows" "${PKG_ROOT}/manifests" \
  "${PKG_ROOT}/archives" "${PKG_ROOT}/reports"

banner "Installing narrative guides"
GUIDES=(
  00_START_HERE.md 01_PROJECT_OVERVIEW.md 02_ARCHITECTURE.md
  03_MODULE_INDEX.md 04_FEATURE_MATRIX.md 05_RELEASE_STATUS.md
  06_KNOWN_LIMITATIONS.md 07_REPOSITORY_MAP.md 08_DEPENDENCY_REPORT.md
  09_AUDIT_GUIDE.md AUDIT_MANIFEST.md
)
for g in "${GUIDES[@]}"; do
  [[ -f "${TEMPLATES}/${g}" ]] || { echo "Missing template: ${TEMPLATES}/${g}"; exit 1; }
  cp -p "${TEMPLATES}/${g}" "${PKG_ROOT}/${g}"
done

banner "Copying root documentation"
copy_file_safe "${REPO_ROOT}/README.md" "${PKG_ROOT}/docs/root" || true
copy_file_safe "${REPO_ROOT}/CONTRIBUTING.md" "${PKG_ROOT}/docs/root" || true
copy_file_safe "${REPO_ROOT}/LICENSE" "${PKG_ROOT}/docs/root" || true
copy_file_safe "${REPO_ROOT}/CHANGELOG.md" "${PKG_ROOT}/docs/root" || true
copy_file_safe "${REPO_ROOT}/docs/CHANGELOG.md" "${PKG_ROOT}/docs/root" "CHANGELOG_docs.md" || true

banner "Copying governance-critical project docs"
PROJECT_DOCS=(
  ARCHITECTURE_BIBLE.md ARCHITECTURE_GOVERNANCE.md ARCHITECTURE_CHECKLIST.md
  CORE_VALUES.md CV_001_DATA_AUTHENTICITY_FIRST.md CV_002_TO_010_TIER0_CORE_VALUES.md
  RESEARCH_STANDARDS.md RS_001_TO_RS_010.md USER_TRUST_STANDARD.md
  PRODUCT_CONSTITUTION.md IMPLEMENTATION_QUALITY_GATE.md CODE_REVIEW_CHECKLIST.md
  KNOWN_LIMITATIONS.md RESEARCH_ARCHITECTURE.md REPORT_ARCHITECTURE.md
  SECURITY_GUIDE.md CONFIGURATION_GUIDE.md RELEASE_ENGINEERING.md
  RELEASE_NOTES_v1.0.0.md PRODUCT_VISION.md PROJECT_CHARTER.md
)
PROJ_COPIED=0
for n in "${PROJECT_DOCS[@]}"; do
  if copy_file_safe "${REPO_ROOT}/docs/${n}" "${PKG_ROOT}/docs/project"; then
    PROJ_COPIED=$((PROJ_COPIED + 1))
  fi
done
echo "  project docs copied: ${PROJ_COPIED}"

banner "Copying docs trees"
for sub in design governance research releases reviews; do
  c="$(copy_tree_filtered "${REPO_ROOT}/docs/${sub}" "${PKG_ROOT}/docs/${sub}" | tail -n1)"
  echo "  docs/${sub} : ${c} files"
done

banner "Copying web source"
WEB_COUNT="$(copy_tree_filtered "${REPO_ROOT}/apps/web/src" "${PKG_ROOT}/source/web/src" | tail -n1)"
echo "  apps/web/src : ${WEB_COUNT} files"
PUB_COUNT="$(copy_tree_filtered "${REPO_ROOT}/apps/web/public" "${PKG_ROOT}/source/web/public" | tail -n1)"
echo "  apps/web/public : ${PUB_COUNT} files"
copy_file_safe "${REPO_ROOT}/apps/web/README.md" "${PKG_ROOT}/source/web" || true
copy_file_safe "${REPO_ROOT}/apps/web/VERSION_MANIFEST.json" "${PKG_ROOT}/source/web" || true

banner "Copying packages source"
PKG_FILE_COUNT=0
PKG_NAMES=()
if [[ -d "${REPO_ROOT}/packages" ]]; then
  for pkg in "${REPO_ROOT}/packages"/*; do
    [[ -d "$pkg" ]] || continue
    name="$(basename "$pkg")"
    PKG_NAMES+=("$name")
    dest="${PKG_ROOT}/source/packages/${name}"
    mkdir -p "$dest"
    for sub in src tests test; do
      if [[ -d "${pkg}/${sub}" ]]; then
        c="$(copy_tree_filtered "${pkg}/${sub}" "${dest}/${sub}" | tail -n1)"
        PKG_FILE_COUNT=$((PKG_FILE_COUNT + c))
      fi
    done
    for f in pyproject.toml README.md setup.py setup.cfg; do
      if copy_file_safe "${pkg}/${f}" "$dest"; then
        PKG_FILE_COUNT=$((PKG_FILE_COUNT + 1))
      fi
    done
  done
fi
echo "  packages mirrored: ${#PKG_NAMES[@]} packages / ${PKG_FILE_COUNT} files"

banner "Copying configs"
for rc in package.json package-lock.json pnpm-lock.yaml yarn.lock \
  tsconfig.json tsconfig.base.json pyproject.toml VERSION \
  PRODUCTION_VERSION_MANIFEST.json Makefile docker-compose.yml \
  .env.example .env.production.example; do
  copy_file_safe "${REPO_ROOT}/${rc}" "${PKG_ROOT}/configs/root" || true
done
shopt -s nullglob
for f in "${REPO_ROOT}"/tsconfig*.json "${REPO_ROOT}"/eslint* "${REPO_ROOT}"/prettier* \
  "${REPO_ROOT}"/vitest* "${REPO_ROOT}"/playwright* "${REPO_ROOT}"/tailwind* \
  "${REPO_ROOT}"/postcss* "${REPO_ROOT}"/next.config.*; do
  [[ -f "$f" ]] && cp -p "$f" "${PKG_ROOT}/configs/root/"
done
for wc in package.json package-lock.json pnpm-lock.yaml yarn.lock tsconfig.json \
  next.config.ts next.config.js next.config.mjs eslint.config.mjs eslint.config.js \
  .eslintrc.json .eslintrc.js .prettierrc .prettierrc.json .prettierignore \
  vitest.config.ts vitest.config.js vitest.setup.ts playwright.config.ts \
  playwright.config.js tailwind.config.ts tailwind.config.js postcss.config.mjs \
  postcss.config.js components.json lighthouserc.cjs next-env.d.ts .env.example; do
  copy_file_safe "${REPO_ROOT}/apps/web/${wc}" "${PKG_ROOT}/configs/web" || true
done
shopt -u nullglob

banner "Copying GitHub workflows"
WF_COUNT="$(copy_tree_filtered "${REPO_ROOT}/.github/workflows" "${PKG_ROOT}/workflows" | tail -n1)"
echo "  workflows: ${WF_COUNT} files"

banner "Writing manifests"
VERSION_TEXT="UNKNOWN"
[[ -f "${REPO_ROOT}/VERSION" ]] && VERSION_TEXT="$(tr -d '\r\n' < "${REPO_ROOT}/VERSION")"
printf '%s\n' "$VERSION_TEXT" > "${PKG_ROOT}/manifests/VERSION"
GIT_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unavailable)"
GIT_BRANCH="$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || echo unavailable)"
GIT_SHORT="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo unavailable)"

{
  echo "# Package Inventory"
  echo ""
  echo "| Field | Value |"
  echo "|---|---|"
  echo "| Generated (UTC) | ${GENERATED_AT} |"
  echo "| Product VERSION | ${VERSION_TEXT} |"
  echo "| Git branch | ${GIT_BRANCH} |"
  echo "| Git SHA | ${GIT_SHA} |"
  echo "| Web source files | ${WEB_COUNT} |"
  echo "| Packages mirrored | ${#PKG_NAMES[@]} |"
  echo "| Package source files | ${PKG_FILE_COUNT} |"
  echo "| Workflows | ${WF_COUNT} |"
  echo ""
  echo "## Packages"
  echo ""
  for n in "${PKG_NAMES[@]}"; do echo "- \`${n}\`"; done
} > "${PKG_ROOT}/manifests/PACKAGE_INVENTORY.md"

{
  echo "# Dependency Summary"
  echo ""
  echo "Generated: ${GENERATED_AT}"
  echo ""
  echo "## Web package"
  echo ""
  if [[ -f "${PKG_ROOT}/configs/web/package.json" ]]; then
    echo "- see \`configs/web/package.json\` and lockfile"
  else
    echo "- web package.json missing"
  fi
  echo ""
  echo "## Python"
  echo ""
  echo "- Root: \`configs/root/pyproject.toml\`"
  echo "- Per-package: \`source/packages/*/pyproject.toml\` (${#PKG_NAMES[@]} packages)"
} > "${PKG_ROOT}/manifests/DEPENDENCY_SUMMARY.md"

{
  echo "# Generation Metadata"
  echo ""
  echo "- generator: tools/audit-package/generate-audit-package.sh"
  echo "- generator_version: 1.0.0"
  echo "- generated_utc: ${GENERATED_AT}"
  echo "- product_version: ${VERSION_TEXT}"
  echo "- git_branch: ${GIT_BRANCH}"
  echo "- git_sha: ${GIT_SHA}"
  echo "- commercial_ga: REJECTED"
  echo "- pilot_posture: GO (closed-beta / institutional pilot)"
} > "${PKG_ROOT}/manifests/GENERATION_META.md"

banner "Validating exclusions"
VIOLATIONS=0
while IFS= read -r -d '' f; do
  rel="${f#"$PKG_ROOT"}"
  if [[ "$rel" =~ /(node_modules|\.next|\.git|coverage|playwright-report|test-results)(/|$) ]]; then
    echo "  violation: $rel"
    VIOLATIONS=$((VIOLATIONS + 1))
  fi
  base="$(basename "$f")"
  if [[ "$base" == *.log || "$base" == *.tsbuildinfo ]]; then
    echo "  violation: $rel"
    VIOLATIONS=$((VIOLATIONS + 1))
  fi
done < <(find "$PKG_ROOT" -type f -print0 2>/dev/null)

if [[ "$VIOLATIONS" -eq 0 ]]; then
  echo "  Exclusion validation: PASS"
else
  echo "  Exclusion validation: FAIL ($VIOLATIONS paths)"
fi

TOTAL_BYTES="$(dir_size_bytes "$PKG_ROOT")"
SOURCE_BYTES="$(dir_size_bytes "${PKG_ROOT}/source")"
DOCS_BYTES="$(dir_size_bytes "${PKG_ROOT}/docs")"
CONFIG_BYTES="$(dir_size_bytes "${PKG_ROOT}/configs")"
FILE_COUNT="$(find "$PKG_ROOT" -type f | wc -l | tr -d ' ')"

banner "Computing sizes"
echo "  Total  : $(format_size "$TOTAL_BYTES") ($FILE_COUNT files)"
echo "  Source : $(format_size "$SOURCE_BYTES")"
echo "  Docs   : $(format_size "$DOCS_BYTES")"
echo "  Configs: $(format_size "$CONFIG_BYTES")"

ZIP_REPORT_LINES=()
if [[ "$SKIP_ZIP" != "1" ]]; then
  banner "Creating ZIP archives"
  rm -f "${PKG_ROOT}/archives"/*.zip
  TOTAL_MB=$(( TOTAL_BYTES / 1024 / 1024))
  if command -v zip >/dev/null 2>&1; then
    make_zip "${PKG_ROOT}/docs" "${PKG_ROOT}/archives/audit-docs.zip" && \
      ZIP_REPORT_LINES+=("| \`audit-docs.zip\` | $(format_size "$(stat -c%s "${PKG_ROOT}/archives/audit-docs.zip" 2>/dev/null || stat -f%z "${PKG_ROOT}/archives/audit-docs.zip")") |")
    make_zip "${PKG_ROOT}/source" "${PKG_ROOT}/archives/audit-source.zip" && \
      ZIP_REPORT_LINES+=("| \`audit-source.zip\` | $(format_size "$(stat -c%s "${PKG_ROOT}/archives/audit-source.zip" 2>/dev/null || stat -f%z "${PKG_ROOT}/archives/audit-source.zip")") |")
    make_zip "${PKG_ROOT}/configs" "${PKG_ROOT}/archives/audit-config.zip" && \
      ZIP_REPORT_LINES+=("| \`audit-config.zip\` | $(format_size "$(stat -c%s "${PKG_ROOT}/archives/audit-config.zip" 2>/dev/null || stat -f%z "${PKG_ROOT}/archives/audit-config.zip")") |")
    make_zip "${PKG_ROOT}/workflows" "${PKG_ROOT}/archives/audit-workflows.zip" && \
      ZIP_REPORT_LINES+=("| \`audit-workflows.zip\` | $(format_size "$(stat -c%s "${PKG_ROOT}/archives/audit-workflows.zip" 2>/dev/null || stat -f%z "${PKG_ROOT}/archives/audit-workflows.zip")") |")
    GUIDE_STAGE="$(mktemp -d)"
    for g in "${GUIDES[@]}"; do cp "${PKG_ROOT}/${g}" "${GUIDE_STAGE}/"; done
    make_zip "$GUIDE_STAGE" "${PKG_ROOT}/archives/audit-guides.zip" && \
      ZIP_REPORT_LINES+=("| \`audit-guides.zip\` | $(format_size "$(stat -c%s "${PKG_ROOT}/archives/audit-guides.zip" 2>/dev/null || stat -f%z "${PKG_ROOT}/archives/audit-guides.zip")") |")
    rm -rf "$GUIDE_STAGE"
    if (( TOTAL_MB > SIZE_LIMIT_MB )); then
      echo "  Package > ${SIZE_LIMIT_MB}MB — split archives preferred (already produced component zips)"
    fi
    FULL_STAGE="$(mktemp -d)"
    rsync -a --exclude 'archives' "${PKG_ROOT}/" "${FULL_STAGE}/"
    make_zip "$FULL_STAGE" "${PKG_ROOT}/archives/DSP_AI_INDICATOR_AUDIT_PACKAGE_FULL.zip" && \
      ZIP_REPORT_LINES+=("| \`DSP_AI_INDICATOR_AUDIT_PACKAGE_FULL.zip\` | $(format_size "$(stat -c%s "${PKG_ROOT}/archives/DSP_AI_INDICATOR_AUDIT_PACKAGE_FULL.zip" 2>/dev/null || stat -f%z "${PKG_ROOT}/archives/DSP_AI_INDICATOR_AUDIT_PACKAGE_FULL.zip")") |")
    rm -rf "$FULL_STAGE"
  else
    echo "  WARNING: zip not installed — skipping archives"
    ZIP_REPORT_LINES+=("| _(zip unavailable)_ | — |")
  fi
fi

banner "Writing AUDIT_PACKAGE_REPORT"
ZIP_SECTION="$(printf '%s\n' "${ZIP_REPORT_LINES[@]:-| _(none)_ | — |}")"
VALIDATION_RESULT="PASS"
[[ "$VIOLATIONS" -eq 0 ]] || VALIDATION_RESULT="FAIL ($VIOLATIONS paths)"

REPORT_PATH="${SCRIPT_DIR}/AUDIT_PACKAGE_REPORT.md"
cat > "$REPORT_PATH" <<EOF
# AUDIT_PACKAGE_REPORT

| Field | Value |
|---|---|
| Generator | \`tools/audit-package/generate-audit-package.sh\` v1.0.0 |
| Generated (UTC) | ${GENERATED_AT} |
| Product VERSION | **${VERSION_TEXT}** |
| Git | \`${GIT_BRANCH}\` @ \`${GIT_SHORT}\` (\`${GIT_SHA}\`) |
| Package path | \`tools/audit-package/${PKG_NAME}/\` |
| Pilot posture | **GO** (closed-beta / institutional pilot) |
| Commercial GA | **REJECTED** |

---

## 1. Executive Summary

Reproducible Enterprise Audit Package for DSP AI Indicator Version **${VERSION_TEXT}**.
Closed-beta / institutional pilot is **GO**. Unrestricted **Commercial GA is REJECTED**.
Thin client: browser presentation only; analytics owned by backend \`/api/v1\` and \`packages/*\`.

---

## 2. Files Included (summary)

| Area | Count / notes |
|---|---|
| Narrative guides | ${#GUIDES[@]} |
| docs/project (key) | ${PROJ_COPIED} files |
| source/web | ${WEB_COUNT} files |
| source/packages | ${#PKG_NAMES[@]} packages / ${PKG_FILE_COUNT} files |
| workflows | ${WF_COUNT} files |
| Total package files | ${FILE_COUNT} |

---

## 3. Files Excluded

\`node_modules\`, \`.next\`, \`.git\`, \`coverage\`, \`dist\`, \`build\`, \`out\`, \`.cache\`, \`.turbo\`,
\`playwright-report\`, \`test-results\`, \`logs\`, \`tmp\`, IDE folders, virtualenvs, \`__pycache__\`,
\`*.egg-info\`, \`*.log\`, \`*.tsbuildinfo\`, and similar generated artefacts. Secrets not copied.

---

## 4. Generated Documents

Guides \`00\`–\`09\`, \`AUDIT_MANIFEST.md\`, and \`manifests/*\`.

---

## 5. Validation

| Check | Result |
|---|---|
| Exclusion validation | ${VALIDATION_RESULT} |
| docs (GA cert) | $([[ -f "${PKG_ROOT}/docs/releases/GA_CERTIFICATION_REPORT.md" ]] && echo PASS || echo FAIL) |
| source | $([[ ${SOURCE_BYTES} -gt 0 ]] && echo PASS || echo FAIL) |
| configs | $([[ -f "${PKG_ROOT}/configs/web/package.json" ]] && echo PASS || echo FAIL) |
| workflows | $([[ ${WF_COUNT} -gt 0 ]] && echo PASS || echo FAIL) |

---

## 6. Package Size

| Component | Size |
|---|---|
| Total | $(format_size "$TOTAL_BYTES") |
| source/ | $(format_size "$SOURCE_BYTES") |
| docs/ | $(format_size "$DOCS_BYTES") |
| configs/ | $(format_size "$CONFIG_BYTES") |

---

## 7. ZIP Archives

| Archive | Size |
|---|---|
${ZIP_SECTION}

---

## 8. Recommendations

1. Distribute ZIPs from \`archives/\` to auditors / AI review tools.
2. Do not soften **COMMERCIAL GA REJECTED**.
3. Re-run after VERSION or release-board changes.
4. Keep heavy \`source/\` copies and ZIPs gitignored; commit scripts + guides + this report.

---

## 9. Regeneration

\`\`\`bash
bash tools/audit-package/generate-audit-package.sh
\`\`\`

\`\`\`powershell
pwsh -File tools/audit-package/generate-audit-package.ps1
\`\`\`
EOF

cp -p "$REPORT_PATH" "${PKG_ROOT}/reports/AUDIT_PACKAGE_REPORT.md"

banner "Statistics"
echo "VERSION          : ${VERSION_TEXT}"
echo "Files            : ${FILE_COUNT}"
echo "Total size       : $(format_size "$TOTAL_BYTES")"
echo "Validation       : ${VALIDATION_RESULT}"
echo "Report           : ${REPORT_PATH}"
echo ""
echo "Done."

[[ "$VIOLATIONS" -eq 0 ]] || exit 2
exit 0
