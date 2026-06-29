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
