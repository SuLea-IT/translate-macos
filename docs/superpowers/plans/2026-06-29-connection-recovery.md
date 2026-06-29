# Connection Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automatic reconnect for transient Gemini Live WebSocket interruptions and localized friendly runtime statuses.

**Architecture:** Introduce pure connection event and retry policy models, let `GeminiLiveTranslateClient` emit typed lifecycle events, and let `AppState` own reconnect scheduling so capture/transcript sessions remain alive across transient socket drops.

**Tech Stack:** Swift, URLSessionWebSocketTask, Swift Testing, SwiftUI localization dictionaries, Python static verifiers, GitHub Actions xcodebuild.

---

## File Structure

Create:

- `LiveBuddy/Models/ConnectionRecovery.swift` — pure retry policy and connection event classification.
- `LiveBuddyTests/ConnectionRecoveryTests.swift` — tests for backoff and recoverability.

Modify:

- `LiveBuddy/Services/GeminiLiveTranslateClient.swift` — emit typed connection events.
- `LiveBuddy/Models/AppState.swift` — schedule/cancel reconnect and reconnect only the Gemini client.
- `LiveBuddy/Models/InterfaceLanguage.swift` — localized reconnect/status strings.
- `scripts/verify_p0_onboarding.py` — static checks for recovery wiring.
- `scripts/verify_interface_language.py` — require new localization keys.
- `README.md` — document automatic recovery.

---

### Task 1: Pure recovery model

**Files:**
- Create: `LiveBuddy/Models/ConnectionRecovery.swift`
- Create: `LiveBuddyTests/ConnectionRecoveryTests.swift`

Steps:

1. Write failing tests for exponential delays and recoverability classification.
2. Verify RED with `swiftc -typecheck` referencing `ConnectionRecoveryPolicy.default` and `LiveConnectionEvent.disconnected`.
3. Implement `ConnectionRecoveryPolicy` and `LiveConnectionEvent`.
4. Verify GREEN with a small one-off Swift executable.
5. Commit `feat: add connection recovery policy`.

### Task 2: Gemini typed connection events

**Files:**
- Modify: `LiveBuddy/Services/GeminiLiveTranslateClient.swift`

Steps:

1. Add `onConnectionEvent` callback.
2. Emit `.socketOpened` and `.sessionReady` on successful lifecycle steps.
3. Emit `.socketClosed`, `.disconnected`, `.sendFailed`, `.serverError`, and `.parseFailed` at existing error points.
4. Keep existing `onStatus` strings so current UI/logging behavior does not regress.
5. Typecheck `GeminiLiveTranslateClient.swift` with `ConnectionRecovery.swift` and commit `feat: emit Gemini connection events`.

### Task 3: AppState reconnect orchestration and localization

**Files:**
- Modify: `LiveBuddy/Models/AppState.swift`
- Modify: `LiveBuddy/Models/InterfaceLanguage.swift`
- Modify: `scripts/verify_p0_onboarding.py`
- Modify: `scripts/verify_interface_language.py`

Steps:

1. Add localization keys and translations for reconnecting/recovered/failed/provider-error statuses.
2. Extract Gemini client setup into a helper so initial connect and reconnect share callbacks.
3. Add reconnect state fields: policy, attempts, task, manual-stop flag.
4. Handle recoverable events by scheduling one reconnect task with policy delay.
5. On reconnect success, replace only the Gemini client and leave capture/transcript state intact.
6. On manual stop, cancel reconnect and suppress reconnect from close events.
7. Update verifiers and commit `feat: recover transient Gemini disconnects`.

### Task 4: Documentation, verification, push, CI

**Files:**
- Modify: `README.md`

Steps:

1. Document automatic reconnect and no audio buffering during reconnect.
2. Run:
   - `python3 scripts/verify_p0_onboarding.py`
   - `python3 scripts/verify_interface_language.py`
   - `python3 scripts/verify_ci_workflow.py`
   - one-off Swift recovery checks
   - full temp Swift typecheck with previews stripped
3. Commit `docs: document connection recovery`.
4. Push `git push target HEAD:main`.
5. Watch latest GitHub Actions run with `gh run watch --exit-status`.

## Self-Review

- Spec coverage: retry policy, typed events, AppState orchestration, localization, docs, verification covered.
- Placeholder scan: no TODO/TBD placeholders.
- Type consistency: `ConnectionRecoveryPolicy`, `LiveConnectionEvent`, and `onConnectionEvent` names are consistent.
