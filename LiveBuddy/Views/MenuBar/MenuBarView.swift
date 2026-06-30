import SwiftUI

struct MenuBarView: View {
    @Environment(\.openWindow) private var openWindow
    @EnvironmentObject private var appState: AppState

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 12) {
                // Header
                HStack(spacing: 12) {
                    Button {
                        appState.toggle()
                    } label: {
                        Image(systemName: appState.isRunning ? "stop.circle.fill" : "play.circle.fill")
                            .font(.title2)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(appState.isRunning ? Color.red : Color.green)
                    .help(appState.isRunning ? appState.t(.stop) : appState.t(.start))
                    
                    Spacer()
                    
                    Button {
                        NotificationCenter.default.post(name: .showCaptionWindow, object: nil)
                    } label: {
                        Image(systemName: "captions.bubble")
                            .font(.title3)
                    }
                    .buttonStyle(.plain)
                    .help(appState.t(.showCaptionWindow))
                    
                    Button {
                        openWindow(id: "settings")
                        NSApp.activate(ignoringOtherApps: true)
                    } label: {
                        Image(systemName: "gearshape")
                            .font(.title3)
                    }
                    .buttonStyle(.plain)
                    .help(appState.t(.settings))
                    
                    Button {
                        NSApp.terminate(nil)
                    } label: {
                        Image(systemName: "power")
                            .font(.title3)
                    }
                    .buttonStyle(.plain)
                    .help(appState.t(.quitLiveBuddy))
                }
                
                Divider()

                if !appState.setupChecklist.canStart {
                    Button {
                        openWindow(id: "settings")
                        NSApp.activate(ignoringOtherApps: true)
                    } label: {
                        Label(appState.t(.setupIncomplete), systemImage: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                    }
                    .buttonStyle(.plain)

                    Divider()
                }

                usageCompactView

                Divider()
                
                // Audio Settings
                VStack(alignment: .leading, spacing: 12) {
                    Text(appState.t(.translationAndAudio))
                        .font(.headline)

                    Picker(appState.t(.interfaceLanguage), selection: appState.binding(\.interfaceLanguage)) {
                        ForEach(InterfaceLanguage.allCases) { language in
                            Text(language.displayName).tag(language)
                        }
                    }
                        
                    Picker(appState.t(.audioSource), selection: appState.binding(\.audioSource)) {
                        ForEach(AudioSource.allCases) { source in
                            Text(source.localizedTitle(language: appState.settings.interfaceLanguage)).tag(source)
                        }
                    }
                    .labelsHidden()
                    .pickerStyle(.segmented)
                    
                    if appState.settings.audioSource == .microphone || appState.settings.audioSource == .both {
                        Picker(appState.t(.microphone), selection: appState.binding(\.selectedMicrophoneDeviceUID)) {
                            Text(appState.t(.systemDefault)).tag(nil as String?)
                            ForEach(appState.availableMicrophones) { device in
                                Text(device.name).tag(device.uid as String?)
                            }
                        }
                    }
                    
                    Picker(appState.t(.translateFrom), selection: appState.binding(\.sourceLanguageCode)) {
                        Text(appState.t(.autoDetectLanguage)).tag(nil as String?)
                        ForEach(TranslationLanguage.all) { language in
                            Text(language.localizedName(language: appState.settings.interfaceLanguage)).tag(language.id as String?)
                        }
                    }

                    Picker(appState.t(.translateTo), selection: appState.binding(\.targetLanguageCode)) {
                        ForEach(TranslationLanguage.all) { language in
                            Text(language.localizedName(language: appState.settings.interfaceLanguage)).tag(language.id)
                        }
                    }

                    Picker(appState.t(.subtitleDisplayMode), selection: appState.binding(\.subtitleDisplayMode)) {
                        ForEach(SubtitleDisplayMode.allCases) { mode in
                            Text(mode.localizedTitle(language: appState.settings.interfaceLanguage)).tag(mode)
                        }
                    }
                    
                    Toggle(appState.t(.echoTargetLanguage), isOn: appState.binding(\.echoTargetLanguage))
                }
                
                Divider()
                
                // Volume
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(appState.t(.capturedAudioPlaybackVolume))
                        Spacer()
                        Text("\(Int(appState.settings.audioPlayerVolume * 100))%")
                            .monospacedDigit()
                            .foregroundStyle(.secondary)
                    }
                    HStack {
                        Button {
                            appState.updateSetting(\.audioPlayerMuted, to: !appState.settings.audioPlayerMuted)
                        } label: {
                            Image(systemName: appState.settings.audioPlayerMuted || appState.settings.audioPlayerVolume == 0 ? "speaker.slash.fill" : (appState.settings.audioPlayerVolume < 0.5 ? "speaker.wave.1.fill" : "speaker.wave.2.fill"))
                        }
                        .buttonStyle(.plain)
                        .help(appState.settings.audioPlayerMuted ? appState.t(.unmute) : appState.t(.mute))
                        
                        Slider(value: appState.binding(\.audioPlayerVolume), in: 0...1)
                            .disabled(appState.settings.audioPlayerMuted)
                    }
                }
                
                Divider()
                
                // Subtitle Styles
                VStack(alignment: .leading, spacing: 12) {
                    Text(appState.t(.subtitleStyle))
                        .font(.headline)
                        
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(appState.t(.subtitleFontSize))
                            Spacer()
                            Text("\(Int(appState.settings.subtitleFontSize))pt")
                                .monospacedDigit()
                                .foregroundStyle(.secondary)
                        }
                        Slider(value: appState.binding(\.subtitleFontSize), in: 14...60, step: 1)
                    }
                    
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(appState.t(.blackTransparency))
                            Spacer()
                            Text("\(Int(appState.settings.backgroundOpacity * 100))%")
                                .monospacedDigit()
                                .foregroundStyle(.secondary)
                        }
                        Slider(value: appState.binding(\.backgroundOpacity), in: 0.15...0.95)
                    }
                    
                    Picker(appState.t(.font), selection: appState.binding(\.subtitleFontName)) {
                        ForEach(SubtitleFontName.allCases) { font in
                            Text(font.displayName).tag(font)
                        }
                    }
                    
                    HStack(spacing: 12) {
                        Text(appState.t(.style))
                        Spacer()
                        Toggle(isOn: appState.binding(\.subtitleIsBold)) {
                            Text("B").font(.system(size: 14, weight: .bold))
                        }
                        .toggleStyle(.button)

                        Toggle(isOn: appState.binding(\.subtitleIsItalic)) {
                            Text("I").font(.system(size: 14, weight: .regular).italic())
                        }
                        .toggleStyle(.button)

                        Toggle(isOn: appState.binding(\.subtitleIsUnderline)) {
                            Text("U").font(.system(size: 14, weight: .regular)).underline()
                        }
                        .toggleStyle(.button)
                    }
                    
                    HStack(spacing: 8) {
                        Text(appState.t(.color))
                        Spacer()
                        ForEach(SubtitleColor.presets, id: \.id) { preset in
                            Button {
                                appState.updateSetting(\.subtitleColor, to: preset.color)
                            } label: {
                                Circle()
                                    .fill(preset.color.swiftUIColor)
                                    .frame(width: 16, height: 16)
                                    .overlay(
                                        Circle()
                                            .stroke(Color.primary, lineWidth: appState.settings.subtitleColor == preset.color ? 2 : 0)
                                            .frame(width: 20, height: 20)
                                    )
                            }
                            .buttonStyle(.plain)
                            .help(appState.t(preset.titleKey))
                        }
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
        .frame(width: 350, height: 550)
        .tint(.white)
        .onAppear {
            appState.refreshAvailableMicrophones()
            appState.openWindowAction = openWindow
        }
    }

    private var usageCompactView: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(appState.t(.usageControl))
                .font(.headline)

            HStack {
                Text(appState.t(.thisSessionTranslatedTime))
                Spacer()
                Text(AppState.formatUsageDuration(appState.usageSnapshot.sessionSentAudioSeconds))
                    .monospacedDigit()
                    .foregroundStyle(.secondary)
            }

            HStack {
                Text(appState.t(.todayTranslatedTime))
                Spacer()
                Text(AppState.formatUsageDuration(appState.usageSnapshot.todaySentAudioSeconds))
                    .monospacedDigit()
                    .foregroundStyle(.secondary)
            }

            Toggle(appState.t(.idleAutoPause), isOn: appState.binding(\.usageControls.idleAutoPauseEnabled))
        }
    }
}
