import AVFoundation
import AudioToolbox
import CoreAudio

final class PCM16AudioPlayer {
    nonisolated(unsafe) private let engine = AVAudioEngine()
    nonisolated(unsafe) private let player = AVAudioPlayerNode()
    private let queue = DispatchQueue(label: "livebuddy.audio.playback")
    nonisolated(unsafe) private var isPrepared = false
    nonisolated(unsafe) private var isAttached = false
    nonisolated(unsafe) private var outputDeviceUID: String?

    nonisolated func playPCM16(_ data: Data, sampleRate: Double) {
        guard !data.isEmpty else { return }
        queue.async { [weak self] in
            self?.enqueue(data, sampleRate: sampleRate)
        }
    }

    nonisolated func stop() {
        queue.async { [weak self] in
            self?.player.stop()
            self?.engine.stop()
            self?.isPrepared = false
        }
    }

    nonisolated func setVolume(_ volume: Float) {
        queue.async { [weak self] in
            self?.player.volume = volume
        }
    }

    nonisolated func setOutputDeviceUID(_ uid: String?) {
        queue.async { [weak self] in
            guard let self, self.outputDeviceUID != uid else { return }
            self.outputDeviceUID = uid
            self.player.stop()
            self.engine.stop()
            self.isPrepared = false
        }
    }

    private nonisolated func enqueue(_ data: Data, sampleRate: Double) {
        do {
            try prepare(sampleRate: sampleRate)
        } catch {
            return
        }

        guard let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: sampleRate, channels: 1, interleaved: false) else { return }
        let frameCount = AVAudioFrameCount(data.count / MemoryLayout<Int16>.size)
        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frameCount) else { return }
        buffer.frameLength = frameCount
        guard let output = buffer.floatChannelData?[0] else { return }

        data.withUnsafeBytes { rawBuffer in
            let samples = rawBuffer.bindMemory(to: Int16.self)
            for index in 0..<Int(frameCount) {
                output[index] = Float(Int16(littleEndian: samples[index])) / Float(Int16.max)
            }
        }

        player.scheduleBuffer(buffer)
        if !player.isPlaying {
            player.play()
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
        try applyOutputDeviceIfNeeded()
        try engine.start()
        isPrepared = true
    }

    private nonisolated func applyOutputDeviceIfNeeded() throws {
        guard let outputDeviceUID,
              let deviceID = AudioDeviceManager.getOutputDeviceID(for: outputDeviceUID),
              let audioUnit = engine.outputNode.audioUnit else {
            return
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
        if status != noErr {
            throw NSError(
                domain: "LiveBuddy.PCM16AudioPlayer",
                code: Int(status),
                userInfo: [NSLocalizedDescriptionKey: "Could not switch translated voice output device: \(status)"]
            )
        }
    }
}
