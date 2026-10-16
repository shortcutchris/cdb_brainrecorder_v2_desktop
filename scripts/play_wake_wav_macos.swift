// Explicit room-test playback on the built-in speaker; never changes the default output.
// Compile on the Mac Studio. No arguments prints the selected device without playing.
import Foundation
import CoreAudio
import AVFAudio
func property(_ id: AudioObjectID, _ selector: AudioObjectPropertySelector) -> String {
    var address = AudioObjectPropertyAddress(mSelector: selector, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
    var value: CFString = "" as CFString
    var size = UInt32(MemoryLayout<CFString>.size)
    guard AudioObjectGetPropertyData(id, &address, 0, nil, &size, &value) == noErr else { return "" }
    return value as String
}
var address = AudioObjectPropertyAddress(mSelector: kAudioHardwarePropertyDevices, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
var size: UInt32 = 0
AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &size)
var devices = [AudioObjectID](repeating: 0, count: Int(size)/MemoryLayout<AudioObjectID>.size)
AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &size, &devices)
guard let device = devices.first(where: { property($0, kAudioObjectPropertyName).contains("Mac Studio") }) else { fatalError("Built-in Mac Studio speaker missing") }
let uid = property(device, kAudioDevicePropertyDeviceUID)
for element: UInt32 in [0, 1, 2] {
    var volumeAddress = AudioObjectPropertyAddress(mSelector: kAudioDevicePropertyVolumeScalar, mScope: kAudioDevicePropertyScopeOutput, mElement: element)
    var volume: Float32 = 0
    var volumeSize = UInt32(MemoryLayout<Float32>.size)
    if AudioObjectGetPropertyData(device, &volumeAddress, 0, nil, &volumeSize, &volume) == noErr {
        print("Device volume channel \(element): \(volume)")
    }
}
if CommandLine.arguments.count == 1 { print("Selected: \(property(device, kAudioObjectPropertyName)); UID: \(uid)"); exit(0) }
let player = try AVAudioPlayer(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
player.currentDevice = uid
let volume = CommandLine.arguments.count > 2 ? Float(CommandLine.arguments[2]) : 0.65
guard let volume, volume.isFinite, (0...1).contains(volume) else { fatalError("Use player volume 0–1") }
player.volume = volume
player.enableRate = false
guard player.prepareToPlay(), player.play() else { fatalError("Playback failed") }
print("Playing on \(property(device, kAudioObjectPropertyName)), UID \(player.currentDevice ?? "unknown"), duration \(player.duration), player volume \(volume), native rate")
let deadline = Date().addingTimeInterval(player.duration + 3)
while player.isPlaying && Date() < deadline { RunLoop.current.run(until: Date().addingTimeInterval(0.02)) }
if player.isPlaying { player.stop(); exit(2) }
