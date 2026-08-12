#!/usr/bin/env powershell
#Requires -Version 5.1
<#
.SYNOPSIS
  Generate the DSP AI Indicator Enterprise Audit Package (reproducible).

.DESCRIPTION
  One-command regenerate:
    1) Assemble DSP_AI_INDICATOR_AUDIT_PACKAGE/
    2) Copy docs, source, configs, workflows (with exclusions)
    3) Create ZIP archives
    4) Validate exclusions + sizes
    5) Print statistics and write AUDIT_PACKAGE_REPORT.md

.NOTES
  Version: 1.0.0
#>

[CmdletBinding()]
param(
    [switch]$SkipZip,
    [switch]$KeepExistingSource
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$PkgName = "DSP_AI_INDICATOR_AUDIT_PACKAGE"
$PkgRoot = Join-Path $ScriptDir $PkgName
$Templates = Join-Path $ScriptDir "templates"
$SizeLimitMB = 350
$GeneratedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$Tick = [string][char]96

$ExcludeDirNames = @(
    "node_modules", ".next", ".git", "coverage", "dist", "build", "out",
    ".cache", ".turbo", "playwright-report", "test-results", "logs", "tmp",
    "temp", ".idea", ".vscode", ".venv", "venv", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "htmlcov", ".tox", ".nox"
)
$ExcludeFilePatterns = @(
    "*.log", "*.cache", "*.tsbuildinfo", "*.pyc", "*.pyo", ".DS_Store",
    "Thumbs.db", "*.egg", ".coverage", "coverage.xml", "coverage.json"
)

function Write-Banner {
    param([string]$Message)
    Write-Host ""
    Write-Host ("=== {0} ===" -f $Message) -ForegroundColor Cyan
}

function Test-ExcludedPath {
    param([string]$FullPath)
    $parts = $FullPath -split '[\\/]'
    foreach ($p in $parts) {
        if ($ExcludeDirNames -contains $p) { return $true }
        if ($p -like "*.egg-info") { return $true }
    }
    $name = Split-Path $FullPath -Leaf
    foreach ($pat in $ExcludeFilePatterns) {
        if ($name -like $pat) { return $true }
    }
    return $false
}

function Copy-TreeFiltered {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Destination
    )
    if (-not (Test-Path -LiteralPath $Source)) {
        Write-Host ("  skip (missing): {0}" -f $Source) -ForegroundColor DarkYellow
        return 0
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $count = 0
    $files = Get-ChildItem -LiteralPath $Source -Recurse -File -Force -ErrorAction SilentlyContinue
    foreach ($f in $files) {
        if (Test-ExcludedPath $f.FullName) { continue }
        $rel = $f.FullName.Substring($Source.Length).TrimStart([char[]]@([char]92, [char]47))
        $destFile = Join-Path $Destination $rel
        $destDir = Split-Path $destFile -Parent
        if (-not (Test-Path -LiteralPath $destDir)) {
            New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        }
        Copy-Item -LiteralPath $f.FullName -Destination $destFile -Force
        $count++
    }
    return $count
}

function Copy-FileSafe {
    param([string]$Src, [string]$DestDir, [string]$DestName = $null)
    if (-not (Test-Path -LiteralPath $Src)) { return $false }
    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
    $name = if ($DestName) { $DestName } else { Split-Path $Src -Leaf }
    Copy-Item -LiteralPath $Src -Destination (Join-Path $DestDir $name) -Force
    return $true
}

function Get-DirSizeBytes {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return [int64]0 }
    $sum = (Get-ChildItem -LiteralPath $Path -Recurse -File -Force -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
    if ($null -eq $sum) { return [int64]0 }
    return [int64]$sum
}

function Format-Size {
    param([int64]$Bytes)
    if ($Bytes -ge 1GB) { return ("{0:N2} GB" -f ($Bytes / 1GB)) }
    if ($Bytes -ge 1MB) { return ("{0:N2} MB" -f ($Bytes / 1MB)) }
    if ($Bytes -ge 1KB) { return ("{0:N2} KB" -f ($Bytes / 1KB)) }
    return ("{0} B" -f $Bytes)
}

function New-ZipFromFolder {
    param([string]$Folder, [string]$ZipPath)
    if (Test-Path -LiteralPath $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
    if (-not (Test-Path -LiteralPath $Folder)) { return $false }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        $Folder,
        $ZipPath,
        [System.IO.Compression.CompressionLevel]::Optimal,
        $false
    )
    return $true
}

function Add-Line {
    param($List, [string]$Text)
    [void]$List.Add($Text)
}

Write-Banner "DSP Enterprise Audit Package Generator v1.0.0"
Write-Host ("RepoRoot : {0}" -f $RepoRoot)
Write-Host ("Package  : {0}" -f $PkgRoot)

Write-Banner "Preparing package directories"
$dirs = @(
    $PkgRoot,
    (Join-Path $PkgRoot "docs\root"),
    (Join-Path $PkgRoot "docs\project"),
    (Join-Path $PkgRoot "docs\design"),
    (Join-Path $PkgRoot "docs\governance"),
    (Join-Path $PkgRoot "docs\research"),
    (Join-Path $PkgRoot "docs\releases"),
    (Join-Path $PkgRoot "docs\reviews"),
    (Join-Path $PkgRoot "source\web"),
    (Join-Path $PkgRoot "source\packages"),
    (Join-Path $PkgRoot "configs\root"),
    (Join-Path $PkgRoot "configs\web"),
    (Join-Path $PkgRoot "workflows"),
    (Join-Path $PkgRoot "manifests"),
    (Join-Path $PkgRoot "archives"),
    (Join-Path $PkgRoot "reports")
)
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

if (-not $KeepExistingSource) {
    foreach ($wipe in @(
            (Join-Path $PkgRoot "source\web"),
            (Join-Path $PkgRoot "source\packages"),
            (Join-Path $PkgRoot "configs\root"),
            (Join-Path $PkgRoot "configs\web"),
            (Join-Path $PkgRoot "workflows"),
            (Join-Path $PkgRoot "docs\design"),
            (Join-Path $PkgRoot "docs\governance"),
            (Join-Path $PkgRoot "docs\research"),
            (Join-Path $PkgRoot "docs\releases"),
            (Join-Path $PkgRoot "docs\reviews"),
            (Join-Path $PkgRoot "docs\project"),
            (Join-Path $PkgRoot "docs\root")
        )) {
        if (Test-Path -LiteralPath $wipe) {
            Remove-Item -LiteralPath $wipe -Recurse -Force
            New-Item -ItemType Directory -Force -Path $wipe | Out-Null
        }
    }
}

Write-Banner "Installing narrative guides"
$guideNames = @(
    "00_START_HERE.md", "01_PROJECT_OVERVIEW.md", "02_ARCHITECTURE.md",
    "03_MODULE_INDEX.md", "04_FEATURE_MATRIX.md", "05_RELEASE_STATUS.md",
    "06_KNOWN_LIMITATIONS.md", "07_REPOSITORY_MAP.md", "08_DEPENDENCY_REPORT.md",
    "09_AUDIT_GUIDE.md", "AUDIT_MANIFEST.md"
)
foreach ($g in $guideNames) {
    $src = Join-Path $Templates $g
    if (-not (Test-Path -LiteralPath $src)) { throw ("Missing template: {0}" -f $src) }
    Copy-Item -LiteralPath $src -Destination (Join-Path $PkgRoot $g) -Force
}

Write-Banner "Copying root documentation"
[void](Copy-FileSafe (Join-Path $RepoRoot "README.md") (Join-Path $PkgRoot "docs\root"))
[void](Copy-FileSafe (Join-Path $RepoRoot "CONTRIBUTING.md") (Join-Path $PkgRoot "docs\root"))
[void](Copy-FileSafe (Join-Path $RepoRoot "LICENSE") (Join-Path $PkgRoot "docs\root"))
[void](Copy-FileSafe (Join-Path $RepoRoot "CHANGELOG.md") (Join-Path $PkgRoot "docs\root"))
[void](Copy-FileSafe (Join-Path $RepoRoot "docs\CHANGELOG.md") (Join-Path $PkgRoot "docs\root") "CHANGELOG_docs.md")

Write-Banner "Copying governance-critical project docs"
$projectDocNames = @(
    "ARCHITECTURE_BIBLE.md", "ARCHITECTURE_GOVERNANCE.md", "ARCHITECTURE_CHECKLIST.md",
    "CORE_VALUES.md", "CV_001_DATA_AUTHENTICITY_FIRST.md", "CV_002_TO_010_TIER0_CORE_VALUES.md",
    "RESEARCH_STANDARDS.md", "RS_001_TO_RS_010.md", "USER_TRUST_STANDARD.md",
    "PRODUCT_CONSTITUTION.md", "IMPLEMENTATION_QUALITY_GATE.md", "CODE_REVIEW_CHECKLIST.md",
    "KNOWN_LIMITATIONS.md", "RESEARCH_ARCHITECTURE.md", "REPORT_ARCHITECTURE.md",
    "SECURITY_GUIDE.md", "CONFIGURATION_GUIDE.md", "RELEASE_ENGINEERING.md",
    "RELEASE_NOTES_v1.0.0.md", "PRODUCT_VISION.md", "PROJECT_CHARTER.md"
)
$projCopied = 0
foreach ($n in $projectDocNames) {
    if (Copy-FileSafe (Join-Path $RepoRoot ("docs\{0}" -f $n)) (Join-Path $PkgRoot "docs\project")) {
        $projCopied++
    }
}
Write-Host ("  project docs copied: {0}" -f $projCopied)

Write-Banner "Copying docs/design,governance,research,releases,reviews"
$docTreeCounts = @{}
foreach ($sub in @("design", "governance", "research", "releases", "reviews")) {
    $c = Copy-TreeFiltered -Source (Join-Path $RepoRoot ("docs\{0}" -f $sub)) -Destination (Join-Path $PkgRoot ("docs\{0}" -f $sub))
    $docTreeCounts[$sub] = $c
    Write-Host ("  docs/{0} : {1} files" -f $sub, $c)
}

Write-Banner "Copying web source"
$webCount = Copy-TreeFiltered -Source (Join-Path $RepoRoot "apps\web\src") -Destination (Join-Path $PkgRoot "source\web\src")
Write-Host ("  apps/web/src : {0} files" -f $webCount)
$pubCount = Copy-TreeFiltered -Source (Join-Path $RepoRoot "apps\web\public") -Destination (Join-Path $PkgRoot "source\web\public")
Write-Host ("  apps/web/public : {0} files" -f $pubCount)
[void](Copy-FileSafe (Join-Path $RepoRoot "apps\web\README.md") (Join-Path $PkgRoot "source\web"))
[void](Copy-FileSafe (Join-Path $RepoRoot "apps\web\VERSION_MANIFEST.json") (Join-Path $PkgRoot "source\web"))

Write-Banner "Copying packages source"
$packagesRoot = Join-Path $RepoRoot "packages"
$pkgFileCount = 0
$pkgNames = New-Object System.Collections.Generic.List[string]
if (Test-Path -LiteralPath $packagesRoot) {
    Get-ChildItem -LiteralPath $packagesRoot -Directory | ForEach-Object {
        $name = $_.Name
        [void]$pkgNames.Add($name)
        $destPkg = Join-Path $PkgRoot ("source\packages\{0}" -f $name)
        New-Item -ItemType Directory -Force -Path $destPkg | Out-Null
        foreach ($sub in @("src", "tests", "test")) {
            $subPath = Join-Path $_.FullName $sub
            if (Test-Path -LiteralPath $subPath) {
                $pkgFileCount += Copy-TreeFiltered -Source $subPath -Destination (Join-Path $destPkg $sub)
            }
        }
        foreach ($f in @("pyproject.toml", "README.md", "setup.py", "setup.cfg")) {
            if (Copy-FileSafe (Join-Path $_.FullName $f) $destPkg) { $pkgFileCount++ }
        }
    }
}
Write-Host ("  packages mirrored: {0} packages / {1} files" -f $pkgNames.Count, $pkgFileCount)

Write-Banner "Copying configs"
$rootConfigs = @(
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "tsconfig.json", "tsconfig.base.json", "pyproject.toml",
    "VERSION", "PRODUCTION_VERSION_MANIFEST.json", "Makefile",
    "docker-compose.yml", ".env.example", ".env.production.example"
)
foreach ($rc in $rootConfigs) {
    [void](Copy-FileSafe (Join-Path $RepoRoot $rc) (Join-Path $PkgRoot "configs\root"))
}
Get-ChildItem -LiteralPath $RepoRoot -File -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -match '^(tsconfig.*\.json|eslint.*|prettier.*|vitest.*|playwright.*|tailwind.*|postcss.*|next\.config\..*)$'
    } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $PkgRoot ("configs\root\{0}" -f $_.Name)) -Force
    }

