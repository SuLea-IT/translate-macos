# Keychain API Key Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store the Gemini API key in macOS Keychain instead of `settings.json`, while preserving legacy settings migration and current UI behavior.

**Architecture:** Add a small `SecretStore` boundary, a native `KeychainSecretStore`, and an `APIKeyStore` wrapper with LiveBuddy service/account constants. Keep `AppSettings.apiKey` as runtime state, decode legacy JSON for migration, but omit the key when encoding new settings.

**Tech Stack:** Swift, Security.framework Keychain Services, SwiftUI Binding, Swift Testing, Python static verifier, existing GitHub Actions xcodebuild workflow.

---

## File Structure

Create:

- `LiveBuddy/Services/KeychainSecretStore.swift` — native Keychain read/write/delete implementation.
- `LiveBuddy/Services/APIKeyStore.swift` — LiveBuddy-specific API key wrapper over `SecretStore`.
- `LiveBuddyTests/APIKeyStoreTests.swift` — in-memory store tests for save/read/delete.

Modify:

- `LiveBuddy/Models/AppSettings.swift` — omit `apiKey` from encoding, keep legacy decoding.
- `LiveBuddy/Models/AppState.swift` — migrate legacy API key to Keychain, read Keychain on launch, expose `apiKeyBinding()`.
- `LiveBuddy/Views/Settings/SettingsView.swift` — use `appState.apiKeyBinding()` for API key fields.
- `LiveBuddyTests/InterfaceLanguageTests.swift` — add encoding regression for `apiKey` omission.
- `scripts/verify_p0_onboarding.py` — add static checks for Keychain integration.
- `README.md` — document secure API key storage.

## Reference Rules

- Do not add a third-party Keychain dependency.
- Do not copy code from KeychainAccess or keychain-swift.
- Borrow only the architecture and algorithm: stable service/account IDs, add-then-update on duplicate, delete for empty values, and keep Security dictionaries inside one file.
- Do not store `apiKey` in `settings.json` after this feature.

---

### Task 1: API key store tests and pure wrapper

**Files:**
- Create: `LiveBuddy/Services/APIKeyStore.swift`
- Create: `LiveBuddyTests/APIKeyStoreTests.swift`

- [ ] **Step 1: Write the failing tests**

Create `LiveBuddyTests/APIKeyStoreTests.swift`:

```swift
import Foundation
import Testing
@testable import LiveBuddy

private final class InMemorySecretStore: SecretStore {
    private var values: [String: String] = [:]

    func read(service: String, account: String) throws -> String? {
        values["\(service)::\(account)"]
    }

    func write(_ value: String, service: String, account: String) throws {
        values["\(service)::\(account)"] = value
    }

    func delete(service: String, account: String) throws {
        values.removeValue(forKey: "\(service)::\(account)")
    }
}

struct APIKeyStoreTests {
    @Test func savingKeyWritesTrimmedSecret() throws {
        let memory = InMemorySecretStore()
        let store = APIKeyStore(secretStore: memory)

        try store.save("  test-key  ")

        #expect(try store.read() == "test-key")
    }

    @Test func savingEmptyKeyDeletesSecret() throws {
        let memory = InMemorySecretStore()
        let store = APIKeyStore(secretStore: memory)

        try store.save("test-key")
        try store.save("   ")

        #expect(try store.read() == nil)
    }
}
```

- [ ] **Step 2: Verify failure**

Run:

```bash
python3 scripts/verify_p0_onboarding.py
```

Expected before implementation: failure showing missing `APIKeyStore` or `SecretStore` after verifier is updated in Task 3, or Swift compile failure if run under Xcode because `SecretStore` does not exist.

- [ ] **Step 3: Implement `APIKeyStore.swift`**

Create `LiveBuddy/Services/APIKeyStore.swift`:

