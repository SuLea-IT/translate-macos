import AVFoundation
import AudioToolbox
import CoreAudio
import Foundation

private enum PCM16AudioPlayerOutputError: Error {
    case outputDeviceNotFound(String)
    case defaultOutputDeviceUnavailable
    case outputAudioUnitUnavailable
    case routeChangeFailed(OSStatus)
}

enum PCM16AudioPlaybackDropReason: Sendable, CustomStringConvertible {
    case backlogLimit(Int)
    case prepareFailed(String)
    case playerShuttingDown
    case invalidAudioFormat
    case emptyAudioFrame
    case bufferAllocationFailed
    case channelDataUnavailable

    var description: String {
        switch self {
        case .backlogLimit(let limit):
            "playback queue is full (\(limit) pending buffers)"
        case .prepareFailed(let message):
            "audio output preparation failed: \(message)"
        case .playerShuttingDown:
            "audio player is shutting down"
        case .invalidAudioFormat:
            "translated audio format could not be created"
        case .emptyAudioFrame:
            "translated audio chunk had no frames"
        case .bufferAllocationFailed:
            "translated audio buffer allocation failed"
        case .channelDataUnavailable:
            "translated audio channel data was unavailable"
        }
    }
}

final class PCM16AudioPlayer: @unchecked Sendable {
    private static let playbackQueueKey = DispatchSpecificKey<Bool>()
    private static let playbackQueueValue = true
    nonisolated(unsafe) private let engine = AVAudioEngine()
    nonisolated(unsafe) private let player = AVAudioPlayerNode()
    nonisolated(unsafe) private let timePitch = AVAudioUnitTimePitch()
    private let queue = DispatchQueue(label: "livebuddy.audio.playback")
    private let maxPendingPlaybackBuffers = 120
    nonisolated(unsafe) private var isPrepared = false
    nonisolated(unsafe) private var isAttached = false
    nonisolated(unsafe) private var isShuttingDown = false
    nonisolated(unsafe) private var pendingPlaybackBuffers = 0
    nonisolated(unsafe) private var playbackGeneration = UUID()
    nonisolated(unsafe) private var selectedOutputDeviceUID: String?
    nonisolated(unsafe) private var appliedOutputDeviceUID: String?
    nonisolated(unsafe) private var playbackRate: Float = Float(AppSettings.defaultTranslationSpeechRate)
    nonisolated(unsafe) private var onPlaybackDrop: (@Sendable (PCM16AudioPlaybackDropReason) -> Void)?

    init() {
        queue.setSpecific(key: Self.playbackQueueKey, value: Self.playbackQueueValue)
    }

    deinit {
        if DispatchQueue.getSpecific(key: Self.playbackQueueKey) == Self.playbackQueueValue {
            teardownPlaybackResources()
        } else {
            queue.sync {
                teardownPlaybackResources()
            }
        }
    }

    nonisolated func playPCM16(_ data: Data, sampleRate: Double) {
        guard !data.isEmpty else { return }
        queue.async { [weak self] in
            self?.enqueue(data, sampleRate: sampleRate)
        }
    }

    nonisolated func stop() {
        queue.async { [weak self] in
            guard let self else { return }
            self.stopOnPlaybackQueue()
        }
    }

    nonisolated func setVolume(_ volume: Float) {
        queue.async { [weak self] in
            guard let self else { return }
            guard !isShuttingDown else { return }
            self.player.volume = volume
        }
    }

    nonisolated func setOutputDeviceUID(_ uid: String?) {
        let normalizedUID = uid?.trimmingCharacters(in: .whitespacesAndNewlines)
        let selectedUID = normalizedUID?.isEmpty == false ? normalizedUID : nil
        queue.async { [weak self] in
            guard let self else { return }
            guard !isShuttingDown else { return }
            guard self.selectedOutputDeviceUID != selectedUID else { return }
            self.selectedOutputDeviceUID = selectedUID
            self.stopOnPlaybackQueue()
        }
    }

    nonisolated func setPlaybackRate(_ rate: Float) {
        let clampedRate = min(
            max(rate, Float(AppSettings.translationSpeechRateRange.lowerBound)),
            Float(AppSettings.translationSpeechRateRange.upperBound)
        )
        queue.async { [weak self] in
            guard let self else { return }
            guard !isShuttingDown else { return }
            self.playbackRate = clampedRate
            self.timePitch.rate = playbackRate
        }
    }

    nonisolated func setPlaybackDropHandler(_ handler: (@Sendable (PCM16AudioPlaybackDropReason) -> Void)?) {
        queue.async { [weak self] in
            guard let self else { return }
            self.onPlaybackDrop = handler
        }
    }

