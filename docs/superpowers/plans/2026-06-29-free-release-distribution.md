# Free Release Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a zero-cost macOS release pipeline that produces ad-hoc signed DMG/ZIP artifacts, explains Gatekeeper first-open steps, and lets users manually check GitHub Releases from the app.

**Architecture:** Add a standalone packaging script and release workflow outside the app runtime, plus a small Settings button that opens the releases URL. Keep paid signing/notarization out of this path and make all checks explicit and reproducible.

**Tech Stack:** zsh/bash shell scripts, macOS `swiftc`/`xcodebuild`, `codesign`, `iconutil`, `hdiutil`, GitHub Actions, SwiftUI, existing Python verifier style.

---

## Task 1: Packaging script and install note

**Files:**
- Create: `scripts/package_release.sh`
- Create: `packaging/INSTALL.txt`
- Create: `scripts/verify_release_packaging.py`

- [ ] Write verifier expecting packaging script, install note, and key commands.
- [ ] Run verifier to see RED failure.
- [ ] Implement package script with Xcode build path and swiftc fallback.
- [ ] Implement install note explaining right-click Open.
- [ ] Run verifier and local package script.
- [ ] Commit `feat: add free mac release packaging`.

## Task 2: GitHub release workflow

**Files:**
- Create: `.github/workflows/release.yml`
- Modify: `scripts/verify_release_packaging.py`

- [ ] Extend verifier for workflow triggers and `gh release create`.
- [ ] Run verifier to see RED failure.
- [ ] Implement workflow with `workflow_dispatch`, `v*` tag trigger, artifact upload, and release creation on tag.
- [ ] Run verifier.
- [ ] Commit `ci: add free release workflow`.

## Task 3: App update-check button

**Files:**
- Modify: `LiveBuddy/Models/InterfaceLanguage.swift`
- Modify: `LiveBuddy/Views/Settings/SettingsView.swift`

- [ ] Add localization keys for Check for Updates and GitHub Releases.
- [ ] Add Settings button that opens `https://github.com/SuLea-IT/translate-macos/releases`.
- [ ] Run interface-language verifier and Swift typecheck.
- [ ] Commit `feat: add manual update check`.

## Task 4: README and final verification

**Files:**
- Modify: `README.md`

- [ ] Document GitHub Releases, DMG/ZIP, and first-open right-click flow.
- [ ] Run all verifiers and local package script.
- [ ] Commit `docs: document free release install`.
- [ ] Push to `target main` and wait for CI success.
