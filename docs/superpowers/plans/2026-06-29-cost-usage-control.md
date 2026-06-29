# Cost and Usage Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add live usage metrics, estimated cost, idle soft pause, and per-session/daily usage limits.

**Architecture:** Add a pure `UsageControlEngine` model for accounting, idle detection, hysteresis, and buffer decisions. `AppState` integrates the engine between audio capture and Gemini send, owns reconnect/flush side effects, and exposes a localized snapshot to Settings/MenuBar.

**Tech Stack:** Swift, SwiftUI, Foundation, existing Swift Testing tests, existing verifier scripts, existing Gemini WebSocket client.

---

## File structure

- Create `LiveBuddy/Models/UsageControl.swift`: pure usage settings, snapshots, ledger, ring-buffer bookkeeping, and engine decisions.
- Create `LiveBuddyTests/UsageControlTests.swift`: test all pure usage and idle behavior.
- Modify `LiveBuddy/Models/AppSettings.swift`: add `LiveUsageSettings` with legacy decode defaults.
- Modify `LiveBuddy/Models/AppState.swift`: wire usage engine into audio sending, auto-pause/resume, daily ledger persistence, transcript activity markers, and public snapshots.
- Modify `LiveBuddy/Models/InterfaceLanguage.swift`: localized labels/statuses for cost controls.
- Modify `LiveBuddy/Views/Settings/SettingsView.swift`: add Cost & Usage Control section.
- Modify `LiveBuddy/Views/MenuBar/MenuBarView.swift`: show compact runtime usage.
- Modify `README.md`: document cost controls and approximate pricing.

## Task 1: Pure usage-control model with TDD

**Files:**
- Create: `LiveBuddyTests/UsageControlTests.swift`
- Create: `LiveBuddy/Models/UsageControl.swift`

- [ ] Write failing tests for sent-duration cost calculation, idle warning, idle pause, hysteresis, resume buffer, per-session limit, and daily ledger reset.
- [ ] Run focused red check with a temporary Swift test harness; expected failure is missing `LiveUsageSettings` / `UsageControlEngine`.
- [ ] Implement `LiveUsageSettings`, `UsageControlSnapshot`, `UsageControlPauseReason`, `UsageControlRuntimeState`, `BufferedAudioChunk`, `UsageControlDecision`, `UsageLedger`, and `UsageControlEngine`.
- [ ] Run focused green check and full app typecheck.
- [ ] Commit `feat: add usage control engine`.

## Task 2: Settings persistence

**Files:**
- Modify: `LiveBuddy/Models/AppSettings.swift`
- Modify: `LiveBuddyTests/UsageControlTests.swift`

- [ ] Add tests that legacy settings decode usage defaults and encoding round-trips edited values.
- [ ] Add `usageControls` to `AppSettings`, `CodingKeys`, decoder, and encoder.
- [ ] Verify changes do not mark running Gemini session for restart unless audio/API-affecting usage settings require runtime handling.
- [ ] Run tests/typecheck.
- [ ] Commit `feat: persist usage control settings`.

## Task 3: AppState runtime integration

**Files:**
- Modify: `LiveBuddy/Models/AppState.swift`

- [ ] Add ledger URL, usage engine, resume buffer, usage snapshot published state, and helper formatters.
- [ ] On start, reset the engine with current settings and today's ledger.
- [ ] Replace direct `client.sendAudio(data)` with `handleCapturedAudio(data:source:level:)` that asks the engine whether to send, pause, warn, or resume.
- [ ] Implement `enterIdleAutoPause`, `enterLimitPause`, `resumeFromUsagePauseIfNeeded`, and `flushBufferedAudio`.
- [ ] Mark transcript activity in `appendOriginalText` and `appendCaption`.
- [ ] Persist the daily ledger after counted sends and when stopping.
- [ ] Run typecheck.
- [ ] Commit `feat: wire usage controls into audio runtime`.

## Task 4: UI and localization

**Files:**
- Modify: `LiveBuddy/Models/InterfaceLanguage.swift`
- Modify: `LiveBuddy/Views/Settings/SettingsView.swift`
- Modify: `LiveBuddy/Views/MenuBar/MenuBarView.swift`

- [ ] Add localized strings for cost controls, session/today duration, estimate, idle pause, limits, and approximate pricing note across all interface languages.
- [ ] Add Settings section with toggles/sliders/steppers and current metrics.
- [ ] Add compact MenuBar usage panel.
- [ ] Run interface-language verifier and typecheck.
- [ ] Commit `feat: add cost control UI`.

## Task 5: Documentation, verification, push, local update

**Files:**
- Modify: `README.md`

- [ ] Document cost controls and the default Gemini Live Translate estimate.
- [ ] Run `python3 scripts/verify_p0_onboarding.py`, `python3 scripts/verify_interface_language.py`, `python3 scripts/verify_ci_workflow.py`, `python3 scripts/verify_release_packaging.py`, focused usage tests, and app source `swiftc -typecheck`.
- [ ] Commit `docs: document cost usage controls`.
- [ ] Push to `target main` and wait for GitHub Actions.
- [ ] Rebuild `/Users/sule/Documents/mac翻译/releases/Live Translate Buddy.app` and launch it.
