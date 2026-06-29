# Global Shortcuts Design

## Goal

Let users control LiveBuddy without opening the menu bar: start/stop translation, show captions, and mute/unmute translated audio from anywhere in macOS.

## References and Borrowed Ideas

### KeyboardShortcuts

Project: https://github.com/sindresorhus/KeyboardShortcuts

Relevant ideas to borrow:

- Keep shortcut definitions as typed names/actions.
- Register shortcuts globally through macOS APIs.
- Keep the UI layer separate from the low-level hotkey registration.

What we will not copy:

- We will not add the dependency or implement its full recorder UI in this pass.

### HotKey

Project: https://github.com/soffes/HotKey

Relevant ideas to borrow:

- Wrap Carbon `RegisterEventHotKey` behind a small Swift API.
- Store registration references and unregister on deinit/disable.
- Dispatch actions back to the main app state.

What we will not copy:

- We will not copy source or expose a generic public library surface.

### MASShortcut

Project: https://github.com/shpakovski/MASShortcut

Relevant ideas to borrow:

- Distinguish shortcut model, registration, and UI presentation.
- Treat registration failure as recoverable and report it.

What we will not copy:

- We will not build a custom shortcut recording control yet.

## Design

### Shortcuts

Use three fixed shortcuts with a low-conflict modifier chord:

- `⌃⌥⌘T` — Start/Stop translation.
- `⌃⌥⌘C` — Show caption window.
- `⌃⌥⌘M` — Mute/Unmute translated audio.

`AppSettings.globalShortcutsEnabled` defaults to `true`. Users can disable all global shortcuts in Settings.

### Architecture

Create a pure model:

- `GlobalShortcutAction`
- `GlobalShortcut`
- `GlobalShortcutRegistrationStatus`
- `GlobalShortcutRegistrationResult`

Create a low-level registrar:

- `GlobalShortcutRegistering` protocol.
- `CarbonGlobalShortcutRegistrar` implementation using `RegisterEventHotKey`, `InstallEventHandler`, and `UnregisterEventHotKey`.

`AppState` owns the registrar and maps actions to existing app behaviors. The registrar does not know about translation, UI, settings, or captions.

### Memory and lifecycle

- One event handler per registrar.
- Store only `EventHotKeyRef` references and unregister before re-registering.
- No polling or NSEvent monitor loop.
- No per-key background timers.

### UI

Settings shows:

- A global shortcuts enable toggle.
- A compact list of the three shortcut bindings.

MenuBar does not need another control beyond the normal buttons; shortcuts are documented in Settings and README.

## Verification

- Pure tests verify default shortcuts are unique and display strings are correct.
- Static verifier checks Carbon registrar uses register/unregister APIs and AppState routes all actions.
- Local `swiftc -typecheck` checks AppKit/Carbon integration.
- GitHub Actions xcodebuild build + unit tests must pass.
