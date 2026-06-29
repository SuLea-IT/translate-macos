import AVFoundation
import Foundation

final class PCM16AudioPlayer: @unchecked Sendable {
    nonisolated(unsafe) private let engine = AVAudioEngine()
    nonisolated(unsafe) private let player = AVAudioPlayerNode()
    private let queue = DispatchQueue(label: "livebuddy.audio.playback")
    private let maxPendingPlaybackBuffers = 120
    nonisolated(unsafe) private var isPrepared = false
    nonisolated(unsafe) private var isAttached = false
    nonisolated(unsafe) private var pendingPlaybackBuffers = 0
    nonisolated(unsafe) private var playbackGeneration = UUID()

    deinit {
        player.stop()
        player.reset()
        engine.stop()
        isPrepared = false
        pendingPlaybackBuffers = 0
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
            playbackGeneration = UUID()
            pendingPlaybackBuffers = 0
            player.stop()
            player.reset()
            engine.stop()
            isPrepared = false
        }
    }

    nonisolated func setVolume(_ volume: Float) {
        queue.async { [weak self] in
            self?.player.volume = volume
        }
    }

    private nonisolated func enqueue(_ data: Data, sampleRate: Double) {
        guard pendingPlaybackBuffers < maxPendingPlaybackBuffers else { return }
        do {
            try prepare(sampleRate: sampleRate)
        } catch {
            return
        }

        guard let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: sampleRate, channels: 1, interleaved: false) else { return }
        let frameCount = AVAudioFrameCount(data.count / MemoryLayout<Int16>.size)
        guard frameCount > 0 else { return }
        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frameCount) else { return }
        buffer.frameLength = frameCount
        guard let output = buffer.floatChannelData?[0] else { return }

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

    private nonisolated func finishBufferPlayback(generation: UUID) {
        queue.async { [weak self] in
            guard let self else { return }
            guard self.playbackGeneration == generation else { return }
            self.pendingPlaybackBuffers = max(0, self.pendingPlaybackBuffers - 1)
        }
    }

    private nonisolated func prepare(sampleRate: Double) throws {
        guard !isPrepared else { return }
        if !isAttached {
            engine.attach(player)
            isAttached = true
        }
        guard let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: sampleRate, channels: 1, interleaved: false) else { return }
        engine.disconnectNodeOutput(player)
        engine.connect(player, to: engine.mainMixerNode, format: format)
        try engine.start()
        isPrepared = true
    }
}
