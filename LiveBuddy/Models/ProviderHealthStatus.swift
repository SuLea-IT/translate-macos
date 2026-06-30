import Foundation

enum ProviderHealthStatus: Codable, Equatable {
    case missing
    case unchecked
    case checking
    case valid(checkedAt: Date)
    case invalid(message: String, checkedAt: Date)
    case failed(message: String, checkedAt: Date)

    var blocksStart: Bool {
        switch self {
        case .missing, .invalid:
            true
        case .unchecked, .checking, .valid, .failed:
            false
        }
    }
}
