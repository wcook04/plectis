import SwiftUI

// MARK: - Palette
//
// A small, deliberate dark "studio deck" token set. The previous UI leaned on
// `.regularMaterial` everywhere, which reads muddy in screenshots. These are
// explicit layered surfaces (base < stage/rail < card < cardHi) plus a tight
// state palette so color always means something.

enum DTC {
    static let base       = Color(red: 0.047, green: 0.051, blue: 0.063)
    static let stage      = Color(red: 0.027, green: 0.031, blue: 0.039)
    static let rail       = Color(red: 0.075, green: 0.082, blue: 0.098)
    static let deck       = Color(red: 0.090, green: 0.098, blue: 0.118)
    static let card       = Color(red: 0.110, green: 0.122, blue: 0.145)
    static let cardHi     = Color(red: 0.150, green: 0.165, blue: 0.196)
    static let stroke     = Color.white.opacity(0.07)
    static let strokeHi   = Color.white.opacity(0.16)

    static let accent     = Color(red: 0.27, green: 0.55, blue: 1.00)
    static let recording  = Color(red: 1.00, green: 0.27, blue: 0.23)
    static let success    = Color(red: 0.20, green: 0.83, blue: 0.35)
    static let attention  = Color(red: 1.00, green: 0.62, blue: 0.04)

    static let textPrimary   = Color.white.opacity(0.92)
    static let textSecondary = Color.white.opacity(0.62)
    static let textTertiary  = Color.white.opacity(0.42)
}

enum Tone {
    case neutral, accent, recording, success, attention, danger
    var color: Color {
        switch self {
        case .neutral:   DTC.textSecondary
        case .accent:    DTC.accent
        case .recording: DTC.recording
        case .success:   DTC.success
        case .attention: DTC.attention
        case .danger:    DTC.recording
        }
    }
}

// MARK: - Formatting helpers

func dtcClock(_ seconds: TimeInterval) -> String {
    let s = seconds.isFinite ? max(0, seconds) : 0
    let whole = Int(s)
    return String(format: "%02d:%02d", whole / 60, whole % 60)
}

/// MM:SS.s — used for transcript cue timestamps where sub-second matters.
func dtcCueTime(_ seconds: Double) -> String {
    let s = seconds.isFinite ? max(0, seconds) : 0
    let minutes = Int(s) / 60
    let remainder = s - Double(minutes * 60)
    return String(format: "%02d:%04.1f", minutes, remainder)
}

func capabilityColor(_ status: CapabilityStatus) -> Color {
    switch status {
    case .ready:             DTC.success
    case .missing, .low:     DTC.recording
    case .unknown:           DTC.attention
    case .notRequired:       DTC.textTertiary
    }
}

// MARK: - Primitives

struct HLine: View {
    var body: some View { Rectangle().fill(DTC.stroke).frame(height: 1) }
}

struct VLine: View {
    var body: some View { Rectangle().fill(DTC.stroke).frame(width: 1) }
}

struct SectionLabel: View {
    let text: String
    var accessory: String?
    init(_ text: String, accessory: String? = nil) {
        self.text = text
        self.accessory = accessory
    }
    var body: some View {
        HStack(spacing: 8) {
            Text(text.uppercased())
                .font(.system(size: 11, weight: .semibold))
                .tracking(0.9)
                .foregroundStyle(DTC.textTertiary)
            if let accessory {
                Text(accessory)
                    .font(.system(size: 11))
                    .foregroundStyle(DTC.textTertiary)
            }
            Spacer(minLength: 0)
        }
    }
}

struct PulsingDot: View {
    let color: Color
    var size: CGFloat = 9
    @State private var on = false
    var body: some View {
        Circle()
            .fill(color)
            .frame(width: size, height: size)
            .shadow(color: color.opacity(0.8), radius: on ? 5 : 1)
            .opacity(on ? 1 : 0.5)
            .onAppear {
                withAnimation(.easeInOut(duration: 0.85).repeatForever(autoreverses: true)) { on = true }
            }
    }
}