$webConfigDir = Join-Path $RepoRoot "apps\web"
$webConfigNames = @(
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "tsconfig.json", "next.config.ts", "next.config.js", "next.config.mjs",
    "eslint.config.mjs", "eslint.config.js", ".eslintrc.json", ".eslintrc.js",
    ".prettierrc", ".prettierrc.json", ".prettierignore",
    "vitest.config.ts", "vitest.config.js", "vitest.setup.ts",
    "playwright.config.ts", "playwright.config.js",
    "tailwind.config.ts", "tailwind.config.js", "postcss.config.mjs", "postcss.config.js",
    "components.json", "lighthouserc.cjs", "next-env.d.ts", ".env.example"
)
foreach ($wc in $webConfigNames) {
    [void](Copy-FileSafe (Join-Path $webConfigDir $wc) (Join-Path $PkgRoot "configs\web"))
}

Write-Banner "Copying GitHub workflows"
$wfCount = Copy-TreeFiltered -Source (Join-Path $RepoRoot ".github\workflows") -Destination (Join-Path $PkgRoot "workflows")
Write-Host ("  workflows: {0} files" -f $wfCount)

Write-Banner "Writing manifests"
$versionSrc = Join-Path $RepoRoot "VERSION"
$versionText = if (Test-Path $versionSrc) { (Get-Content -LiteralPath $versionSrc -Raw).Trim() } else { "UNKNOWN" }
Set-Content -LiteralPath (Join-Path $PkgRoot "manifests\VERSION") -Value $versionText -Encoding UTF8

