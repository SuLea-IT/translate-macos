import Foundation

enum PermissionRequirement: String, Codable, CaseIterable, Equatable {
    case microphone
    case screenRecording
}

enum PermissionGrantState: String, Codable, Equatable {
    case granted
    case denied
    case notDetermined
    case restricted
    case unknown

    var isGranted: Bool { self == .granted }
}

struct PermissionStatus: Codable, Equatable {
    let requirement: PermissionRequirement
    let state: PermissionGrantState
    let checkedAt: Date

    static func unknown(_ requirement: PermissionRequirement, checkedAt: Date = Date()) -> PermissionStatus {
        PermissionStatus(requirement: requirement, state: .unknown, checkedAt: checkedAt)
    }
}

enum ChecklistRequirementState: String, Codable, Equatable {
    case satisfied
    case blocked
    case notNeeded
    case unknown
}

struct PermissionChecklistItem: Codable, Equatable {
    let requirement: PermissionRequirement
    let permissionState: PermissionGrantState
    let requirementState: ChecklistRequirementState
    let checkedAt: Date
}

enum SetupBlockingIssue: String, Codable, CaseIterable, Equatable {
    case apiKeyMissing
    case apiKeyInvalid
    case microphonePermissionMissing
    case screenRecordingPermissionMissing
}

struct SetupChecklistState: Codable, Equatable {
    let apiKey: ProviderHealthStatus
    let microphone: PermissionChecklistItem
    let screenRecording: PermissionChecklistItem
    let blockingIssues: [SetupBlockingIssue]

    var canStart: Bool { blockingIssues.isEmpty }

    static let initial = SetupChecklistState.derive(
        audioSource: .screen,
        apiKey: .missing,
        microphone: .unknown(.microphone),
        screenRecording: .unknown(.screenRecording)
    )

    static func derive(
        audioSource: AudioSource,
        apiKey: ProviderHealthStatus,
        microphone: PermissionStatus,
        screenRecording: PermissionStatus
    ) -> SetupChecklistState {
        var issues: [SetupBlockingIssue] = []
        switch apiKey {
        case .missing:
            issues.append(.apiKeyMissing)
        case .invalid:
            issues.append(.apiKeyInvalid)
        case .unchecked, .checking, .valid, .failed:
            break
        }

        let needsMicrophone = audioSource == .microphone || audioSource == .both
        let needsScreen = audioSource == .screen || audioSource == .both
        let microphoneItem = item(for: microphone, needed: needsMicrophone)
        let screenItem = item(for: screenRecording, needed: needsScreen)

        if microphoneItem.requirementState == .blocked {
            issues.append(.microphonePermissionMissing)
        }
        if screenItem.requirementState == .blocked {
            issues.append(.screenRecordingPermissionMissing)
        }

        return SetupChecklistState(
            apiKey: apiKey,
            microphone: microphoneItem,
            screenRecording: screenItem,
            blockingIssues: issues
        )
    }

    private static func item(for status: PermissionStatus, needed: Bool) -> PermissionChecklistItem {
        let requirementState: ChecklistRequirementState
        if !needed {
            requirementState = .notNeeded
        } else if status.state == .granted {
            requirementState = .satisfied
        } else if status.state == .unknown || status.state == .notDetermined {
            requirementState = .unknown
        } else {
            requirementState = .blocked
        }

        return PermissionChecklistItem(
            requirement: status.requirement,
            permissionState: status.state,
            requirementState: requirementState,
            checkedAt: status.checkedAt
        )
    }
}

enum SetupPreflightResult: Equatable {
    case allowed
    case blocked(SetupBlockingIssue)

    static func from(_ checklist: SetupChecklistState) -> SetupPreflightResult {
        if let firstIssue = checklist.blockingIssues.first {
            return .blocked(firstIssue)
        }
        return .allowed
    }
}
