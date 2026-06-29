# Virtual Audio Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add opt-in BlackHole-style audio isolation so original audio can be routed away from speakers while translated speech plays to the selected output device.

**Architecture:** Extend settings and CoreAudio device helpers, add output-device routing to `PCM16AudioPlayer`, and integrate an isolation branch in `AppState.startCapture()`. UI exposes an enable toggle, device pickers, status, and setup links.

**Tech Stack:** Swift, SwiftUI, CoreAudio, AudioToolbox, AVFoundation, existing verifier scripts, GitHub Actions.

---

## Task 1: Settings and pure device-selection tests

**Files:**
- Modify `LiveBuddy/Models/AppSettings.swift`
- Modify `LiveBuddy/Services/AudioDeviceManager.swift`
- Create/modify `LiveBuddyTests/VirtualAudioIsolationTests.swift`

- [ ] Write failing tests for settings defaults/round-trip and virtual input auto-selection.
- [ ] Implement new settings fields and pure selector helper.
- [ ] Run focused Swift harness and app typecheck.
- [ ] Commit `feat: add virtual audio isolation settings`.

## Task 2: Runtime audio routing

**Files:**
- Modify `LiveBuddy/Services/AudioDeviceManager.swift`
- Modify `LiveBuddy/Utilities/PCM16AudioPlayer.swift`
- Modify `LiveBuddy/Models/AppState.swift`

- [ ] Add output device enumeration and output UID lookup.
- [ ] Add translated-output-device routing to `PCM16AudioPlayer`.
- [ ] Add `availableOutputDevices`, refresh logic, and isolation capture branch in `AppState`.
- [ ] Run app typecheck.
- [ ] Commit `feat: route translated audio output device`.

## Task 3: UI/localization/docs/final verification

**Files:**
- Modify `LiveBuddy/Models/InterfaceLanguage.swift`
- Modify `LiveBuddy/Views/Settings/SettingsView.swift`
- Modify `LiveBuddy/Views/MenuBar/MenuBarView.swift` if needed
- Modify `README.md`

- [ ] Add localized strings for isolation toggle, device pickers, setup links, and guide text.
- [ ] Add Settings controls and update translated voice volume wording.
- [ ] Document BlackHole setup.
- [ ] Run all verifiers, typecheck, push, wait for CI, rebuild local app.