struct ReadinessChip: View {
    let label: String
    let status: CapabilityStatus
    var body: some View {
        HStack(spacing: 5) {
            Circle().fill(capabilityColor(status)).frame(width: 6, height: 6)
            Text(label).font(.system(size: 11, weight: .medium)).foregroundStyle(DTC.textSecondary)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Capsule().fill(DTC.card))
        .overlay(Capsule().strokeBorder(DTC.stroke, lineWidth: 1))
        .help("\(label): \(status.label)")
    }
}

struct InfoChip: View {
    let icon: String
    let text: String
    var tone: Tone = .neutral
    var body: some View {
        HStack(spacing: 5) {
            Image(systemName: icon).font(.system(size: 10, weight: .semibold))
            Text(text).font(.system(size: 11, weight: .medium)).lineLimit(1)
        }
        .foregroundStyle(tone.color)
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Capsule().fill(tone.color.opacity(0.13)))
    }
}

struct LevelMeter: View {
    let level: Float
    var body: some View {
        GeometryReader { proxy in
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 3).fill(Color.white.opacity(0.08))
                RoundedRectangle(cornerRadius: 3)
                    .fill(meterColor)
                    .frame(width: max(3, proxy.size.width * CGFloat(min(max(level, 0), 1))))
            }
        }
        .frame(height: 8)
        .accessibilityLabel("Microphone level")
        .accessibilityValue("\(Int(min(max(level, 0), 1) * 100)) percent")
    }
    private var meterColor: Color {
        if level > 0.82 { return DTC.recording }
        if level > 0.55 { return DTC.attention }
        return DTC.success
    }
}

/// Faint dot grid + center falloff for the capture stage, so the empty field
/// reads as intentional monitor topology instead of unused void.
struct StageBackdrop: View {
    var body: some View {
        ZStack {
            Canvas { context, size in
                let step: CGFloat = 26
                let dot: CGFloat = 1.4
                var y: CGFloat = step / 2
                while y < size.height {
                    var x: CGFloat = step / 2
                    while x < size.width {
                        let rect = CGRect(x: x - dot / 2, y: y - dot / 2, width: dot, height: dot)
                        context.fill(Path(ellipseIn: rect), with: .color(.white.opacity(0.05)))
                        x += step
                    }
                    y += step
                }
            }
            RadialGradient(colors: [Color.clear, DTC.stage.opacity(0.85)],
                           center: .center, startRadius: 120, endRadius: 700)
        }
        .allowsHitTesting(false)
    }
}

// MARK: - Button style

struct DTCButtonStyle: ButtonStyle {
    enum Kind { case primary, danger, secondary, ghost }
    var kind: Kind = .secondary
    var large: Bool = false
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: large ? 13 : 12, weight: .semibold))
            .padding(.horizontal, large ? 16 : 12)
            .padding(.vertical, large ? 9 : 6)
            .foregroundStyle(foreground)
            .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(background))
            .overlay(RoundedRectangle(cornerRadius: 8, style: .continuous).strokeBorder(border, lineWidth: 1))
            .opacity(configuration.isPressed ? 0.78 : 1)
            .opacity(isEnabled ? 1 : 0.4)
            .contentShape(Rectangle())
    }

    private var foreground: Color {
        switch kind {
        case .primary:   .white
        case .danger:    .white
        case .secondary: DTC.textPrimary
        case .ghost:     DTC.textSecondary
        }
    }
    private var background: Color {
        switch kind {
        case .primary:   DTC.accent
        case .danger:    DTC.recording
        case .secondary: DTC.card
        case .ghost:     Color.white.opacity(0.04)
        }
    }
    private var border: Color {
        switch kind {
        case .primary:   Color.clear
        case .danger:    Color.clear
        case .secondary: DTC.strokeHi
        case .ghost:     DTC.stroke
        }
    }
}

// MARK: - Card surface

extension View {
    func dtcCard(_ fill: Color = DTC.card,
                 padding: CGFloat = 14,
                 radius: CGFloat = 12,
                 stroke: Color = DTC.stroke) -> some View {
        self
            .padding(padding)
            .background(RoundedRectangle(cornerRadius: radius, style: .continuous).fill(fill))
            .overlay(RoundedRectangle(cornerRadius: radius, style: .continuous).strokeBorder(stroke, lineWidth: 1))
    }
}