    private nonisolated func enqueue(_ data: Data, sampleRate: Double) {
        guard !isShuttingDown else {
            notifyPlaybackDrop(.playerShuttingDown)
            return
        }
        guard pendingPlaybackBuffers < maxPendingPlaybackBuffers else {
            notifyPlaybackDrop(.backlogLimit(maxPendingPlaybackBuffers))
            return
        }
        do {
            try prepare(sampleRate: sampleRate)
        } catch {
            notifyPlaybackDrop(.prepareFailed(error.localizedDescription))
            return
        }

        guard let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: sampleRate, channels: 1, interleaved: false) else {
            notifyPlaybackDrop(.invalidAudioFormat)
            return
        }
        let frameCount = AVAudioFrameCount(data.count / MemoryLayout<Int16>.size)
        guard frameCount > 0 else {
            notifyPlaybackDrop(.emptyAudioFrame)
            return
        }
        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frameCount) else {
            notifyPlaybackDrop(.bufferAllocationFailed)
            return
        }
        buffer.frameLength = frameCount
        guard let output = buffer.floatChannelData?[0] else {
            notifyPlaybackDrop(.channelDataUnavailable)
            return
        }

        data.withUnsafeBytes { rawBuffer in
            let samples = rawBuffer.bindMemory(to: Int16.self)
            for index in 0..<Int(frameCount) {
                output[index] = Float(Int16(littleEndian: samples[index])) / Float(Int16.max)
            }
        }

        let generation = playbackGeneration
        pendingPlaybackBuffers += 1
        player.scheduleBuffer(buffer, completionHandler: { [weak self] in
            self?.finishBufferPlayback(generation: generation)
        })
        if !player.isPlaying {
            player.play()
        }
    }

    private nonisolated func stopOnPlaybackQueue() {
        playbackGeneration = UUID()
        pendingPlaybackBuffers = 0
        player.stop()
        player.reset()
        engine.stop()
        isPrepared = false
    }

    private nonisolated func teardownPlaybackResources() {
        isShuttingDown = true
        stopOnPlaybackQueue()
        if isAttached {
            engine.detach(timePitch)
            engine.detach(player)
            isAttached = false
        }
    }

    private nonisolated func finishBufferPlayback(generation: UUID) {
        queue.async { [weak self] in
            guard let self else { return }
            guard self.playbackGeneration == generation else { return }
            self.pendingPlaybackBuffers = max(0, self.pendingPlaybackBuffers - 1)
        }
    }

    private nonisolated func notifyPlaybackDrop(_ reason: PCM16AudioPlaybackDropReason) {
        onPlaybackDrop?(reason)
    }

    private nonisolated func prepare(sampleRate: Double) throws {
        guard !isPrepared else { return }
        if !isAttached {
            engine.attach(player)
            engine.attach(timePitch)
            isAttached = true
        }
        guard let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: sampleRate, channels: 1, interleaved: false) else { return }
        timePitch.rate = playbackRate
        engine.disconnectNodeOutput(player)
        engine.disconnectNodeOutput(timePitch)
        engine.connect(player, to: timePitch, format: format)
        engine.connect(timePitch, to: engine.mainMixerNode, format: format)
        try applyOutputDeviceIfNeeded()
        try engine.start()
        isPrepared = true
    }

    private nonisolated func applyOutputDeviceIfNeeded() throws {
        guard appliedOutputDeviceUID != selectedOutputDeviceUID else { return }
        let deviceID: AudioDeviceID
        if let uid = selectedOutputDeviceUID {
            guard let selectedDeviceID = AudioDeviceManager.getOutputDeviceID(for: uid) else {
                throw PCM16AudioPlayerOutputError.outputDeviceNotFound(uid)
            }
            deviceID = selectedDeviceID
        } else {
            guard let defaultDeviceID = AudioDeviceManager.getDefaultOutputDeviceID() else {
                throw PCM16AudioPlayerOutputError.defaultOutputDeviceUnavailable
            }
            deviceID = defaultDeviceID
        }

        guard let audioUnit = engine.outputNode.audioUnit else {
            throw PCM16AudioPlayerOutputError.outputAudioUnitUnavailable
        }
        var mutableDeviceID = deviceID
        let status = AudioUnitSetProperty(
            audioUnit,
            kAudioOutputUnitProperty_CurrentDevice,
            kAudioUnitScope_Global,
            0,
            &mutableDeviceID,
            UInt32(MemoryLayout<AudioDeviceID>.size)
        )
        guard status == noErr else {
            throw PCM16AudioPlayerOutputError.routeChangeFailed(status)
        }
        appliedOutputDeviceUID = selectedOutputDeviceUID
    }
}
