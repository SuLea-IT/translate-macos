import Foundation
import AppKit

enum AudioSource: String, CaseIterable, Codable, Identifiable {
    case screen
    case microphone
    case both

    var id: String { rawValue }

    var title: String {
        switch self {
        case .screen: "Screen audio"
        case .microphone: "Microphone"
        case .both: "Screen + Mic"
        }
    }
}

enum AudioPlaybackMode: String, CaseIterable, Codable, Identifiable {
    case mediaAndTranslation
    case mediaOnly
    case translationOnly

    var id: String { rawValue }

    var allowsTranslatedAudio: Bool {
        self != .mediaOnly
    }
}

enum AIProvider: String, CaseIterable, Codable, Identifiable {
    case gemini
    
    var id: String { rawValue }
    var title: String {
        switch self {
        case .gemini: return "Google Gemini"
        }
    }
}

struct TranslationLanguage: Identifiable, Hashable {
    let id: String
    let name: String

    func localizedName(language: InterfaceLanguage) -> String {
        if let localized = Locale(identifier: language.localeIdentifier)
            .localizedString(forLanguageCode: id)?
            .trimmingCharacters(in: .whitespacesAndNewlines),
           !localized.isEmpty {
            return localized
        }
        return name
    }
}

extension TranslationLanguage {
    static let all: [TranslationLanguage] = [
        .init(id: "af", name: "Afrikaans"),
        .init(id: "sq", name: "Albanian"),
        .init(id: "am", name: "Amharic"),
        .init(id: "ar", name: "Arabic"),
        .init(id: "hy", name: "Armenian"),
        .init(id: "az", name: "Azerbaijani"),
        .init(id: "eu", name: "Basque"),
        .init(id: "be", name: "Belarusian"),
        .init(id: "bn", name: "Bengali"),
        .init(id: "bs", name: "Bosnian"),
        .init(id: "bg", name: "Bulgarian"),
        .init(id: "ca", name: "Catalan"),
        .init(id: "ceb", name: "Cebuano"),
        .init(id: "zh", name: "Chinese"),
        .init(id: "hr", name: "Croatian"),
        .init(id: "cs", name: "Czech"),
        .init(id: "da", name: "Danish"),
        .init(id: "nl", name: "Dutch"),
        .init(id: "en", name: "English"),
        .init(id: "eo", name: "Esperanto"),
        .init(id: "et", name: "Estonian"),
        .init(id: "fi", name: "Finnish"),
        .init(id: "fr", name: "French"),
        .init(id: "gl", name: "Galician"),
        .init(id: "ka", name: "Georgian"),
        .init(id: "de", name: "German"),
        .init(id: "el", name: "Greek"),
        .init(id: "gu", name: "Gujarati"),
        .init(id: "ht", name: "Haitian Creole"),
        .init(id: "ha", name: "Hausa"),
        .init(id: "he", name: "Hebrew"),
        .init(id: "hi", name: "Hindi"),
        .init(id: "hmn", name: "Hmong"),
        .init(id: "hu", name: "Hungarian"),
        .init(id: "is", name: "Icelandic"),
        .init(id: "ig", name: "Igbo"),
        .init(id: "id", name: "Indonesian"),
        .init(id: "ga", name: "Irish"),
        .init(id: "it", name: "Italian"),
        .init(id: "ja", name: "Japanese"),
        .init(id: "jv", name: "Javanese"),
        .init(id: "kn", name: "Kannada"),
        .init(id: "kk", name: "Kazakh"),
        .init(id: "km", name: "Khmer"),
        .init(id: "ko", name: "Korean"),
        .init(id: "ku", name: "Kurdish"),
        .init(id: "ky", name: "Kyrgyz"),
        .init(id: "lo", name: "Lao"),
        .init(id: "la", name: "Latin"),
        .init(id: "lv", name: "Latvian"),
        .init(id: "lt", name: "Lithuanian"),
        .init(id: "mk", name: "Macedonian"),
        .init(id: "mg", name: "Malagasy"),
        .init(id: "ms", name: "Malay"),
        .init(id: "ml", name: "Malayalam"),
        .init(id: "mt", name: "Maltese"),
        .init(id: "mi", name: "Maori"),
        .init(id: "mr", name: "Marathi"),
        .init(id: "mn", name: "Mongolian"),
        .init(id: "my", name: "Myanmar"),
        .init(id: "ne", name: "Nepali"),
        .init(id: "no", name: "Norwegian"),
        .init(id: "ps", name: "Pashto"),
        .init(id: "fa", name: "Persian"),
        .init(id: "pl", name: "Polish"),
        .init(id: "pt", name: "Portuguese"),
        .init(id: "pa", name: "Punjabi"),
        .init(id: "ro", name: "Romanian"),
        .init(id: "ru", name: "Russian"),
        .init(id: "sm", name: "Samoan"),
        .init(id: "sr", name: "Serbian"),
        .init(id: "st", name: "Sesotho"),
        .init(id: "sn", name: "Shona"),
        .init(id: "sd", name: "Sindhi"),
        .init(id: "si", name: "Sinhala"),
        .init(id: "sk", name: "Slovak"),
        .init(id: "sl", name: "Slovenian"),
        .init(id: "so", name: "Somali"),
        .init(id: "es", name: "Spanish"),
        .init(id: "su", name: "Sundanese"),
        .init(id: "sw", name: "Swahili"),
        .init(id: "sv", name: "Swedish"),
        .init(id: "tl", name: "Tagalog"),
        .init(id: "tg", name: "Tajik"),
        .init(id: "ta", name: "Tamil"),
        .init(id: "te", name: "Telugu"),
        .init(id: "th", name: "Thai"),
        .init(id: "tr", name: "Turkish"),
        .init(id: "uk", name: "Ukrainian"),
        .init(id: "ur", name: "Urdu"),
        .init(id: "uz", name: "Uzbek"),
        .init(id: "vi", name: "Vietnamese"),
        .init(id: "cy", name: "Welsh"),
        .init(id: "xh", name: "Xhosa"),
        .init(id: "yi", name: "Yiddish"),
        .init(id: "yo", name: "Yoruba"),
        .init(id: "zu", name: "Zulu")
    ]

