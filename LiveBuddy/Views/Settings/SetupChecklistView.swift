import SwiftUI

struct SetupChecklistView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(appState.t(.setupChecklist))
                    .font(.headline)
                Spacer()
                Button(appState.t(.refreshStatus)) {
                    appState.refreshSetupChecklist()
                }
                .controlSize(.small)
            }

            SetupChecklistRow(
                title: appState.t(.apiKeyUpper),
                detail: providerDetail,
                state: providerState
            )

            SetupChecklistRow(
                title: appState.t(.microphonePermission),
                detail: detail(for: appState.setupChecklist.microphone),
                state: appState.setupChecklist.microphone.requirementState,
                actionTitle: appState.t(.openMicrophoneSettings)
            ) {
                appState.openMicrophoneSettings()
            }

            SetupChecklistRow(
                title: appState.t(.screenRecordingPermission),
                detail: detail(for: appState.setupChecklist.screenRecording),
                state: appState.setupChecklist.screenRecording.requirementState,
                actionTitle: appState.t(.openScreenRecordingSettings)
            ) {
                appState.openScreenRecordingSettings()
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(Color(nsColor: .controlBackgroundColor))
        )
        .onAppear {
            appState.refreshSetupChecklist()
        }
    }

    private var providerState: ChecklistRequirementState {
        switch appState.setupChecklist.apiKey {
        case .valid:
            return .satisfied
        case .missing, .invalid:
            return .blocked
        case .failed:
            return .unknown
        case .unchecked, .checking:
            return .unknown
        }
    }

    private var providerDetail: String {
        switch appState.setupChecklist.apiKey {
        case .missing:
            return appState.t(.apiKeyMissingMessage)
        case .unchecked:
            return appState.t(.apiKeyUnchecked)
        case .checking:
            return appState.t(.checking)
        case .valid:
            return appState.t(.apiKeyValid)
        case .invalid, .failed:
            return localizedProviderIssueDetail(for: appState.setupChecklist.apiKey)
        }
    }

    private func localizedProviderIssueDetail(for status: ProviderHealthStatus) -> String {
        if let issue = DiagnosticClassifier.from(providerStatus: status) {
            return appState.t(issue.messageKey)
        }
        return appState.t(.verificationFailed)
    }

    private func detail(for item: PermissionChecklistItem) -> String {
        switch item.requirementState {
        case .satisfied:
            return appState.t(.granted)
        case .blocked:
            return appState.t(.missing)
        case .notNeeded:
            return appState.t(.notNeeded)
        case .unknown:
            return appState.t(.unknown)
        }
    }
}

private struct SetupChecklistRow: View {
    let title: String
    let detail: String
    let state: ChecklistRequirementState
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: iconName)
                .foregroundStyle(iconColor)
                .frame(width: 18)

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.subheadline.weight(.medium))
                Text(detail)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 8)

            if let actionTitle, let action, state == .blocked {
                Button(actionTitle, action: action)
                    .controlSize(.small)
            }
        }
    }

    private var iconName: String {
        switch state {
        case .satisfied, .notNeeded:
            return "checkmark.circle.fill"
        case .blocked:
            return "exclamationmark.triangle.fill"
        case .unknown:
            return "questionmark.circle.fill"
        }
    }

    private var iconColor: Color {
        switch state {
        case .satisfied:
            return .green
        case .blocked:
            return .orange
        case .notNeeded, .unknown:
            return .secondary
        }
    }
}
