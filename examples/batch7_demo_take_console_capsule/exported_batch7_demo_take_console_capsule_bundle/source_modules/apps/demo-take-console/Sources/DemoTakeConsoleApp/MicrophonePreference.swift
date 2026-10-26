import Foundation

struct MicrophonePreference: Equatable {
    let uniqueID: String?
    let name: String?
    let index: Int?

    var hasSelection: Bool {
        clean(uniqueID) != nil || clean(name) != nil || index != nil
    }

    var displayLabel: String {
        clean(name) ?? clean(uniqueID) ?? index.map { "microphone index \($0)" } ?? "saved microphone"
    }

    private func clean(_ value: String?) -> String? {
        let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? nil : trimmed
    }
}

enum MicrophonePreferenceResolver {
    static func resolve(_ preference: MicrophonePreference, in devices: [CaptureDevice]) -> CaptureDevice? {
        if let uniqueID = clean(preference.uniqueID),
           let match = devices.first(where: { $0.uniqueID == uniqueID }) {
            return match
        }
        if let name = clean(preference.name) {
            if let exact = devices.first(where: { $0.name == name }) {
                return exact
            }
            if let caseInsensitive = devices.first(where: { $0.name.compare(name, options: [.caseInsensitive]) == .orderedSame }) {
                return caseInsensitive
            }
        }
        if let index = preference.index,
           let match = devices.first(where: { $0.index == index }) {
            return match
        }
        return nil
    }

    private static func clean(_ value: String?) -> String? {
        let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? nil : trimmed
    }
}