```swift
import Foundation

protocol SecretStore {
    func read(service: String, account: String) throws -> String?
    func write(_ value: String, service: String, account: String) throws
    func delete(service: String, account: String) throws
}

struct APIKeyStore {
    static let liveBuddy = APIKeyStore(secretStore: KeychainSecretStore())

    let secretStore: SecretStore
    let service: String
    let account: String

    init(
        secretStore: SecretStore,
        service: String = "LiveBuddy",
        account: String = "gemini-api-key"
    ) {
        self.secretStore = secretStore
        self.service = service
        self.account = account
    }

    func read() throws -> String? {
        try secretStore.read(service: service, account: account)
    }

    func save(_ apiKey: String) throws {
        let trimmed = apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            try secretStore.delete(service: service, account: account)
        } else {
            try secretStore.write(trimmed, service: service, account: account)
        }
    }
}
```

- [ ] **Step 4: Verify wrapper behavior**

Run a temporary Swift check or GitHub unit tests. Local fallback:

```bash
cat > /tmp/api_key_store_check.swift <<'SWIFT'
import Foundation

private final class InMemorySecretStore: SecretStore {
    private var values: [String: String] = [:]
    func read(service: String, account: String) throws -> String? { values["\(service)::\(account)"] }
    func write(_ value: String, service: String, account: String) throws { values["\(service)::\(account)"] = value }
    func delete(service: String, account: String) throws { values.removeValue(forKey: "\(service)::\(account)") }
}

@main
struct Check {
    static func main() throws {
        let memory = InMemorySecretStore()
        let store = APIKeyStore(secretStore: memory)
        try store.save("  test-key  ")
        precondition(try store.read() == "test-key")
        try store.save("   ")
        precondition(try store.read() == nil)
        print("api key store check passed")
    }
}
SWIFT
swiftc -parse-as-library LiveBuddy/Services/APIKeyStore.swift LiveBuddy/Services/KeychainSecretStore.swift /tmp/api_key_store_check.swift -o /tmp/api_key_store_check
/tmp/api_key_store_check
```

Expected after Task 2: prints `api key store check passed`.

- [ ] **Step 5: Commit after Task 2 completes**

Commit together with Task 2 because `APIKeyStore.liveBuddy` references `KeychainSecretStore`.

---

### Task 2: Native Keychain secret store

**Files:**
- Create: `LiveBuddy/Services/KeychainSecretStore.swift`

- [ ] **Step 1: Implement Keychain service**

Create `LiveBuddy/Services/KeychainSecretStore.swift`:

```swift
import Foundation
import Security

struct KeychainSecretStore: SecretStore {
    func read(service: String, account: String) throws -> String? {
        var query = baseQuery(service: service, account: account)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound {
            return nil
        }
        guard status == errSecSuccess else {
            throw KeychainSecretStoreError.unhandledStatus(status)
        }
        guard let data = result as? Data,
              let value = String(data: data, encoding: .utf8) else {
            throw KeychainSecretStoreError.invalidData
        }
        return value
    }

    func write(_ value: String, service: String, account: String) throws {
        guard let data = value.data(using: .utf8) else {
            throw KeychainSecretStoreError.invalidData
        }

        var query = baseQuery(service: service, account: account)
        query[kSecValueData as String] = data
        query[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly

        let addStatus = SecItemAdd(query as CFDictionary, nil)
        if addStatus == errSecSuccess {
            return
        }
        if addStatus == errSecDuplicateItem {
            let attributes: [String: Any] = [
                kSecValueData as String: data,
                kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            ]
            let updateStatus = SecItemUpdate(baseQuery(service: service, account: account) as CFDictionary, attributes as CFDictionary)
            guard updateStatus == errSecSuccess else {
                throw KeychainSecretStoreError.unhandledStatus(updateStatus)
            }
            return
        }
        throw KeychainSecretStoreError.unhandledStatus(addStatus)
    }

    func delete(service: String, account: String) throws {
        let status = SecItemDelete(baseQuery(service: service, account: account) as CFDictionary)
        if status == errSecSuccess || status == errSecItemNotFound {
            return
        }
        throw KeychainSecretStoreError.unhandledStatus(status)
    }

    private func baseQuery(service: String, account: String) -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
    }
}

enum KeychainSecretStoreError: LocalizedError, Equatable {
    case invalidData
    case unhandledStatus(OSStatus)

    var errorDescription: String? {
        switch self {
        case .invalidData:
            return "Cannot encode or decode Keychain data."
        case .unhandledStatus(let status):
            return "Keychain operation failed with status \(status)."
        }
    }
}
```

