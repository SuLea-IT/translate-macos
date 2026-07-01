import SwiftUI
import AppKit
import Combine

struct CaptionView: View {
    @EnvironmentObject private var appState: AppState
    let onClose: () -> Void

    var body: some View {
        ZStack {
            VisualEffectView(
                material: .hudWindow,
                blendingMode: .behindWindow,
                state: .active
            )
            .opacity(appState.settings.backgroundOpacity)
            .overlay(
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .stroke(
                        LinearGradient(
                            stops: [
                                .init(color: .white.opacity(0.4), location: 0),
                                .init(color: .clear, location: 0.3),
                                .init(color: .white.opacity(0.1), location: 1)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        lineWidth: 1
                    )
            )
            .shadow(color: .black.opacity(0.3), radius: 12, x: 0, y: 6)

            CaptionScrollTextView(
                lines: appState.subtitleLines,
                settings: appState.settings
            )
            .padding(.horizontal, 12)
            .padding(.vertical, 8)

            Color.clear
                .frame(height: 1)
        }
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .overlay(alignment: .topLeading) {
            topControls
                .padding(.leading, 10)
                .padding(.top, 8)
                .opacity(isHovered ? 1 : 0)
                .animation(.easeInOut(duration: 0.2), value: isHovered)
        }
        .overlay(alignment: .topTrailing) {
            closeButton
                .padding(.trailing, 9)
                .padding(.top, 8)
                .opacity(isHovered ? 1 : 0)
                .animation(.easeInOut(duration: 0.2), value: isHovered)
        }
        .overlay {
            SubtitleResizeOverlay()
        }
        .padding(1)
        .onHover { hovering in
            isHovered = hovering
        }
    }

    @State private var isHovered = false

    private var topControls: some View {
        HStack(spacing: 9) {
            Button {
                appState.toggle()
            } label: {
                Image(systemName: appState.isRunning ? "pause.fill" : "play.fill")
                    .font(.system(size: 14, weight: .bold))
                    .frame(width: 28, height: 28)
                    .contentShape(Rectangle())
                    .contentTransition(.symbolEffect(.replace))
            }
            .buttonStyle(.plain)
            .foregroundStyle(.white.opacity(0.86))
            .help(appState.isRunning ? appState.t(.pause) : appState.t(.play))

            StatusDot(level: appState.statusLevel, interfaceLanguage: appState.settings.interfaceLanguage)

            Text(appState.languagePairDisplayText)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white.opacity(0.72))
                .lineLimit(1)
                .frame(maxWidth: 170, alignment: .leading)

            if appState.isRunning {
                WaveSoundBar(level: appState.audioLevel)
                    .transition(.opacity)
            }

            Image(systemName: "circle.lefthalf.filled")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(.white.opacity(0.62))

            Slider(
                value: Binding(
                    get: { appState.settings.backgroundOpacity },
                    set: { appState.updateSetting(\.backgroundOpacity, to: $0) }
                ),
                in: 0.15...0.95
            )
            .controlSize(.small)
            .frame(width: 82)
            .help(appState.t(.transparency))

            Color.white.opacity(0.2)
                .frame(width: 1, height: 12)

            Picker(appState.t(.audioPlaybackMode), selection: appState.binding(\.audioPlaybackMode)) {
                ForEach(AudioPlaybackMode.allCases) { mode in
                    Text(mode.localizedTitle(language: appState.settings.interfaceLanguage)).tag(mode)
                }
            }
            .labelsHidden()
            .pickerStyle(.menu)
            .controlSize(.small)
            .frame(width: 128)
            .help(appState.t(.audioPlaybackMode))

            Button {
                appState.updateSetting(\.audioPlayerMuted, to: !appState.settings.audioPlayerMuted)
            } label: {
                Image(systemName: !appState.settings.audioPlaybackMode.allowsTranslatedAudio || appState.settings.audioPlayerMuted || appState.settings.audioPlayerVolume == 0 ? "speaker.slash.fill" : (appState.settings.audioPlayerVolume < 0.5 ? "speaker.wave.1.fill" : "speaker.wave.2.fill"))
                    .font(.system(size: 12, weight: .semibold))
                    .frame(width: 16)
            }
            .buttonStyle(.plain)
            .foregroundStyle(.white.opacity(0.86))
            .help(appState.settings.audioPlayerMuted ? appState.t(.unmute) : appState.t(.mute))
            .disabled(!appState.settings.audioPlaybackMode.allowsTranslatedAudio)

            Slider(
                value: Binding(
                    get: { appState.settings.audioPlayerVolume },
                    set: { appState.updateSetting(\.audioPlayerVolume, to: $0) }
                ),
                in: 0...1
            )
            .disabled(!appState.settings.audioPlaybackMode.allowsTranslatedAudio || appState.settings.audioPlayerMuted)
            .controlSize(.small)
            .frame(width: 60)
            .help(appState.t(.volume))
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 5)
        .background(
            Capsule()
                .fill(.ultraThinMaterial)
                .overlay(
                    Capsule()
                        .stroke(
                            LinearGradient(
                                colors: [.white.opacity(0.3), .clear],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 0.5
                        )
                )
                .shadow(color: .black.opacity(0.2), radius: 4, x: 0, y: 2)
        )
    }

    private var closeButton: some View {
        Button(action: onClose) {
            Image(systemName: "xmark")
                .font(.system(size: 12, weight: .bold))
                .frame(width: 22, height: 22)
        }
        .buttonStyle(.plain)
        .foregroundStyle(.white.opacity(0.8))
        .background(
            Circle()
                .fill(.ultraThinMaterial)
                .overlay(
                    Circle()
                        .stroke(
                            LinearGradient(
                                colors: [.white.opacity(0.3), .clear],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 0.5
                        )
                )
                .shadow(color: .black.opacity(0.2), radius: 4, x: 0, y: 2)
        )
        .help(appState.t(.closeSubtitleWindowAndStopCapture))
    }
}
