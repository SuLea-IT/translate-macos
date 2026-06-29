# Keychain API Key Storage Design

## Goal

Move the Gemini API key out of `settings.json` and into macOS Keychain while keeping LiveBuddy's UI and runtime behavior unchanged for users. The migration must preserve existing keys from old settings files and keep ordinary preferences in JSON.

## Current State

- `AppSettings.apiKey` is part of the Codable settings model in `LiveBuddy/Models/AppSettings.swift`.
- `AppState.saveSettings()` writes the whole settings object to `~/Library/Application Support/LiveBuddy/settings.json`.
- `SettingsView` binds `SecureField` directly to `appState.binding(\.apiKey)`.
- `ProviderHealthService` and `GeminiLiveTranslateClient` read `settings.apiKey` at runtime.

This means the secret can be written to plain JSON. That is not acceptable for a real user-facing macOS app.

## References and Borrowed Ideas

### Apple Keychain Services

Use the native Security framework with a generic password item:

- `kSecClassGenericPassword`
- `kSecAttrService = "LiveBuddy"`
- `kSecAttrAccount = "gemini-api-key"`
- `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`
- `SecItemCopyMatching` for read
- `SecItemAdd` for first write
- `SecItemUpdate` when `SecItemAdd` returns `errSecDuplicateItem`
- `SecItemDelete` for empty values or explicit removal

### KeychainAccess

Borrow the architecture pattern, not source code:

- A small typed wrapper around Security queries.
- Service and account are stable identifiers.
- Read/write/delete have one responsibility each.
- Call sites should not build raw Keychain dictionaries.

### keychain-swift

Borrow the lightweight API shape:

- `get`, `set`, and `delete` style operations.
- Keep the app code free of Security framework details.
- Use small data conversions and avoid retaining extra copies longer than needed.

## Design

### Storage boundary

Create a `SecretStore` protocol and a `KeychainSecretStore` implementation. App code talks to `APIKeyStore`; only `KeychainSecretStore` imports `Security`.

```swift
protocol SecretStore {
    func read(service: String, account: String) throws -> String?
    func write(_ value: String, service: String, account: String) throws
    func delete(service: String, account: String) throws
}
```

`APIKeyStore` owns the LiveBuddy service/account constants and trims whitespace when saving.

### Settings JSON behavior

`AppSettings` keeps `apiKey` as an in-memory runtime value so existing code can continue to read `settings.apiKey`.

Encoding must omit `apiKey`, so new `settings.json` files do not contain the secret. Decoding must still accept legacy JSON with `apiKey` so migration works.

### Migration

On `AppState` initialization:

1. Decode `settings.json` as before.
2. Read Keychain API key.
3. If Keychain has a value, use it as `settings.apiKey`.
4. If Keychain is empty but legacy JSON has a key, write that key to Keychain and keep it in runtime settings.
5. Rewrite settings after a successful migration so the JSON copy is removed.
6. If Keychain access fails, keep the runtime value for the session and log a user-visible error.

### UI binding

Replace direct `appState.binding(\.apiKey)` calls with `appState.apiKeyBinding()`. This lets the setter write to Keychain and then update runtime settings.

### Verification

- Unit tests cover `APIKeyStore` with an in-memory `SecretStore`.
- Unit tests prove `AppSettings` encoding omits `apiKey` while decoding legacy `apiKey` still works.
- Static verifier proves `AppState` uses `APIKeyStore`, `SettingsView` uses `apiKeyBinding()`, and Keychain code uses `SecItemAdd`/`SecItemUpdate` rather than plain JSON.
- Existing CI continues to run xcodebuild build and unit tests.

## Out of Scope

- iCloud Keychain sync.
- Multiple API providers beyond the existing Gemini provider.
- Showing masked key metadata such as last four characters.
- Manually editing or exporting Keychain items.