- [ ] **Step 2: Run wrapper verification**

Run the local fallback command from Task 1 Step 4.

Expected: `api key store check passed`.

- [ ] **Step 3: Commit**

```bash
git add LiveBuddy/Services/APIKeyStore.swift LiveBuddy/Services/KeychainSecretStore.swift LiveBuddyTests/APIKeyStoreTests.swift
git commit -m "feat: add keychain API key store"
```

---

### Task 3: Settings encoding and AppState migration

**Files:**
- Modify: `LiveBuddy/Models/AppSettings.swift`
- Modify: `LiveBuddy/Models/AppState.swift`
- Modify: `LiveBuddy/Views/Settings/SettingsView.swift`
- Modify: `LiveBuddyTests/InterfaceLanguageTests.swift`
- Modify: `scripts/verify_p0_onboarding.py`

- [ ] **Step 1: Add failing encoding test**

Append to `LiveBuddyTests/InterfaceLanguageTests.swift`:

```swift
@Test func encodedSettingsDoNotContainApiKey() throws {
    var settings = AppSettings()
    settings.apiKey = "secret-key"

    let data = try JSONEncoder().encode(settings)
    let json = String(decoding: data, as: UTF8.self)

    #expect(json.contains("secret-key") == false)
    #expect(json.contains("apiKey") == false)
}
```

- [ ] **Step 2: Verify failure**

Run a local fallback check:

```bash
cat > /tmp/appsettings_keychain_red.swift <<'SWIFT'
import Foundation

@main
struct Check {
    static func main() throws {
        var settings = AppSettings()
        settings.apiKey = "secret-key"
        let data = try JSONEncoder().encode(settings)
        let json = String(decoding: data, as: UTF8.self)
        precondition(!json.contains("secret-key"))
        precondition(!json.contains("apiKey"))
    }
}
SWIFT
swiftc -parse-as-library LiveBuddy/Models/AppSettings.swift LiveBuddy/Models/InterfaceLanguage.swift /tmp/task2_stubs.swift /tmp/appsettings_keychain_red.swift -o /tmp/appsettings_keychain_red
/tmp/appsettings_keychain_red
```

Expected before implementation: precondition failure because `apiKey` is encoded.

- [ ] **Step 3: Implement custom encode**

In `AppSettings`, keep `case apiKey` in `CodingKeys` for decoding legacy JSON, but add `encode(to:)` and do not encode `apiKey`:

```swift
func encode(to encoder: Encoder) throws {
    var container = encoder.container(keyedBy: CodingKeys.self)
    try container.encode(activeProvider, forKey: .activeProvider)
    try container.encode(interfaceLanguage, forKey: .interfaceLanguage)
    try container.encode(targetLanguageCode, forKey: .targetLanguageCode)
    try container.encode(userPrompt, forKey: .userPrompt)
    try container.encode(audioSource, forKey: .audioSource)
    try container.encodeIfPresent(selectedMicrophoneDeviceUID, forKey: .selectedMicrophoneDeviceUID)
    try container.encode(backgroundOpacity, forKey: .backgroundOpacity)
    try container.encode(echoTargetLanguage, forKey: .echoTargetLanguage)
    try container.encodeIfPresent(subtitleScreenFrame, forKey: .subtitleScreenFrame)
    try container.encode(audioPlayerVolume, forKey: .audioPlayerVolume)
    try container.encode(audioPlayerMuted, forKey: .audioPlayerMuted)
    try container.encode(subtitleFontSize, forKey: .subtitleFontSize)
    try container.encode(subtitleFontName, forKey: .subtitleFontName)
    try container.encode(subtitleIsBold, forKey: .subtitleIsBold)
    try container.encode(subtitleIsItalic, forKey: .subtitleIsItalic)
    try container.encode(subtitleIsUnderline, forKey: .subtitleIsUnderline)
    try container.encode(subtitleColor, forKey: .subtitleColor)
}
```