    static func name(for code: String) -> String {
        all.first { $0.id == code }?.name ?? code
    }

    static func name(for code: String, language: InterfaceLanguage) -> String {
        all.first { $0.id == code }?.localizedName(language: language) ?? code
    }
}

enum SubtitleFontName: String, CaseIterable, Codable, Identifiable {
    case system = "System"
    case helveticaNeue = "Helvetica Neue"
    case avenir = "Avenir"
    case georgia = "Georgia"
    case futura = "Futura"
    case palatino = "Palatino"
    case menlo = "Menlo"
    case courierNew = "Courier New"
    case timesNewRoman = "Times New Roman"
    case arial = "Arial"

    var id: String { rawValue }
    var displayName: String { rawValue }

    func nsFont(size: CGFloat, bold: Bool, italic: Bool) -> NSFont {
        if self == .system {
            let weight: NSFont.Weight = bold ? .bold : .regular
            let base = NSFont.systemFont(ofSize: size, weight: weight)
            if italic {
                return NSFontManager.shared.convert(base, toHaveTrait: .italicFontMask)
            }
            return base
        }

        var traits: NSFontTraitMask = []
        if bold { traits.insert(.boldFontMask) }
        if italic { traits.insert(.italicFontMask) }

        if let font = NSFontManager.shared.font(withFamily: rawValue, traits: traits, weight: bold ? 9 : 5, size: size) {
            return font
        }
        return NSFont.systemFont(ofSize: size, weight: bold ? .bold : .regular)
    }
}

struct SubtitleColor: Codable, Equatable, Hashable {
    var red: Double
    var green: Double
    var blue: Double
    var alpha: Double

    static let white = SubtitleColor(red: 1, green: 1, blue: 1, alpha: 1)
    static let yellow = SubtitleColor(red: 1, green: 1, blue: 0, alpha: 1)
    static let cyan = SubtitleColor(red: 0, green: 1, blue: 1, alpha: 1)
    static let green = SubtitleColor(red: 0.2, green: 1, blue: 0.4, alpha: 1)
    static let orange = SubtitleColor(red: 1, green: 0.6, blue: 0, alpha: 1)
    static let pink = SubtitleColor(red: 1, green: 0.4, blue: 0.7, alpha: 1)

    var nsColor: NSColor {
        NSColor(red: red, green: green, blue: blue, alpha: alpha)
    }

    var swiftUIColor: Color {
        Color(red: red, green: green, blue: blue, opacity: alpha)
    }

    static let presets: [(id: String, titleKey: InterfaceText, color: SubtitleColor)] = [
        ("white", .subtitleColorWhite, .white),
        ("yellow", .subtitleColorYellow, .yellow),
        ("cyan", .subtitleColorCyan, .cyan),
        ("green", .subtitleColorGreen, .green),
        ("orange", .subtitleColorOrange, .orange),
        ("pink", .subtitleColorPink, .pink),
    ]
}

import SwiftUI

struct AppSettings: Codable, Equatable {
    static let translationSpeechRateRange: ClosedRange<Double> = 1.0...1.6
    static let defaultTranslationSpeechRate = 1.15

