# Terminology Glossary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight terminology glossary that guides Gemini to preserve or prefer user-defined terms.

**Architecture:** Store glossary entries in `AppSettings`, keep glossary logic in a pure `Glossary.swift` model/helper file, build a concise prompt block with `GlossaryPromptBuilder`, inject it into Gemini setup instructions, and expose add/delete controls in Settings.

**Tech Stack:** Swift, SwiftUI, Codable settings, Gemini systemInstruction, Swift Testing, Python static verifiers, GitHub Actions xcodebuild.

---

## Tasks

### Task 1: Glossary model and prompt builder

Files:
- Create `LiveBuddy/Models/Glossary.swift`
- Modify `LiveBuddy/Models/AppSettings.swift`
- Modify `LiveBuddy/Services/GeminiLiveTranslateClient.swift`
- Create `LiveBuddyTests/GlossaryTests.swift`

Steps:
1. Write failing tests for default empty glossary, restart on glossary change, prompt de-dupe, disabled-entry skip, and preserve-original fallback.
2. Verify RED with `swiftc` referencing `GlossaryEntry`.
3. Implement `GlossaryEntry`, `GlossaryPromptBuilder`, and `GlossaryEntryEditor` in `Glossary.swift`.
4. Add `glossaryEntries` Codable support and restart comparison.
5. Inject glossary block into Gemini `setupInstruction()` before source hint and user prompt.
6. Verify with one-off Swift checks and commit `feat: add terminology glossary model`.

### Task 2: Settings UI and localization

Files:
- Modify `LiveBuddy/Views/Settings/SettingsView.swift`
- Modify `LiveBuddy/Models/AppState.swift`
- Modify `LiveBuddy/Models/InterfaceLanguage.swift`
- Modify verifier scripts

Steps:
1. Add localization keys and translations.
2. Add `addGlossaryEntry(source:target:)` and `deleteGlossaryEntry(_:)` to `AppState`.
3. Add Settings glossary section with source/target fields, Add button, list, and delete buttons.
4. Update verifiers and commit `feat: add terminology glossary UI`.

### Task 3: Docs, verification, push, CI

Files:
- Modify `README.md`

Steps:
1. Document glossary behavior and empty target = preserve original.
2. Run static verifiers, one-off Swift glossary checks, and full temp Swift typecheck.
3. Commit docs.
4. Push to `target/main`.
5. Watch GitHub Actions.
