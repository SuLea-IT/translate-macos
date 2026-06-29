# Live Translate Buddy 

LiveBuddy is a modern, native macOS application designed to provide real-time audio translation and captioning. It captures system/app audio (using macOS's native **ScreenCaptureKit**) and/or microphone input, streams the downsampled audio to the **Google Gemini Live API** over a bidirectional WebSocket, and displays live subtitles in a floating HUD overlay. It also plays back the translated speech returned by the Gemini model in real time.

> **二次开发说明 / Attribution**  
> 本仓库由 [SuLea-IT](https://github.com/SuLea-IT) 在 [IFA-AP-01/gemini-live-translate-macos](https://github.com/IFA-AP-01/gemini-live-translate-macos) 基础上进行二次开发、维护和发布。原始项目作者为 [Huynh Ngoc Huy / huyhunhngc](https://github.com/huyhunhngc)。  
> This repository is a secondary-development version based on the original [`IFA-AP-01/gemini-live-translate-macos`](https://github.com/IFA-AP-01/gemini-live-translate-macos) project, with attribution retained here while the current repository is maintained by [SuLea-IT](https://github.com/SuLea-IT).


https://github.com/user-attachments/assets/a5f94b11-80bf-4043-bbfc-63426b781863


---

## Key Features

*   **Real-time Speech-to-Speech & Speech-to-Text Translation**: Leverages Google Gemini's live translation capability (`models/gemini-3.5-live-translate-preview`) via low-latency bidirectional WebSockets.
*   **Source Language Awareness**: Defaults to automatic source-language detection, shows detected input language in the HUD, and lets users choose a source-language hint when needed.
*   **Usage Control**: Shows this-session/today translated audio time, supports idle auto-pause with local monitoring and pre-roll buffering, and lets users set per-session or daily usage limits.
*   **Terminology Glossary**: Add source terms and preferred translations to preserve names, product names, and technical terms. Leave the preferred translation empty to preserve the original term. Import public terminology sources such as Microsoft Terminology, paste custom HTTPS glossary links, or import local CSV/TSV/TBX/XML/TXT/ZIP files with bounded parsing and duplicate skipping.
*   **Dual-Source Audio Capture**:
    *   **Screen Audio**: Captures system/app output audio directly.
    *   **Microphone**: Captures local voice input.
    *   **Combined Source**: Captures and translates both inputs simultaneously.
*   **HUD Caption Window**:
    *   Borderless, floating, transparent overlay window that stays on top of other applications.
    *   Select translated-only, original-only, or original + translated bilingual subtitle display.
    *   Auto-hiding interactive settings bar (triggered on hover) to easily pause/play, mute/unmute, adjust volumes, or change transparency.
    *   Position and window size are automatically saved and restored.
    *   Smooth animated text scrolling to match speech timing.
*   **Highly Customizable Styles**: Fully customize the caption aesthetics from the Settings window:
    *   *Font Family*: Select between Avenir, Georgia, Helvetica Neue, Menlo, Futura, and more.
    *   *Font Size*: Adjustable slider from 14pt to 60pt.
    *   *Weight/Style*: Underline, Bold, and Italic modifiers.
    *   *Colors*: Preset options including White, Yellow, Cyan, Green, Orange, and Pink.
*   **Transcript History & Management**:
    *   Browse previously recorded sessions.
    *   Detailed statistics: Duration, line count, word count, audio source, and translation language.
    *   Search transcript contents or copy full transcripts/individual lines directly to the clipboard.
    *   Export transcripts as SRT, WebVTT, Markdown, or plain text for subtitle editors, web players, notes, and sharing.
    *   Generate local meeting notes from saved transcripts, including summary, key points, action items, and timeline, with copy/export support.
*   **Diagnostics & Runtime Logs**: Embedded log view monitoring connection status, audio capture format detection, and WebSocket status in real time.
*   **Preflight Test Page**: Run a one-click diagnostic for API key, permissions, selected audio input, and subtitle window rendering before starting a real translation session.
*   **Actionable Diagnostics**: Translates provider, network, permission, capture, and storage failures into clear messages with next-step recovery actions.
*   **Automatic Connection Recovery**: Reconnects transient Gemini Live WebSocket interruptions with capped exponential backoff while keeping the current capture/transcript session alive. Audio is not buffered during reconnects, avoiding memory growth.
*   **Custom Global Shortcuts**: Record, clear, and reset macOS-wide shortcuts for starting translation, showing captions, and muting translated audio.
*   **Global Shortcuts**:
    *   `⌃⌥⌘T`: Start / stop translation from anywhere in macOS.
    *   `⌃⌥⌘C`: Show the caption window.
    *   `⌃⌥⌘M`: Mute / unmute translated audio playback.

---

## Architecture & Audio Pipeline

LiveBuddy uses a modular architecture combining modern macOS system APIs and WebSockets:

```
                  ┌────────────────────────┐
                  │   ScreenCaptureKit     │ (System Audio)
                  └───────────┬────────────┘
                              │ Float32 / Int16 (Multi-channel)
                              ▼
┌─────────────────┐     ┌───────────┐     ┌────────────────┐     ┌─────────────────────┐
│  AVAudioEngine  ├────►│Chunky mono├────►│ PCM16          ├────►│   Gemini Live API   │
└─────────────────┘     │downsampler│     │16kHz PCM chunk │     │ (Bidi WebSocket)    │
(Microphone Audio)      └───────────┘     └────────────────┘     └──────────┬──────────┘
                                                                            │
                                                                            │ Translated Audio / Subtitles
                                                                            ▼
┌─────────────────┐     ┌───────────┐     ┌────────────────┐     ┌─────────────────────┐
│ Floating Subtitle│◄────┤  App State├◄────┤  AVAudioPlayer ├◄────┤   UI Updates &      │
│     Overlay     │     │Controller │     │  Playback Node │     │   JSON Parsing      │
└─────────────────┘     └───────────┘     └────────────────┘     └─────────────────────┘
```

### 1. Audio Capture & Processing (`Services/` & `Utilities/`)
*   **`MicrophoneCapture`**: Uses `AVAudioEngine` to tap the microphone, requesting permission at runtime.
*   **`ScreenAudioCapture`**: Interfaces with `ScreenCaptureKit` (`SCStream`) to capture system audio while excluding LiveBuddy's own output to prevent loopback/feedback.
*   **`PCM16Downsampler`**: Converts captured audio (typically multi-channel Float32 at 44.1kHz/48kHz) down to the `audio/pcm;rate=16000` mono format required by Gemini.
*   **`PCM16Chunker`**: Pools the downsampled PCM stream and pushes chunks to the WebSocket client in optimal sizes.

### 2. WebSocket Client (`Services/`)
*   **`GeminiLiveTranslateClient`**: Manages the bidirectional `URLSessionWebSocketTask` session communicating with `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent`.
*   Supports live system instructions, target language codes, and toggling target language audio echo.

### 3. Audio Playback (`Utilities/`)
*   **`PCM16AudioPlayer`**: Uses `AVAudioEngine` and `AVAudioPlayerNode` to schedule and play the translated incoming `Float32` PCM audio samples generated by Gemini.

---

## Prerequisites & Setup

### Requirements
*   **macOS 13.0+** (ScreenCaptureKit requires Ventura or later).
*   **Xcode 15.0+** to compile the Swift project.


### Free macOS Download / 免费安装说明

Prebuilt free macOS packages are published on [GitHub Releases](https://github.com/SuLea-IT/translate-macos/releases). Download the DMG first; use the ZIP only as a fallback.

This project does not require a paid Apple Developer Program membership for free builds. Release artifacts are ad-hoc signed but not Apple-notarized. On first launch macOS may show an “unidentified developer” warning. If that happens:

1. Drag `Live Translate Buddy.app` to Applications.
2. Right-click `Live Translate Buddy.app`.
3. Choose **Open**.
4. Click **Open** again in the confirmation dialog.

Inside the app, open Settings → Updates → **Check for Updates** to jump to the latest GitHub Releases page.

### Setup Instructions

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/<your-username>/LiveBuddy.git
    cd LiveBuddy
    ```
2.  **Open in Xcode**:
    Open `LiveBuddy.xcodeproj` in Xcode.
3.  **Configure API Key**:
    *   Obtain a Gemini API key from [Google AI Studio](https://aistudio.google.com/).
    *   Launch LiveBuddy. On first launch, a setup sheet will prompt you to enter the **Google Gemini API Key**.
4.  **Permissions**:
    *   **Microphone Access**: When selecting the Microphone audio source, grant permissions when prompted.
    *   **Screen Recording / Audio Capture**: ScreenCaptureKit requires Screen Recording permission on macOS. Make sure to enable this in *System Settings > Privacy & Security > Screen Recording* for LiveBuddy.

### First-Run Checklist

LiveBuddy shows a setup checklist before starting translation. It checks the Gemini API key, microphone permission, and screen recording permission needed by the selected audio source. Permission status is refreshed on app launch, settings open, start preflight, or when you click **Refresh Status**; LiveBuddy does not continuously poll permissions in the background.

### Secure API Key Storage

LiveBuddy stores the Gemini API key in macOS Keychain. Existing keys from older `settings.json` files are migrated to Keychain on launch, and new settings saves omit the API key from JSON.

## Configuration & Customization

The app provides deep customization parameters through **Settings**:

| Category | Option | Description |
| :--- | :--- | :--- |
| **Interface** | Interface Language | Switch LiveBuddy's UI between English, Simplified Chinese, Japanese, Korean, Spanish, French, German, and Vietnamese. |
| **API Provider** | API Key & System Prompt | Set up your credentials and custom instructions for translation behavior. |
| **Translation** | Translate From | Use Auto Detect by default or choose a source-language hint for more predictable translation. |
| **Translation** | Translate To | Choose between dozens of target languages (e.g., Vietnamese, Spanish, French, Japanese). |
| **Translation** | Terminology glossary | Add source terms and preferred translations; leave the target empty to preserve the original term. |
| **Translation** | Subtitle display | Show translated only, original only, or original + translated bilingual subtitles in the HUD. |
| **Translation** | Echo target language | Toggles voice playback of the translated translation output. |
| **Translation** | Translation volume | Control or mute the translation playback speaker output. |
| **Translation** | Usage control | Track translated audio seconds, auto-pause on idle while monitoring locally, and enforce per-session/daily limits. |
| **Transcripts** | Export formats | Save a transcript as SRT, WebVTT, Markdown, or TXT from the transcript detail view. |
| **Transcripts** | Meeting notes | Generate local extractive meeting notes with summary, key points, action items, and timeline from saved transcript detail views. |
| **Diagnostics** | Preflight test | Checks API key, permissions, microphone/screen audio levels, and subtitle window rendering without starting Gemini or saving transcripts. |
| **Diagnostics** | Actionable error guidance | Shows the latest issue with a clear explanation, recovery hint, and one-click action where available. |
| **Global Shortcuts** | Custom shortcuts | Toggle macOS-wide shortcuts, record custom bindings for each action, clear conflicts, or restore defaults. |
| **Runtime** | Automatic reconnect | Recovers transient Gemini Live disconnects with capped exponential backoff; manual Stop cancels recovery. |
| **Caption Overlay**| Background Opacity | Adjust HUD transparency slider from 15% to 95%. |
| **Subtitle Style** | Font Family | Standard and customized typefaces (Helvetica, Georgia, Avenir, Georgia, etc.). |
| **Subtitle Style** | Font Size & Modifiers| Font size (14–60pt), Bold, Italic, and Underline formatting. |
| **Subtitle Style** | Text Color | Presets for color choices (White, Yellow, Cyan, Green, etc.). |

---

##

 License

This project is licensed under the MIT License - see the LICENSE file for details.
