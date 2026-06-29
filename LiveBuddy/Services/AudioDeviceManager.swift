import Foundation
import CoreAudio

struct AudioDevice: Identifiable, Hashable, Codable {
    var id: AudioDeviceID {
        deviceID
    }
    let deviceID: AudioDeviceID
    let uid: String
    let name: String

    var idString: String {
        uid
    }
}

final class AudioDeviceManager {
    static func getInputDevices() -> [AudioDevice] {
        getDevices(scope: kAudioDevicePropertyScopeInput)
    }

    static func getOutputDevices() -> [AudioDevice] {
        getDevices(scope: kAudioDevicePropertyScopeOutput)
    }

    private static func getDevices(scope: AudioObjectPropertyScope) -> [AudioDevice] {
        var propertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        
        var dataSize: UInt32 = 0
        var status = AudioObjectGetPropertyDataSize(
            AudioObjectID(kAudioObjectSystemObject),
            &propertyAddress,
            0,
            nil,
            &dataSize
        )
        
        guard status == noErr else { return [] }
        
        let deviceCount = Int(dataSize) / MemoryLayout<AudioObjectID>.size
        var deviceIDs = [AudioObjectID](repeating: 0, count: deviceCount)
        
        status = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &propertyAddress,
            0,
            nil,
            &dataSize,
            &deviceIDs
        )
        
        guard status == noErr else { return [] }
        
        var devices: [AudioDevice] = []
        
        for deviceID in deviceIDs {
            // Check if the device has streams in the requested scope.
            var streamAddress = AudioObjectPropertyAddress(
                mSelector: kAudioDevicePropertyStreams,
                mScope: scope,
                mElement: kAudioObjectPropertyElementMain
            )
            
            var streamDataSize: UInt32 = 0
            status = AudioObjectGetPropertyDataSize(
                deviceID,
                &streamAddress,
                0,
                nil,
                &streamDataSize
            )
            
            guard status == noErr, streamDataSize > 0 else { continue }
            
            // Get device name
            var nameAddress = AudioObjectPropertyAddress(
                mSelector: kAudioDevicePropertyDeviceNameCFString,
                mScope: scope,
                mElement: kAudioObjectPropertyElementMain
            )
            
            var name: CFString = "" as CFString
            var nameSize = UInt32(MemoryLayout<CFString>.size)
            status = withUnsafeMutablePointer(to: &name) {
                AudioObjectGetPropertyData(
                    deviceID,
                    &nameAddress,
                    0,
                    nil,
                    &nameSize,
                    $0
                )
            }
            
            let deviceName = (status == noErr) ? (name as String) : "Unknown Device"
            
            // Get UID
            var uidAddress = AudioObjectPropertyAddress(
                mSelector: kAudioDevicePropertyDeviceUID,
                mScope: scope,
                mElement: kAudioObjectPropertyElementMain
            )
            var uid: CFString = "" as CFString
            var uidSize = UInt32(MemoryLayout<CFString>.size)
            status = withUnsafeMutablePointer(to: &uid) {
                AudioObjectGetPropertyData(
                    deviceID,
                    &uidAddress,
                    0,
                    nil,
                    &uidSize,
                    $0
                )
            }
            
            let deviceUID = (status == noErr) ? (uid as String) : ""
            
            devices.append(AudioDevice(deviceID: deviceID, uid: deviceUID, name: deviceName))
        }
        
        return devices
    }

    static func getDeviceID(for uid: String) -> AudioDeviceID? {
        getInputDevices().first { $0.uid == uid }?.deviceID
    }

    static func getOutputDeviceID(for uid: String) -> AudioDeviceID? {
        getOutputDevices().first { $0.uid == uid }?.deviceID
    }

    static func preferredVirtualInputDevice(from devices: [AudioDevice], selectedUID: String?) -> AudioDevice? {
        if let selectedUID,
           let selected = devices.first(where: { $0.uid == selectedUID }) {
            return selected
        }
        return devices.first(where: isLikelyVirtualLoopbackDevice)
    }

    static func isLikelyVirtualLoopbackDevice(_ device: AudioDevice) -> Bool {
        let haystack = "\(device.name) \(device.uid)".lowercased()
        return haystack.contains("blackhole")
            || haystack.contains("black hole")
            || haystack.contains("loopback")
            || haystack.contains("soundflower")
            || haystack.contains("vb-cable")
            || haystack.contains("virtual")
    }
}