try {
    $gitSha = (git -C $RepoRoot rev-parse HEAD 2>$null)
    $gitBranch = (git -C $RepoRoot branch --show-current 2>$null)
    $gitShort = (git -C $RepoRoot rev-parse --short HEAD 2>$null)
} catch {
    $gitSha = "unavailable"
    $gitBranch = "unavailable"
    $gitShort = "unavailable"
}
if (-not $gitSha) { $gitSha = "unavailable" }
if (-not $gitBranch) { $gitBranch = "unavailable" }
if (-not $gitShort) { $gitShort = "unavailable" }

$inv = New-Object System.Collections.Generic.List[string]
Add-Line $inv "# Package Inventory"
Add-Line $inv ""
Add-Line $inv "| Field | Value |"
Add-Line $inv "|---|---|"
Add-Line $inv ("| Generated (UTC) | {0} |" -f $GeneratedAt)
Add-Line $inv ("| Product VERSION | {0} |" -f $versionText)
Add-Line $inv ("| Git branch | {0} |" -f $gitBranch)
Add-Line $inv ("| Git SHA | {0} |" -f $gitSha)
Add-Line $inv ("| Git short | {0} |" -f $gitShort)
Add-Line $inv ("| Web source files | {0} |" -f $webCount)
Add-Line $inv ("| Packages mirrored | {0} |" -f $pkgNames.Count)
Add-Line $inv ("| Package source files | {0} |" -f $pkgFileCount)
Add-Line $inv ("| Workflows | {0} |" -f $wfCount)
Add-Line $inv ""
Add-Line $inv "## Packages"
Add-Line $inv ""
foreach ($pn in $pkgNames) {
    Add-Line $inv ("- {0}{1}{0}" -f $Tick, $pn)
}
Set-Content -LiteralPath (Join-Path $PkgRoot "manifests\PACKAGE_INVENTORY.md") -Value ($inv -join [Environment]::NewLine) -Encoding UTF8

