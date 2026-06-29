# Source Language Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Auto/selected source language support and display detected source language in the HUD.

**Architecture:** Persist an optional source-language hint in `AppSettings`, append that hint to Gemini system instructions without adding unsupported provider config fields, track runtime detected source language from input transcript callbacks, and surface source-to-target labels in Settings, Menu Bar, and HUD.

**Tech Stack:** Swift, SwiftUI, Codable settings, Gemini Live setup JSON, Swift Testing, Python static verifiers, GitHub Actions xcodebuild.

---

## File Structure

Modify:

- `LiveBuddy/Models/AppSettings.swift` — add `sourceLanguageCode`, Codable support, restart comparison, display helper.
- `LiveBuddy/Services/GeminiLiveTranslateClient.swift` — append source-language hint to `systemInstruction` when selected.
- `LiveBuddy/Models/AppState.swift` — store `detectedSourceLanguageCode` and source/target display text.
- `LiveBuddy/Views/Settings/SettingsView.swift` — add `Translate from` picker.
- `LiveBuddy/Views/MenuBar/MenuBarView.swift` — add `Translate from` picker.
- `LiveBuddy/Views/Caption/CaptionView.swift` — show source-to-target label.
- `LiveBuddy/Models/InterfaceLanguage.swift` — localization keys and translations.
- `LiveBuddyTests/InterfaceLanguageTests.swift` — settings decode/restart tests.
- `scripts/verify_p0_onboarding.py` and `scripts/verify_interface_language.py` — static checks.
- `README.md` — document source language auto/manual behavior.

---

### Task 1: Settings model and source hint

1. Write failing tests in `InterfaceLanguageTests`:
   - legacy settings decode `sourceLanguageCode == nil`;
   - changing `sourceLanguageCode` requires session restart.
2. Verify RED with `swiftc -typecheck` referencing `AppSettings().sourceLanguageCode` before implementation.
3. Add `sourceLanguageCode` to `AppSettings`, Codable, and `requiresSessionRestart`.
4. Add `TranslationLanguage.name(for:)` reuse for hint construction.
5. Modify Gemini setup to prepend a source-language hint to `systemInstruction` only when `sourceLanguageCode` is non-nil.
6. Verify with a one-off `swiftc` check and commit `feat: add source language setting`.

### Task 2: Runtime detection and UI

1. Add localization keys: `translateFrom`, `autoDetectLanguage`, `detectedSourceLanguage`.
2. Add `detectedSourceLanguageCode` and display helpers to `AppState`.
3. Reset detection on start.
4. Update detection when `onInputTranscript` passes `languageCode`.
5. Add source picker to Settings and Menu Bar.
6. Replace HUD target-only label with source-to-target label.
7. Update verifier scripts and commit `feat: show source language selection`.

### Task 3: Documentation, verification, push, CI

1. Update README.
2. Run static verifiers, one-off Swift checks, full temporary Swift typecheck.
3. Commit docs.
4. Push to `target/main`.
5. Watch GitHub Actions `Swift` workflow.

## Self-Review

- Spec coverage: settings, provider hint, detection display, UI, localization, docs, verification covered.
- Placeholder scan: no TODO/TBD placeholders.
- Type consistency: `sourceLanguageCode`, `detectedSourceLanguageCode`, and display helpers consistently named.
