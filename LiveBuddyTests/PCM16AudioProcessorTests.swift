import Foundation
import Testing
@testable import LiveBuddy

private final class PCM16ChunkerReentryProbe: @unchecked Sendable {
    private let lock = NSLock()
    private var emittedChunks = 0
    var chunker: PCM16Chunker?

    var emittedCount: Int {
        lock.lock()
        defer { lock.unlock() }
        return emittedChunks
    }

    func handleChunk(_ chunk: Data) {
        guard !chunk.isEmpty else { return }
        chunker?.reset()
        lock.lock()
        emittedChunks += 1
        lock.unlock()
    }
}

private final class PCM16ChunkerReentryHarness: @unchecked Sendable {
    let probe: PCM16ChunkerReentryProbe
    let chunker: PCM16Chunker

    init() {
        let probe = PCM16ChunkerReentryProbe()
        let chunker = PCM16Chunker { chunk in
            probe.handleChunk(chunk)
        }
        probe.chunker = chunker
        self.probe = probe
        self.chunker = chunker
    }

    func appendOneChunkAndResetFromCallback() {
        chunker.append(Data(repeating: 1, count: 3_200))
    }
}

struct PCM16AudioProcessorTests {
    @Test func chunkerAllowsCallbackToResetPendingBuffer() {
        let harness = PCM16ChunkerReentryHarness()

        harness.appendOneChunkAndResetFromCallback()
        #expect(harness.probe.emittedCount == 1)
    }
}