$dep = New-Object System.Collections.Generic.List[string]
Add-Line $dep "# Dependency Summary"
Add-Line $dep ""
Add-Line $dep ("Generated: {0}" -f $GeneratedAt)
Add-Line $dep ""
$webPkgJson = Join-Path $PkgRoot "configs\web\package.json"
if (Test-Path $webPkgJson) {
    try {
        $pj = Get-Content -LiteralPath $webPkgJson -Raw | ConvertFrom-Json
        Add-Line $dep "## Web package"
        Add-Line $dep ""
        Add-Line $dep ("- name: {0}{1}{0}" -f $Tick, $pj.name)
        Add-Line $dep ("- version: {0}{1}{0}" -f $Tick, $pj.version)
        Add-Line $dep ("- dependencies: {0}" -f $pj.dependencies.PSObject.Properties.Count)
        Add-Line $dep ("- devDependencies: {0}" -f $pj.devDependencies.PSObject.Properties.Count)
        Add-Line $dep ""
        Add-Line $dep "### Runtime dependencies"
        $pj.dependencies.PSObject.Properties | Sort-Object Name | ForEach-Object {
            Add-Line $dep ("- {0}{1}{0}: {2}" -f $Tick, $_.Name, $_.Value)
        }
    } catch {
        Add-Line $dep "_Failed to parse web package.json_"
    }
}
Add-Line $dep ""
Add-Line $dep "## Python"
Add-Line $dep ""
Add-Line $dep ("- Root: {0}configs/root/pyproject.toml{0}" -f $Tick)
Add-Line $dep ("- Per-package: {0}source/packages/*/pyproject.toml{0} ({1} packages)" -f $Tick, $pkgNames.Count)
Set-Content -LiteralPath (Join-Path $PkgRoot "manifests\DEPENDENCY_SUMMARY.md") -Value ($dep -join [Environment]::NewLine) -Encoding UTF8

$tree = New-Object System.Collections.Generic.List[string]
Add-Line $tree "# Source Tree (top-level)"
Add-Line $tree ""
Add-Line $tree "## source/web"
Get-ChildItem (Join-Path $PkgRoot "source\web") -ErrorAction SilentlyContinue | ForEach-Object {
    Add-Line $tree ("- {0}" -f $_.Name)
}
Add-Line $tree ""
Add-Line $tree "## source/packages"
$pkgNames | Sort-Object | ForEach-Object { Add-Line $tree ("- {0}" -f $_) }
Set-Content -LiteralPath (Join-Path $PkgRoot "manifests\SOURCE_TREE.txt") -Value ($tree -join [Environment]::NewLine) -Encoding UTF8

$meta = New-Object System.Collections.Generic.List[string]
Add-Line $meta "# Generation Metadata"
Add-Line $meta ""
Add-Line $meta "- generator: tools/audit-package/generate-audit-package.ps1"
Add-Line $meta "- generator_version: 1.0.0"
Add-Line $meta ("- generated_utc: {0}" -f $GeneratedAt)
Add-Line $meta ("- repo_root: {0}" -f $RepoRoot)
Add-Line $meta ("- product_version: {0}" -f $versionText)
Add-Line $meta ("- git_branch: {0}" -f $gitBranch)
Add-Line $meta ("- git_sha: {0}" -f $gitSha)
Add-Line $meta "- commercial_ga: REJECTED"
Add-Line $meta "- pilot_posture: GO (closed-beta / institutional pilot)"
Set-Content -LiteralPath (Join-Path $PkgRoot "manifests\GENERATION_META.md") -Value ($meta -join [Environment]::NewLine) -Encoding UTF8

