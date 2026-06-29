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