- [ ] **Step 4: Wire AppState migration and binding**

Modify `AppState`:

- Add `private let apiKeyStore: APIKeyStore`.
- Change initializer to `init(apiKeyStore: APIKeyStore = .liveBuddy)`.
- During initialization, read Keychain and migrate legacy JSON.
- Add:

```swift
func apiKeyBinding() -> Binding<String> {
    Binding(
        get: { self.settings.apiKey },
        set: { [weak self] value in
            DispatchQueue.main.async {
                self?.updateAPIKey(value)
            }
        }
    )
}

func updateAPIKey(_ apiKey: String) {
    do {
        try apiKeyStore.save(apiKey)
    } catch {
        updateStatus("Cannot save API key securely", level: .error, log: true)
    }
    settings.apiKey = apiKey
    refreshSetupChecklist()
}
```

- [ ] **Step 5: Update SettingsView bindings**

Replace both `appState.binding(\.apiKey)` occurrences with `appState.apiKeyBinding()`.

- [ ] **Step 6: Update verifier**

Add static checks to `scripts/verify_p0_onboarding.py`:

- `KeychainSecretStore.swift` exists.
- It contains `SecItemAdd`, `SecItemUpdate`, `SecItemCopyMatching`, `SecItemDelete`.
- `AppState.swift` contains `APIKeyStore` and `apiKeyBinding()`.
- `SettingsView.swift` contains `apiKeyBinding()`.
- `AppSettings.swift` has `func encode(to encoder: Encoder)` and does not encode `apiKey` in that method.

- [ ] **Step 7: Verify and commit**

Run:

```bash
python3 scripts/verify_p0_onboarding.py
python3 scripts/verify_interface_language.py
python3 scripts/verify_ci_workflow.py
rm -rf /tmp/livebuddy_typecheck
mkdir -p /tmp/livebuddy_typecheck
cp -R LiveBuddy /tmp/livebuddy_typecheck/LiveBuddy
python3 - <<'PY'
from pathlib import Path
for p in Path('/tmp/livebuddy_typecheck/LiveBuddy').rglob('*.swift'):
    text = p.read_text()
    marker = '\n#Preview {'
    idx = text.find(marker)
    if idx != -1:
        p.write_text(text[:idx].rstrip() + '\n')
PY
swiftc -typecheck $(find /tmp/livebuddy_typecheck/LiveBuddy -name '*.swift' | sort)
```

Expected: verifier passes; typecheck exits 0, existing Sendable warnings may remain.

Commit:

```bash
git add LiveBuddy/Models/AppSettings.swift LiveBuddy/Models/AppState.swift LiveBuddy/Views/Settings/SettingsView.swift LiveBuddyTests/InterfaceLanguageTests.swift scripts/verify_p0_onboarding.py
git commit -m "feat: migrate API key storage to Keychain"
```

---

### Task 4: Documentation, push, and CI

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document secure API key storage**

Add under setup/configuration:

```markdown
### Secure API Key Storage

LiveBuddy stores the Gemini API key in macOS Keychain. Existing keys from older `settings.json` files are migrated to Keychain on launch, and new settings saves omit the API key from JSON.
```

- [ ] **Step 2: Verify**

Run the same verifier and typecheck commands from Task 3 Step 7.

- [ ] **Step 3: Commit and push**

```bash
git add README.md
git commit -m "docs: document Keychain API key storage"
git push target HEAD:main
```

- [ ] **Step 4: Watch CI**

```bash
gh run list --repo SuLea-IT/translate-macos --limit 5
gh run watch <new-run-id> --repo SuLea-IT/translate-macos --exit-status
```

Expected: GitHub Actions `Swift` workflow succeeds.

## Self-Review

- Spec coverage: secure store, migration, runtime compatibility, verifier, docs are all covered.
- Placeholder scan: no TODO/TBD placeholders.
- Type consistency: `SecretStore`, `KeychainSecretStore`, `APIKeyStore`, `apiKeyBinding()` names are consistent across tasks.