Write-Banner "Validating exclusions"
$violations = New-Object System.Collections.Generic.List[string]
$allFiles = @(Get-ChildItem -LiteralPath $PkgRoot -Recurse -File -Force -ErrorAction SilentlyContinue)
foreach ($f in $allFiles) {
    $rel = $f.FullName.Substring($PkgRoot.Length)
    if ($rel -match '\\node_modules\\|\\\.next\\|\\\.git\\|\\coverage\\|\\playwright-report\\|\\test-results\\') {
        [void]$violations.Add($rel)
    }
    if (($f.Extension -eq ".log" -or $f.Extension -eq ".tsbuildinfo") -and ($rel -notmatch '\\reports\\')) {
        [void]$violations.Add($rel)
    }
}
$validationPass = ($violations.Count -eq 0)
if ($validationPass) {
    Write-Host "  Exclusion validation: PASS" -ForegroundColor Green
} else {
    Write-Host ("  Exclusion validation: FAIL ({0} paths)" -f $violations.Count) -ForegroundColor Red
    $violations | Select-Object -First 20 | ForEach-Object { Write-Host ("    {0}" -f $_) }
}

$presenceGuides = Test-Path (Join-Path $PkgRoot "00_START_HERE.md")
$presenceDocs = Test-Path (Join-Path $PkgRoot "docs\releases\GA_CERTIFICATION_REPORT.md")
$presenceSource = ((Get-DirSizeBytes (Join-Path $PkgRoot "source")) -gt 0)
$presenceConfigs = Test-Path (Join-Path $PkgRoot "configs\web\package.json")
$presenceWorkflows = ((Get-ChildItem (Join-Path $PkgRoot "workflows") -File -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0)
Write-Host ("  presence/guides: {0}" -f ($(if ($presenceGuides) { "OK" } else { "MISSING" })))
Write-Host ("  presence/docs: {0}" -f ($(if ($presenceDocs) { "OK" } else { "MISSING" })))
Write-Host ("  presence/source: {0}" -f ($(if ($presenceSource) { "OK" } else { "MISSING" })))
Write-Host ("  presence/configs: {0}" -f ($(if ($presenceConfigs) { "OK" } else { "MISSING" })))
Write-Host ("  presence/workflows: {0}" -f ($(if ($presenceWorkflows) { "OK" } else { "MISSING" })))

Write-Banner "Computing sizes"
$totalBytes = Get-DirSizeBytes $PkgRoot
$sourceBytes = Get-DirSizeBytes (Join-Path $PkgRoot "source")
$docsBytes = Get-DirSizeBytes (Join-Path $PkgRoot "docs")
$configBytes = Get-DirSizeBytes (Join-Path $PkgRoot "configs")
$wfBytes = Get-DirSizeBytes (Join-Path $PkgRoot "workflows")
$fileCount = $allFiles.Count
Write-Host ("  Total  : {0} ({1} files)" -f (Format-Size $totalBytes), $fileCount)
Write-Host ("  Source : {0}" -f (Format-Size $sourceBytes))
Write-Host ("  Docs   : {0}" -f (Format-Size $docsBytes))
Write-Host ("  Configs: {0}" -f (Format-Size $configBytes))
Write-Host ("  WF     : {0}" -f (Format-Size $wfBytes))

$zipList = New-Object System.Collections.Generic.List[object]
if (-not $SkipZip) {
    Write-Banner "Creating ZIP archives"
    $archDir = Join-Path $PkgRoot "archives"
    Get-ChildItem -LiteralPath $archDir -Filter "*.zip" -ErrorAction SilentlyContinue | Remove-Item -Force

    $totalMB = [math]::Round($totalBytes / 1MB, 2)
    $zipJobs = [ordered]@{
        "audit-docs.zip"      = (Join-Path $PkgRoot "docs")
        "audit-source.zip"    = (Join-Path $PkgRoot "source")
        "audit-config.zip"    = (Join-Path $PkgRoot "configs")
        "audit-workflows.zip" = (Join-Path $PkgRoot "workflows")
    }

    $guideStage = Join-Path $env:TEMP ("dsp-audit-guides-{0}" -f $PID)
    if (Test-Path $guideStage) { Remove-Item $guideStage -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $guideStage | Out-Null
    foreach ($g in $guideNames) {
        Copy-Item (Join-Path $PkgRoot $g) (Join-Path $guideStage $g) -Force
    }
    $zipJobs["audit-guides.zip"] = $guideStage

    if ($totalMB -gt $SizeLimitMB) {
        Write-Host ("  Package > {0}MB - creating split archives (plus tests)" -f $SizeLimitMB)
        $testStage = Join-Path $env:TEMP ("dsp-audit-tests-{0}" -f $PID)
        if (Test-Path $testStage) { Remove-Item $testStage -Recurse -Force }
        New-Item -ItemType Directory -Force -Path $testStage | Out-Null
        $srcRoot = Join-Path $PkgRoot "source"
        Get-ChildItem $srcRoot -Recurse -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -in @("tests", "test", "e2e") } |
            ForEach-Object {
                $rel = $_.FullName.Substring($srcRoot.Length).TrimStart([char[]]@([char]92, [char]47))
                [void](Copy-TreeFiltered -Source $_.FullName -Destination (Join-Path $testStage $rel))
            }
        $zipJobs["audit-tests.zip"] = $testStage
    }

    foreach ($key in @($zipJobs.Keys)) {
        $folder = $zipJobs[$key]
        $zp = Join-Path $archDir $key
        if (New-ZipFromFolder -Folder $folder -ZipPath $zp) {
            $len = (Get-Item $zp).Length
            [void]$zipList.Add([pscustomobject]@{ Name = $key; Bytes = $len })
            Write-Host ("  wrote {0} ({1})" -f $key, (Format-Size $len))
        }
    }

    if ($totalMB -le $SizeLimitMB) {
        $fullZip = Join-Path $archDir "DSP_AI_INDICATOR_AUDIT_PACKAGE_FULL.zip"
        $fullStage = Join-Path $env:TEMP ("dsp-audit-full-{0}" -f $PID)
        if (Test-Path $fullStage) { Remove-Item $fullStage -Recurse -Force }
        New-Item -ItemType Directory -Force -Path $fullStage | Out-Null
        Get-ChildItem -LiteralPath $PkgRoot -Force | Where-Object { $_.Name -ne "archives" } | ForEach-Object {
            $dest = Join-Path $fullStage $_.Name
            if ($_.PSIsContainer) {
                Copy-Item -LiteralPath $_.FullName -Destination $dest -Recurse -Force
            } else {
                Copy-Item -LiteralPath $_.FullName -Destination $dest -Force
            }
        }
        if (New-ZipFromFolder -Folder $fullStage -ZipPath $fullZip) {
            $len = (Get-Item $fullZip).Length
            [void]$zipList.Add([pscustomobject]@{ Name = "DSP_AI_INDICATOR_AUDIT_PACKAGE_FULL.zip"; Bytes = $len })
            Write-Host ("  wrote DSP_AI_INDICATOR_AUDIT_PACKAGE_FULL.zip ({0})" -f (Format-Size $len))
        }
        if (Test-Path $fullStage) { Remove-Item $fullStage -Recurse -Force }
    }

    if (Test-Path $guideStage) { Remove-Item $guideStage -Recurse -Force }
    $testStagePath = Join-Path $env:TEMP ("dsp-audit-tests-{0}" -f $PID)
    if (Test-Path $testStagePath) { Remove-Item $testStagePath -Recurse -Force }
}

Write-Banner "Writing AUDIT_PACKAGE_REPORT"
$validationText = if ($validationPass) { "PASS" } else { ("FAIL ({0} paths)" -f $violations.Count) }
$fence = $Tick + $Tick + $Tick
$rpt = New-Object System.Collections.Generic.List[string]

Add-Line $rpt "# AUDIT_PACKAGE_REPORT"
Add-Line $rpt ""
Add-Line $rpt "| Field | Value |"
Add-Line $rpt "|---|---|"
Add-Line $rpt ("| Generator | {0}tools/audit-package/generate-audit-package.ps1{0} v1.0.0 |" -f $Tick)
Add-Line $rpt ("| Generated (UTC) | {0} |" -f $GeneratedAt)
Add-Line $rpt ("| Product VERSION | **{0}** |" -f $versionText)
Add-Line $rpt ("| Git | {0}{1}{0} @ {0}{2}{0} ({0}{3}{0}) |" -f $Tick, $gitBranch, $gitShort, $gitSha)
Add-Line $rpt ("| Package path | {0}tools/audit-package/{1}/{0} |" -f $Tick, $PkgName)
Add-Line $rpt "| Pilot posture | **GO** (closed-beta / institutional pilot) |"
Add-Line $rpt "| Commercial GA | **REJECTED** |"
Add-Line $rpt ""
Add-Line $rpt "---"
Add-Line $rpt ""
Add-Line $rpt "## 1. Executive Summary"
Add-Line $rpt ""
Add-Line $rpt ("This report documents a reproducible **Enterprise Audit Package** for DSP AI Indicator Version **{0}**. The package assembles narrative audit guides, authoritative documentation (including GA certification), thin-client web source, backend/research packages, build configs, and CI workflows with generated artefacts excluded." -f $versionText)
Add-Line $rpt ""
Add-Line $rpt ("**Release honesty (authoritative):** Closed-beta / institutional pilot is **GO** (PASS WITH CONDITIONS). Unrestricted **Commercial GA is REJECTED** per {0}docs/releases/GA_CERTIFICATION_REPORT.md{0} and {0}RELEASE_BOARD.md{0}. Limitations are not hidden." -f $Tick)
Add-Line $rpt ""
Add-Line $rpt ("**Architecture:** Thin client - browser presentation only; analytics / valuation / recommendation / AI reasoning owned by backend {0}/api/v1{0} and {0}packages/*{0}." -f $Tick)
Add-Line $rpt ""
Add-Line $rpt "---"
Add-Line $rpt ""
Add-Line $rpt "## 2. Files Included (summary)"
Add-Line $rpt ""
Add-Line $rpt "| Area | Count / notes |"
Add-Line $rpt "|---|---|"
Add-Line $rpt ("| Narrative guides | {0} |" -f $guideNames.Count)
Add-Line $rpt ("| docs/project (key) | {0} files |" -f $projCopied)
Add-Line $rpt ("| docs/design | {0} files |" -f $docTreeCounts["design"])
Add-Line $rpt ("| docs/governance | {0} files |" -f $docTreeCounts["governance"])
Add-Line $rpt ("| docs/research | {0} files |" -f $docTreeCounts["research"])
Add-Line $rpt ("| docs/releases | {0} files |" -f $docTreeCounts["releases"])
Add-Line $rpt ("| docs/reviews | {0} files |" -f $docTreeCounts["reviews"])
Add-Line $rpt ("| source/web | {0} files (+ public {1}) |" -f $webCount, $pubCount)
Add-Line $rpt ("| source/packages | {0} packages / {1} files |" -f $pkgNames.Count, $pkgFileCount)
Add-Line $rpt ("| workflows | {0} files |" -f $wfCount)
Add-Line $rpt ("| Total package files | {0} |" -f $fileCount)
Add-Line $rpt ""
Add-Line $rpt "Root docs copied when present: README, CONTRIBUTING, LICENSE, CHANGELOG."
Add-Line $rpt ""
Add-Line $rpt "---"
Add-Line $rpt ""
Add-Line $rpt "## 3. Files Excluded"
Add-Line $rpt ""
Add-Line $rpt "Mandatory exclusions enforced by generator filters:"
Add-Line $rpt ""
Add-Line $rpt ("{0}node_modules{0}, {0}.next{0}, {0}.git{0}, {0}coverage{0}, {0}dist{0}, {0}build{0}, {0}out{0}, {0}.cache{0}, {0}.turbo{0}, {0}playwright-report{0}, {0}test-results{0}, {0}logs{0}, {0}tmp{0}, IDE folders, virtualenvs, {0}__pycache__{0}, {0}*.egg-info{0}, {0}*.log{0}, {0}*.tsbuildinfo{0}, {0}*.pyc{0}, and similar generated artefacts." -f $Tick)
Add-Line $rpt ""
Add-Line $rpt ("Secrets ({0}.env{0} family) are not copied; only {0}.env.example{0} / {0}.env.production.example{0} when present." -f $Tick)
Add-Line $rpt ""
Add-Line $rpt "---"
Add-Line $rpt ""
Add-Line $rpt "## 4. Generated Documents"
Add-Line $rpt ""
Add-Line $rpt "| Document | Role |"
Add-Line $rpt "|---|---|"
$docRoles = @(
    @{ N = "00_START_HERE.md"; R = "Orientation" },
    @{ N = "01_PROJECT_OVERVIEW.md"; R = "Product overview" },
    @{ N = "02_ARCHITECTURE.md"; R = "Thin client / backend ownership" },
    @{ N = "03_MODULE_INDEX.md"; R = "Module index" },
    @{ N = "04_FEATURE_MATRIX.md"; R = "Pilot feature scope" },
    @{ N = "05_RELEASE_STATUS.md"; R = "Pilot GO / Commercial GA REJECTED" },
    @{ N = "06_KNOWN_LIMITATIONS.md"; R = "Honest limitations" },
    @{ N = "07_REPOSITORY_MAP.md"; R = "Repo to package map" },
    @{ N = "08_DEPENDENCY_REPORT.md"; R = "Dependency guidance" },
    @{ N = "09_AUDIT_GUIDE.md"; R = "Audit procedure" },
    @{ N = "AUDIT_MANIFEST.md"; R = "Inventory / regen policy" },
    @{ N = "manifests/*"; R = "VERSION, inventory, dependency summary, meta" }
)
foreach ($dr in $docRoles) {
    Add-Line $rpt ("| {0}{1}{0} | {2} |" -f $Tick, $dr.N, $dr.R)
}
Add-Line $rpt ""
Add-Line $rpt "---"
Add-Line $rpt ""
Add-Line $rpt "## 5. Validation"
Add-Line $rpt ""
Add-Line $rpt "| Check | Result |"
Add-Line $rpt "|---|---|"
Add-Line $rpt ("| Exclusion validation | {0} |" -f $validationText)
Add-Line $rpt ("| guides | {0} |" -f ($(if ($presenceGuides) { "PASS" } else { "FAIL" })))
Add-Line $rpt ("| docs | {0} |" -f ($(if ($presenceDocs) { "PASS" } else { "FAIL" })))
Add-Line $rpt ("| source | {0} |" -f ($(if ($presenceSource) { "PASS" } else { "FAIL" })))
Add-Line $rpt ("| configs | {0} |" -f ($(if ($presenceConfigs) { "PASS" } else { "FAIL" })))
Add-Line $rpt ("| workflows | {0} |" -f ($(if ($presenceWorkflows) { "PASS" } else { "FAIL" })))
Add-Line $rpt ""
Add-Line $rpt "---"
Add-Line $rpt ""
Add-Line $rpt "## 6. Package Size"
Add-Line $rpt ""
Add-Line $rpt "| Component | Size |"
Add-Line $rpt "|---|---|"
Add-Line $rpt ("| Total | {0} |" -f (Format-Size $totalBytes))
Add-Line $rpt ("| source/ | {0} |" -f (Format-Size $sourceBytes))
Add-Line $rpt ("| docs/ | {0} |" -f (Format-Size $docsBytes))
Add-Line $rpt ("| configs/ | {0} |" -f (Format-Size $configBytes))
Add-Line $rpt ("| workflows/ | {0} |" -f (Format-Size $wfBytes))
Add-Line $rpt ("| Split threshold | {0} MB |" -f $SizeLimitMB)
Add-Line $rpt ""
Add-Line $rpt "---"
Add-Line $rpt ""
Add-Line $rpt "## 7. ZIP Archives"
Add-Line $rpt ""
Add-Line $rpt "| Archive | Size |"
Add-Line $rpt "|---|---|"
if ($zipList.Count -gt 0) {
    foreach ($z in $zipList) {
        Add-Line $rpt ("| {0}{1}{0} | {2} |" -f $Tick, $z.Name, (Format-Size $z.Bytes))
    }
} else {
    Add-Line $rpt "| _(skipped)_ | - |"
}
Add-Line $rpt ""
Add-Line $rpt ("Archives are written under {0}{1}/archives/{0} and are gitignored by default (regenerate for upload)." -f $Tick, $PkgName)
Add-Line $rpt ""
Add-Line $rpt "---"
Add-Line $rpt ""
Add-Line $rpt "## 8. Recommendations"
Add-Line $rpt ""
Add-Line $rpt ("1. Distribute ZIPs from {0}archives/{0} to external auditors / AI review tools." -f $Tick)
Add-Line $rpt "2. Cite GA Certification Report when discussing Commercial GA - do not soften **REJECTED**."
Add-Line $rpt "3. Re-run this generator after any release-board or VERSION change."
Add-Line $rpt ("4. Keep {0}source/{0} and ZIPs out of git if they bloat the monorepo; commit scripts + guides + this report." -f $Tick)
Add-Line $rpt "5. For Commercial GA re-evaluation, require GA-C1...GA-C7 evidence - not package regeneration alone."
Add-Line $rpt ""
Add-Line $rpt "---"
Add-Line $rpt ""
Add-Line $rpt "## 9. Regeneration"
Add-Line $rpt ""
Add-Line $rpt ($fence + "powershell")
Add-Line $rpt "powershell -NoProfile -ExecutionPolicy Bypass -File tools/audit-package/generate-audit-package.ps1"
Add-Line $rpt $fence
Add-Line $rpt ""
Add-Line $rpt ($fence + "bash")
Add-Line $rpt "bash tools/audit-package/generate-audit-package.sh"
Add-Line $rpt $fence

$reportPath = Join-Path $ScriptDir "AUDIT_PACKAGE_REPORT.md"
Set-Content -LiteralPath $reportPath -Value ($rpt -join [Environment]::NewLine) -Encoding UTF8
Copy-Item -LiteralPath $reportPath -Destination (Join-Path $PkgRoot "reports\AUDIT_PACKAGE_REPORT.md") -Force

# Refresh allFiles count after zips (optional stats already captured pre-zip for total without double-count chaos)
Write-Banner "Statistics"
Write-Host ("VERSION          : {0}" -f $versionText)
Write-Host ("Files (pre-zip)  : {0}" -f $fileCount)
Write-Host ("Total size       : {0}" -f (Format-Size $totalBytes))
Write-Host ("ZIP archives     : {0}" -f $zipList.Count)
Write-Host ("Validation       : {0}" -f ($(if ($validationPass) { "PASS" } else { "FAIL" })))
Write-Host ("Report           : {0}" -f $reportPath)
Write-Host ""
Write-Host "Done." -ForegroundColor Green

if (-not $validationPass) { exit 2 }
exit 0