    var activeProvider: AIProvider = .gemini
    var apiKey = ""
    var interfaceLanguage: InterfaceLanguage = .english
    var sourceLanguageCode: String? = nil
    var targetLanguageCode: String = {
        let code = Locale.current.language.languageCode?.identifier ?? "vi"
        return TranslationLanguage.all.contains(where: { $0.id == code }) ? code : "vi"
    }()
    var userPrompt = "Translate the incoming speech naturally. Keep names, code terms, and product names intact."
    var glossaryEntries: [GlossaryEntry] = []
    var audioSource: AudioSource = .screen
    var selectedMicrophoneDeviceUID: String? = nil
    var backgroundOpacity = 0.68
    var echoTargetLanguage = true
    var subtitleScreenFrame: SubtitleScreenFrame?
    var subtitleDisplayMode: SubtitleDisplayMode = .translated
    var globalShortcutsEnabled = true
    var globalShortcuts: GlobalShortcutSet = .defaults
    var usageControls = LiveUsageSettings()

    // Audio Player
    var audioPlayerVolume: Double = 1.0
    var audioPlayerMuted: Bool = false
    var audioPlaybackMode: AudioPlaybackMode = .mediaAndTranslation
    var translationAudioOutputDeviceUID: String? = nil
    var translationSpeechRate: Double = Self.defaultTranslationSpeechRate

    // Subtitle styling
    var subtitleFontSize: Double = 28
    var subtitleFontName: SubtitleFontName = .system
    var subtitleIsBold: Bool = true
    var subtitleIsItalic: Bool = false
    var subtitleIsUnderline: Bool = false
    var subtitleColor: SubtitleColor = .white

    init() {}

    private enum CodingKeys: String, CodingKey {
        case activeProvider
        case apiKey
        case interfaceLanguage
        case sourceLanguageCode
        case targetLanguageCode
        case userPrompt
        case glossaryEntries
        case audioSource
        case selectedMicrophoneDeviceUID
        case backgroundOpacity
        case echoTargetLanguage
        case subtitleScreenFrame
        case subtitleDisplayMode
        case globalShortcutsEnabled
        case globalShortcuts
        case usageControls
        case audioPlayerVolume
        case audioPlayerMuted
        case audioPlaybackMode
        case translationAudioOutputDeviceUID
        case translationSpeechRate
        case subtitleFontSize
        case subtitleFontName
        case subtitleIsBold
        case subtitleIsItalic
        case subtitleIsUnderline
        case subtitleColor
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let defaults = AppSettings()

