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
if CommandLine.arguments.count == 1 { print("Selected: \(property(device, kAudioObjectPropertyName)); UID: \(uid)"); exit(0) }
let player = try AVAudioPlayer(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
player.currentDevice = uid
player.volume = 0.65
player.enableRate = false
guard player.prepareToPlay(), player.play() else { fatalError("Playback failed") }
print("Playing on \(property(device, kAudioObjectPropertyName)), duration \(player.duration), native rate")
let deadline = Date().addingTimeInterval(player.duration + 3)
while player.isPlaying && Date() < deadline { RunLoop.current.run(until: Date().addingTimeInterval(0.02)) }
if player.isPlaying { player.stop(); exit(2) }
