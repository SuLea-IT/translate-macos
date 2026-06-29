# Custom Global Shortcuts Design

## Outcome

Let users customize LiveBuddy's three global shortcuts from Settings without adding third-party dependencies or long-lived keyboard event taps. The feature should keep the current defaults for existing users, validate obvious conflicts before saving, and re-register shortcuts immediately after a change.

## Open-source references studied

- [KeyboardShortcuts](https://github.com/sindresorhus/KeyboardShortcuts)
  - Stores a small value object made from Carbon key code and normalized modifiers.
  - Validates conflicts with system symbolic hotkeys and the app main menu.
  - Uses Carbon `RegisterEventHotKey` for global registration and limits recorder work to UI interaction.
- [HotKey](https://github.com/soffes/HotKey)
  - Uses a compact `KeyCombo` model with Carbon key code + Carbon modifiers.
  - Separates the value model from the Carbon registration controller.
- [MASShortcut](https://github.com/cocoabits/MASShortcut)
  - Uses practical validity rules: bare letters are not valid global shortcuts, while function keys can be more permissive.
  - Checks duplicates against system-wide symbolic hotkeys and menu shortcuts.

We will borrow the patterns, not code: compact value model, pure validation, short-lived recorder, and existing Carbon registration.

## Current state

`GlobalShortcut.defaults` currently hard-codes three shortcuts:

- `⌃⌥⌘T` start/stop translation
- `⌃⌥⌘C` show caption window
- `⌃⌥⌘M` mute/unmute translated audio

`AppState.configureGlobalShortcuts()` always registers `GlobalShortcut.defaults`. Settings shows the shortcuts as read-only rows.

## Design

### Data model

Keep `GlobalShortcut` as the runtime value. Add these pure helpers in `LiveBuddy/Models/GlobalShortcut.swift`:

- `static func defaultShortcut(for action: GlobalShortcutAction) -> GlobalShortcut`
- `static func defaultsByAction() -> [GlobalShortcutAction: GlobalShortcut]`
- `struct GlobalShortcutSet: Codable, Equatable`
  - stores `[GlobalShortcutAction: GlobalShortcut]` logically, encoded as `[GlobalShortcut]` for stable JSON.
  - fills missing actions from defaults on decode/init.
  - rejects duplicate action entries by taking the last valid one.
- `struct GlobalShortcutValidator`
  - pure validation for duplicate LiveBuddy shortcuts and basic validity.
  - optional dependency closures for system/menu conflict checks.

`AppSettings` adds `var globalShortcuts: GlobalShortcutSet = .defaults`. Existing JSON without this field decodes to defaults.

### Validation rules

A shortcut is valid when:

1. It has a non-empty key equivalent and a known key code.
2. Function keys are allowed with no modifier or any modifiers.
3. Non-function keys must include at least `Command` or `Control`.
4. The same key code + modifiers cannot be assigned to two LiveBuddy actions.
5. If system/menu conflict check reports a conflict, Settings shows a warning and does not save.

This follows MASShortcut's practical safety rule and KeyboardShortcuts/HotKey conflict-check separation.

### Registration

Change `AppState.configureGlobalShortcuts()` to register `settings.globalShortcuts.enabledShortcuts` instead of `GlobalShortcut.defaults`.

When a shortcut is changed:

1. Validate proposed shortcut against the current set.
2. If valid, update `settings.globalShortcuts`.
3. `didSet` saves settings.
4. Re-register the Carbon hotkeys immediately.
5. If registration fails because another app already owns the combo, keep the saved setting but show a diagnostic/log entry. This mirrors current registration behavior and avoids hidden mutation after save.

### Recorder UI

Add a small SwiftUI/AppKit bridge in Settings:

- `ShortcutRecorderField`
  - Shows current display text.
  - A `Record` button enters recording mode.
  - While recording, a local `NSEvent` monitor captures the next keyDown event.
  - `Esc` cancels recording.
  - `Delete` / `ForwardDelete` clears the shortcut for that action only if at least one other action remains usable.
  - Monitor is installed only during recording and removed immediately after capture/cancel.

The recorder must not use a global event tap. This keeps memory and privacy footprint low.

### Settings UI

Replace the read-only shortcut rows with editable rows:

- action title
- current shortcut display
- validation warning text when invalid/conflicting
- buttons: Record, Clear, Reset
- section button: Reset All to Defaults

The existing `Enable global shortcuts` toggle remains.

### Localization

Add localized keys for:

- customize shortcut
- record shortcut
- recording prompt
- clear shortcut
- reset shortcut
- reset all shortcuts
- shortcut conflict / invalid messages

Use all eight existing interface languages.

### Non-goals

- No arbitrary per-action shortcut count.
- No global event tap.
- No background polling for system conflicts.
- No user-editable shortcut names.
- No third-party package dependency.

## Testing

Unit tests should cover:

- legacy settings decode default shortcuts.
- custom shortcuts persist through Codable.
- duplicate LiveBuddy shortcuts are rejected.
- bare letter without Command/Control is invalid.
- function keys are valid.
- reset restores defaults.
- registration uses settings shortcuts rather than hard-coded defaults.

Static verifier should assert:

- `AppSettings` persists `globalShortcuts`.
- `AppState.configureGlobalShortcuts` registers `settings.globalShortcuts`.
- Settings renders `ShortcutRecorderField`.
- No `CGEventTapCreate` appears in shortcut recorder code.

## Self-review

- Scope is one feature: custom global shortcuts.
- Design keeps existing defaults and read-only behavior as fallback.
- Runtime memory remains bounded: no history, no background monitors, no event tap.
- Open-source references are patterns only; no code copied.