        activeProvider = try container.decodeIfPresent(AIProvider.self, forKey: .activeProvider) ?? defaults.activeProvider
        apiKey = try container.decodeIfPresent(String.self, forKey: .apiKey) ?? defaults.apiKey
        interfaceLanguage = try container.decodeIfPresent(InterfaceLanguage.self, forKey: .interfaceLanguage) ?? defaults.interfaceLanguage
        sourceLanguageCode = try container.decodeIfPresent(String.self, forKey: .sourceLanguageCode)
        targetLanguageCode = try container.decodeIfPresent(String.self, forKey: .targetLanguageCode) ?? defaults.targetLanguageCode
        userPrompt = try container.decodeIfPresent(String.self, forKey: .userPrompt) ?? defaults.userPrompt
        glossaryEntries = try container.decodeIfPresent([GlossaryEntry].self, forKey: .glossaryEntries) ?? defaults.glossaryEntries
        audioSource = try container.decodeIfPresent(AudioSource.self, forKey: .audioSource) ?? defaults.audioSource
        selectedMicrophoneDeviceUID = try container.decodeIfPresent(String.self, forKey: .selectedMicrophoneDeviceUID)
        backgroundOpacity = try container.decodeIfPresent(Double.self, forKey: .backgroundOpacity) ?? defaults.backgroundOpacity
        echoTargetLanguage = try container.decodeIfPresent(Bool.self, forKey: .echoTargetLanguage) ?? defaults.echoTargetLanguage
        subtitleScreenFrame = try container.decodeIfPresent(SubtitleScreenFrame.self, forKey: .subtitleScreenFrame)
        subtitleDisplayMode = try container.decodeIfPresent(SubtitleDisplayMode.self, forKey: .subtitleDisplayMode) ?? defaults.subtitleDisplayMode
        globalShortcutsEnabled = try container.decodeIfPresent(Bool.self, forKey: .globalShortcutsEnabled) ?? defaults.globalShortcutsEnabled
        globalShortcuts = try container.decodeIfPresent(GlobalShortcutSet.self, forKey: .globalShortcuts) ?? defaults.globalShortcuts
        usageControls = try container.decodeIfPresent(LiveUsageSettings.self, forKey: .usageControls) ?? defaults.usageControls
        audioPlayerVolume = try container.decodeIfPresent(Double.self, forKey: .audioPlayerVolume) ?? defaults.audioPlayerVolume
        audioPlayerMuted = try container.decodeIfPresent(Bool.self, forKey: .audioPlayerMuted) ?? defaults.audioPlayerMuted
        audioPlaybackMode = try container.decodeIfPresent(AudioPlaybackMode.self, forKey: .audioPlaybackMode) ?? defaults.audioPlaybackMode
        translationAudioOutputDeviceUID = try container.decodeIfPresent(String.self, forKey: .translationAudioOutputDeviceUID)
        translationSpeechRate = Self.clampedTranslationSpeechRate(try container.decodeIfPresent(Double.self, forKey: .translationSpeechRate) ?? defaults.translationSpeechRate)
        subtitleFontSize = try container.decodeIfPresent(Double.self, forKey: .subtitleFontSize) ?? defaults.subtitleFontSize
        subtitleFontName = try container.decodeIfPresent(SubtitleFontName.self, forKey: .subtitleFontName) ?? defaults.subtitleFontName
        subtitleIsBold = try container.decodeIfPresent(Bool.self, forKey: .subtitleIsBold) ?? defaults.subtitleIsBold
        subtitleIsItalic = try container.decodeIfPresent(Bool.self, forKey: .subtitleIsItalic) ?? defaults.subtitleIsItalic
        subtitleIsUnderline = try container.decodeIfPresent(Bool.self, forKey: .subtitleIsUnderline) ?? defaults.subtitleIsUnderline
        subtitleColor = try container.decodeIfPresent(SubtitleColor.self, forKey: .subtitleColor) ?? defaults.subtitleColor
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(activeProvider, forKey: .activeProvider)
        try container.encode(interfaceLanguage, forKey: .interfaceLanguage)
        try container.encodeIfPresent(sourceLanguageCode, forKey: .sourceLanguageCode)
        try container.encode(targetLanguageCode, forKey: .targetLanguageCode)
        try container.encode(userPrompt, forKey: .userPrompt)
        try container.encode(glossaryEntries, forKey: .glossaryEntries)
        try container.encode(audioSource, forKey: .audioSource)
        try container.encodeIfPresent(selectedMicrophoneDeviceUID, forKey: .selectedMicrophoneDeviceUID)
        try container.encode(backgroundOpacity, forKey: .backgroundOpacity)
        try container.encode(echoTargetLanguage, forKey: .echoTargetLanguage)
        try container.encodeIfPresent(subtitleScreenFrame, forKey: .subtitleScreenFrame)
        try container.encode(subtitleDisplayMode, forKey: .subtitleDisplayMode)
        try container.encode(globalShortcutsEnabled, forKey: .globalShortcutsEnabled)
        try container.encode(globalShortcuts, forKey: .globalShortcuts)
        try container.encode(usageControls, forKey: .usageControls)
        try container.encode(audioPlayerVolume, forKey: .audioPlayerVolume)
        try container.encode(audioPlayerMuted, forKey: .audioPlayerMuted)
        try container.encode(audioPlaybackMode, forKey: .audioPlaybackMode)
        try container.encodeIfPresent(translationAudioOutputDeviceUID, forKey: .translationAudioOutputDeviceUID)
        try container.encode(translationSpeechRate, forKey: .translationSpeechRate)
        try container.encode(subtitleFontSize, forKey: .subtitleFontSize)
        try container.encode(subtitleFontName, forKey: .subtitleFontName)
        try container.encode(subtitleIsBold, forKey: .subtitleIsBold)
        try container.encode(subtitleIsItalic, forKey: .subtitleIsItalic)
        try container.encode(subtitleIsUnderline, forKey: .subtitleIsUnderline)
        try container.encode(subtitleColor, forKey: .subtitleColor)
    }

    func requiresSettingsFileSave(comparedTo other: AppSettings) -> Bool {
        var current = self
        var comparison = other
        current.apiKey = ""
        comparison.apiKey = ""
        return current != comparison
    }

    static func clampedTranslationSpeechRate(_ rate: Double) -> Double {
        min(max(rate, translationSpeechRateRange.lowerBound), translationSpeechRateRange.upperBound)
    }

    func requiresSessionRestart(comparedTo other: AppSettings) -> Bool {
        activeProvider != other.activeProvider
            || apiKey != other.apiKey
            || sourceLanguageCode != other.sourceLanguageCode
            || targetLanguageCode != other.targetLanguageCode
            || userPrompt != other.userPrompt
            || glossaryEntries != other.glossaryEntries
            || audioSource != other.audioSource
            || echoTargetLanguage != other.echoTargetLanguage
            || selectedMicrophoneDeviceUID != other.selectedMicrophoneDeviceUID
    }
}

struct SubtitleScreenFrame: Codable, Equatable {
    var x: Double
    var y: Double
    var width: Double
    var height: Double
}
