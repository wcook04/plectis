import AppKit
import SwiftUI

// MARK: - Cue sheet rendering (see-through teleprompter)
//
// The operator-private teleprompter. Full-cues mode shows the full parsed run-sheet
// mic surface so the operator can scroll the actual run-through. Glance mode is
// the deliberately compressed WHO / OPEN / ASK card for quick checks.
//
// Scrolling and height are driven by SHARED session state, so every display stays
// in lockstep (same place, same size). The panel is see-through glass; a drop
// shadow keeps the coloured text legible over anything behind it.

struct CueSheetView: View {
    @ObservedObject var session: OverlaySession
    @ObservedObject private var sentinel = SentinelOverlayRenderer.shared
    let displayID: CGDirectDisplayID

    @State private var contentHeight: CGFloat = 0
    @State private var viewportHeight: CGFloat = 0
    @State private var blockFrames: [Int: CGRect] = [:]

    private var isArmed: Bool { session.armedDisplayID == displayID }
    private var contentMeasurementID: String {
        [
            session.selectedRecipientID ?? "none",
            String(session.glanceMode),
            String(format: "%.3f", Double(session.cueTextScale)),
            String(session.compressedScript.count),
            String(session.scriptBlocks.count),
            String(session.verbatimLines.count),
        ].joined(separator: "|")
    }

    var body: some View {
        ZStack {
            background
            VStack(spacing: 0) {
                scrollArea
                Divider().background(Color.white.opacity(0.08))
                footer
            }
            sentinelBand
        }
        .overlay(armedBorder)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    /// Unmistakable high-contrast sentinel painted during a safety check. If this
    /// magenta band shows up in any captured frame, the overlay LEAKS.
    @ViewBuilder private var sentinelBand: some View {
        if sentinel.active {
            ZStack {
                Color(red: 1, green: 0, blue: 1)
                Text("CAPTURE-EXCLUSION SENTINEL")
                    .font(.system(size: 22, weight: .heavy))
                    .foregroundStyle(.black)
            }
        }
    }

    // MARK: - Background (see-through glass)

    private var background: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(.ultraThinMaterial)
                .environment(\.colorScheme, .dark)
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color.black.opacity(0.12))
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(Color.white.opacity(0.12), lineWidth: 1)
        }
    }

    @ViewBuilder private var armedBorder: some View {
        if isArmed {
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(DTC.accent.opacity(0.9), lineWidth: 2.5)
        }
    }

    // MARK: - Footer (fixed; does not scroll)

    private var footer: some View {
        HStack(spacing: 8) {
            Text(session.recipientName)
                .font(.system(size: 11, weight: .heavy))
                .tracking(0.4)
                .foregroundStyle(DTC.accent)
                .lineLimit(1)
            Spacer(minLength: 6)
            if session.glanceMode {
                Text("GLANCE")
                    .font(.system(size: 9, weight: .heavy, design: .monospaced))
                    .tracking(0.6)
                    .foregroundStyle(Color.white.opacity(0.55))
            } else {
                legendDot(CueColor.say, "say")
                if session.scriptBlocks.isEmpty {
                    legendDot(.white, "land")
                    legendDot(CueColor.direction, "do")
                }
                Text(session.lineStepModeEnabled ? "LINE" : "\u{2318} scroll")
                    .font(.system(size: 9, weight: .semibold, design: .monospaced))
                    .foregroundStyle(session.lineStepModeEnabled ? CueColor.say.opacity(0.78) : Color.white.opacity(0.5))
            }
        }
        .legible()
        .padding(.horizontal, 14)
        .padding(.vertical, 6)
    }

    private func legendDot(_ color: Color, _ label: String) -> some View {
        HStack(spacing: 4) {
            Circle().fill(color).frame(width: 6, height: 6)
            Text(label)
                .font(.system(size: 9, weight: .semibold))
                .foregroundStyle(Color.white.opacity(0.7))
        }
    }

    // MARK: - Glance card (default surface; scrolls when clipped)
    //
    // The operator's real on-camera surface: a few cue words to glance at, never a
    // script to read. It shows who this person is, the one thing to open, and the
    // one bounded ask, each compressed to a glanceable length. Derived only from
    // loaded recipient data; an absent field is simply omitted, never fabricated.

    @ViewBuilder private var glanceBody: some View {
        if session.spine != nil || session.doctrineLaw != nil {
            themeGlanceBody
        } else {
            personaGlanceBody
        }
    }

    /// Theme glance card: the first-principles mental model plus the one public law
    /// the clip demonstrates. This is what makes a person-agnostic theme overlay
    /// show real substance — the law, the parts, the mechanism, the ceiling, the
    /// recovery line — instead of an empty persona card.
    @ViewBuilder private var themeGlanceBody: some View {
        let law = session.doctrineLaw
        let s = session.spine
        VStack(alignment: .leading, spacing: 11) {
            if let view = session.onCameraView {
                glanceRow("display", "OPEN", view, color: CueColor.direction, size: 16)
            }
            if let primitive = s?.primitiveProblem {
                glanceRow("questionmark.circle", "WHY", compressedGlance(primitive, words: 18) ?? primitive, color: Color.white.opacity(0.78), size: 14)
            }
            if let law {
                glanceRow("building.columns", "LAW", lawLabel(law), color: DTC.accent, size: 17)
            }
            if let objects = s?.irreducibleObjects {
                glanceRow("cube", "PARTS", compressedGlance(objects, words: 16) ?? objects, color: .white, size: 15)
            }
            if let mech = s?.mechanism {
                glanceRow("gearshape.2", "HOW", compressedGlance(mech, words: 22) ?? mech, color: CueColor.direction, size: 14)
            }
            if let example = s?.workedExample {
                glanceRow("play.rectangle", "SHOW", compressedGlance(example, words: 16) ?? example, color: .white, size: 14)
            }
            if let ceiling = s?.claimCeiling {
                glanceRow("exclamationmark.triangle", "NOT", compressedGlance(ceiling, words: 18) ?? ceiling, color: Color.white.opacity(0.6), size: 12)
            }
            if let recover = s?.recoveryLine {
                glanceRow("lifepreserver", "SAY", compressedGlance(recover, words: 22) ?? recover, color: CueColor.say, size: 15)
            }
            if law == nil, s == nil { recoveryBody }
        }
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .padding(.horizontal, 12)
        .padding(.top, 8)
        .padding(.bottom, 12)
    }

    private func lawLabel(_ d: DoctrineFlash) -> String {
        d.title.isEmpty ? d.id : "\(d.id)  \(d.title)"
    }

    private var personaGlanceBody: some View {
        let a = personaAnchor
        let identity = compressedGlance(session.glanceIdentity ?? a.lens, words: 14)
        let open = compressedGlance(a.corner ?? session.compressedScript.first?.show.first, words: 12)
        let ask = compressedGlance(session.glanceAsk ?? a.ask, words: 18)
        let limit = compressedGlance(session.glanceLimit, words: 12)
        return VStack(alignment: .leading, spacing: 16) {
            if let identity {
                glanceRow("person.fill", "WHO", identity, color: .white, size: 22)
            }
            if let open {
                glanceRow("rectangle.on.rectangle", "OPEN", open, color: CueColor.direction, size: 18)
            }
            if let ask {
                glanceRow("questionmark.circle", "ASK", ask, color: CueColor.say, size: 17)
            }
            if let limit {
                glanceRow("exclamationmark.triangle", "LIMIT", limit, color: Color.white.opacity(0.55), size: 12)
            }
            if identity == nil, open == nil, ask == nil {
                recoveryBody
            }
        }
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .padding(.horizontal, 12)
        .padding(.top, 8)
        .padding(.bottom, 12)
    }

    private func glanceRow(
        _ icon: String,
        _ label: String,
        _ text: String,
        color: Color,
        size: CGFloat
    ) -> some View {
        HStack(alignment: .top, spacing: 9) {
            VStack(spacing: 3) {
                Image(systemName: icon)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(color.opacity(0.85))
                Text(label)
                    .font(.system(size: 8, weight: .heavy))
                    .foregroundStyle(color.opacity(0.7))
            }
            .frame(width: 39)
            .padding(.top, 2)
            Text(styled(text, base: color))
                .font(cueFont(size, weight: .semibold))
                .foregroundStyle(color)
                .lineLimit(4)
                .fixedSize(horizontal: false, vertical: true)
        }
        .legible()
    }

    /// Compress a field to a glanceable length: prefer the first sentence, then cap
    /// at `words`. Returns nil for empty input so the row is simply omitted.
    private func compressedGlance(_ raw: String?, words: Int) -> String? {
        guard let raw else { return nil }
        let trimmed = raw.trimmingCharacters(in: CharacterSet(charactersIn: " \n\t\"\u{201C}\u{201D}"))
        guard !trimmed.isEmpty else { return nil }
        let firstSentence = trimmed
            .split(whereSeparator: { ".!?".contains($0) })
            .first
            .map(String.init)?
            .trimmingCharacters(in: .whitespaces)
        let base = (firstSentence?.isEmpty == false) ? firstSentence! : trimmed
        let parts = base.split(separator: " ")
        if parts.count <= words { return base }
        return parts.prefix(words).joined(separator: " ") + "\u{2026}"
    }

    private func cueFont(
        _ size: CGFloat,
        weight: Font.Weight = .regular,
        design: Font.Design = .default
    ) -> Font {
        .system(size: max(8, size * session.cueTextScale), weight: weight, design: design)
    }

    // MARK: - Scroll area (shared progress; projected per display)

    private var scrollArea: some View {
        GeometryReader { geo in
            let viewport = session.effectiveScrollViewportHeight(
                for: displayID,
                measuredViewportHeight: geo.size.height
            )
            let contentWidth = max(1, geo.size.width - 32)
            scrollContent
                .padding(.horizontal, 16)
                .padding(.top, 4)
                .padding(.bottom, 12)
                .frame(width: geo.size.width, alignment: .topLeading)
                .fixedSize(horizontal: false, vertical: true)
                .id(contentMeasurementID)
                .coordinateSpace(name: CueSheetCoordinateSpace.content)
                .background(
                    GeometryReader { c in
                        Color.clear.preference(key: ContentHeightKey.self, value: c.size.height)
                    }
                )
                .offset(y: -session.offset(for: displayID))
                .onAppear {
                    viewportHeight = viewport
                    reportMetrics(contentHeight: contentHeight, viewportHeight: viewport)
                    reportLineAnchors(contentWidth: contentWidth, blockFrames: blockFrames)
                }
                .onPreferenceChange(ContentHeightKey.self) { h in
                    contentHeight = h
                    reportMetrics(contentHeight: h, viewportHeight: viewport)
                }
                .onPreferenceChange(CueBlockFrameKey.self) { frames in
                    blockFrames = frames
                    reportLineAnchors(contentWidth: contentWidth, blockFrames: frames)
                }
                .onChange(of: geo.size.width) { _, width in
                    reportLineAnchors(contentWidth: max(1, width - 32), blockFrames: blockFrames)
                }
                .onChange(of: geo.size.height) { _, vp in
                    let effectiveViewport = session.effectiveScrollViewportHeight(
                        for: displayID,
                        measuredViewportHeight: vp
                    )
                    viewportHeight = effectiveViewport
                    reportMetrics(contentHeight: contentHeight, viewportHeight: effectiveViewport)
                }
                .onChange(of: contentMeasurementID) { _, _ in
                    contentHeight = 0
                    viewportHeight = viewport
                    blockFrames = [:]
                    reportMetrics(contentHeight: 0, viewportHeight: viewport)
                    reportLineAnchors(contentWidth: contentWidth, blockFrames: [:])
                }
        }
        .clipped()
    }

    private func reportMetrics(contentHeight: CGFloat, viewportHeight: CGFloat) {
        session.setContentMetrics(
            for: displayID,
            contentHeight: contentHeight,
            viewportHeight: viewportHeight
        )
    }

    private func reportLineAnchors(contentWidth: CGFloat, blockFrames: [Int: CGRect]) {
        let anchors = measuredLineAnchors(contentWidth: contentWidth, blockFrames: blockFrames)
        session.setLineAnchors(for: displayID, offsets: anchors)
    }

    private func measuredLineAnchors(contentWidth: CGFloat, blockFrames: [Int: CGRect]) -> [CGFloat] {
        guard !session.glanceMode, !session.scriptBlocks.isEmpty, !blockFrames.isEmpty else { return [] }
        let ordered = ScriptBlockTeleprompterOrder.speakableFirst(session.scriptBlocks)
        var anchors: [CGFloat] = []
        for block in ordered.visibleBlocks {
            guard let frame = blockFrames[block.index], frame.height > 1 else { continue }
            let spec = CueBlockLineMeasurementSpec(block: block, textScale: session.cueTextScale)
            let width = max(1, contentWidth - spec.horizontalReserve)
            for lineOffset in CueTextLineMeasurer.lineOffsets(text: spec.text, font: spec.font, width: width) {
                let anchor = frame.minY + spec.topInset + lineOffset
                guard anchor.isFinite, anchor >= 0 else { continue }
                anchors.append(anchor)
            }
        }
        return anchors
    }

    @ViewBuilder private var scrollContent: some View {
        let beats = session.compressedScript
        if session.glanceMode {
            glanceBody
        } else if !session.scriptBlocks.isEmpty {
            let ordered = ScriptBlockTeleprompterOrder.speakableFirst(session.scriptBlocks)
            VStack(alignment: .leading, spacing: 9) {
                ForEach(ordered.visibleBlocks) { measuredBlockView($0) }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        } else if !beats.isEmpty {
            VStack(alignment: .leading, spacing: 12) {
                madeForBand
                verbatimGroup
                ForEach(Array(beats.enumerated()), id: \.element.id) { idx, beat in
                    beatView(beat)
                    if let next = beat.next, idx < beats.count - 1 {
                        connector(next)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        } else {
            recoveryBody
        }
    }

    // MARK: - Made-for anchor (the personalisation, surfaced at the top)
    //
    // Each cue deck already grounds the cut in this person: their named work (the
    // lens), the open question they are best placed to judge, and their corner of
    // the site. Those three signals are scattered across beats 0, 2 and the WHY
    // beat, so we lift them into one band at the very top — the first thing on
    // screen says, unmistakably, who this is for and why.

    private struct PersonaAnchor {
        var lens: String?
        var ask: String?
        var corner: String?
        var isEmpty: Bool { lens == nil && ask == nil && corner == nil }
    }

    private var personaAnchor: PersonaAnchor {
        let beats = session.compressedScript
        var a = PersonaAnchor()
        if let firstLand = beats.first?.land.first {
            a.lens = stripMadeForYou(firstLand)
        }
        outer: for b in beats {
            for line in b.show + b.land {
                if let r = line.range(of: "open questions", options: .caseInsensitive) {
                    a.ask = formatAsk(String(line[r.upperBound...]))
                    break outer
                }
            }
        }
        if let site = beats.first(where: { $0.name.uppercased().contains("SITE") }),
           let show = site.show.first {
            a.corner = show
        }
        return a
    }

    private func stripMadeForYou(_ s: String) -> String {
        var t = s.trimmingCharacters(in: .whitespaces)
        for p in ["made for you:", "made for you,", "made for you"] where t.lowercased().hasPrefix(p) {
            t = String(t.dropFirst(p.count)).trimmingCharacters(in: CharacterSet(charactersIn: " :,"))
            break
        }
        return t
    }

    private func formatAsk(_ raw: String) -> String {
        let s = raw.trimmingCharacters(in: CharacterSet(charactersIn: " :\"\u{201C}\u{201D}"))
        let parts = s.split(separator: " ", maxSplits: 1)
        let qid = parts.first.map(String.init) ?? ""
        let text = parts.count > 1
            ? String(parts[1]).trimmingCharacters(in: CharacterSet(charactersIn: " \"\u{201C}\u{201D}"))
            : ""
        if qid.isEmpty { return text }
        return text.isEmpty ? qid : "\(qid) \u{2014} \(text)"
    }

    @ViewBuilder private var madeForBand: some View {
        let a = personaAnchor
        if !a.isEmpty {
            VStack(alignment: .leading, spacing: 7) {
                Text("MADE FOR \(session.recipientName.uppercased())")
                    .font(cueFont(12, weight: .heavy))
                    .tracking(0.9)
                    .foregroundStyle(DTC.accent)
                if let lens = a.lens { anchorRow("lens", lens) }
                if let ask = a.ask { anchorRow("asks", ask) }
                if let corner = a.corner { anchorRow("corner", corner) }
            }
            .padding(10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 10).fill(DTC.accent.opacity(0.10)))
            .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(DTC.accent.opacity(0.30), lineWidth: 1))
            .legible()
        }
    }

    private func anchorRow(_ label: String, _ text: String) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Text(label.uppercased())
                .font(cueFont(10, weight: .heavy))
                .foregroundStyle(DTC.accent.opacity(0.85))
                .frame(width: 48, alignment: .leading)
                .padding(.top, 3)
            Text(styled(text, base: .white))
                .font(cueFont(14, weight: .semibold))
                .foregroundStyle(.white)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: - Compressed cue rendering

    /// The exact lines, lifted to the top and shown verbatim — wording carries
    /// weight here, so these are read as-written, not riffed.
    @ViewBuilder private var verbatimGroup: some View {
        let lines = session.verbatimLines
        if !lines.isEmpty {
            VStack(alignment: .leading, spacing: 9) {
                Text("EXACT LINES \u{00B7} say verbatim")
                    .font(cueFont(11, weight: .heavy))
                    .tracking(0.8)
                    .foregroundStyle(CueColor.say)
                ForEach(lines, id: \.self) { line in
                    HStack(alignment: .top, spacing: 8) {
                        sayPill
                        Text(styled(line, base: CueColor.say))
                            .font(cueFont(18, weight: .bold))
                            .foregroundStyle(CueColor.say)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
            .padding(10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 10).fill(CueColor.say.opacity(0.08)))
            .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(CueColor.say.opacity(0.28), lineWidth: 1))
            .legible()
        }
    }

    private var sayPill: some View {
        Text("SAY")
            .font(.system(size: 10, weight: .heavy))
            .padding(.horizontal, 5).padding(.vertical, 2)
            .background(Capsule().fill(CueColor.say))
            .foregroundStyle(.black)
            .padding(.top, 4)
    }

    private func beatView(_ beat: BeatCue) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            // Beat label: "0 · RECOGNITION"
            HStack(spacing: 7) {
                Text(beat.num)
                    .font(cueFont(12, weight: .heavy, design: .monospaced))
                    .padding(.horizontal, 6).padding(.vertical, 2)
                    .background(RoundedRectangle(cornerRadius: 5).fill(DTC.accent.opacity(0.22)))
                    .foregroundStyle(DTC.accent)
                Text(beat.name)
                    .font(cueFont(13, weight: .heavy))
                    .tracking(0.6)
                    .foregroundStyle(DTC.accent)
            }
            .legible()

            // DOCTRINE — the one public law this screen is an instance of.
            if let d = beat.doctrine, !d.id.isEmpty {
                HStack(spacing: 6) {
                    Text(d.id)
                        .font(cueFont(10, weight: .heavy, design: .monospaced))
                        .padding(.horizontal, 5).padding(.vertical, 1)
                        .background(RoundedRectangle(cornerRadius: 4).fill(Color.white.opacity(0.16)))
                        .foregroundStyle(Color.white.opacity(0.88))
                    if !d.flashText.isEmpty {
                        Text(d.flashText)
                            .font(cueFont(12, weight: .semibold))
                            .foregroundStyle(Color.white.opacity(0.72))
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .legible()
                if let dni = d.doNotImply, !dni.isEmpty {
                    Text("not: \(dni)")
                        .font(cueFont(11, weight: .medium))
                        .foregroundStyle(DTC.attention.opacity(0.7))
                        .fixedSize(horizontal: false, vertical: true)
                        .legible()
                }
            }

            // LAND — the compressed point(s) you must land. White, the eye's anchor.
            ForEach(beat.land, id: \.self) { land in
                HStack(alignment: .top, spacing: 9) {
                    Circle().fill(CueColor.say.opacity(0.9))
                        .frame(width: 6, height: 6).padding(.top, 9)
                    Text(styled(land, base: .white))
                        .font(cueFont(18, weight: .semibold))
                        .foregroundStyle(.white)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .legible()
            }

            // SHOW — what is on screen. Amber: a do, not a say.
            ForEach(beat.show, id: \.self) { show in
                HStack(alignment: .top, spacing: 7) {
                    Image(systemName: "rectangle.on.rectangle")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(CueColor.direction.opacity(0.9))
                        .padding(.top, 3)
                    Text(styled(show, base: CueColor.direction))
                        .font(cueFont(14, weight: .medium))
                        .foregroundStyle(CueColor.direction)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .legible()
            }

            // LIMIT — the ceiling / what not to imply. Dim, quiet, present.
            if let limit = beat.limit {
                HStack(alignment: .top, spacing: 7) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(DTC.attention.opacity(0.6))
                        .padding(.top, 3)
                    Text(limit)
                        .font(cueFont(12, weight: .medium))
                        .foregroundStyle(Color.white.opacity(0.55))
                        .fixedSize(horizontal: false, vertical: true)
                }
                .legible()
            }

            // SCREEN — what visual surface to put on camera, plus what it shows.
            if let screenText = beatScreenCueText(beat) {
                HStack(alignment: .top, spacing: 7) {
                    Image(systemName: "display")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(CueColor.direction.opacity(0.7))
                        .padding(.top, 3)
                    Text(screenText)
                        .font(cueFont(12, weight: .medium))
                        .foregroundStyle(Color.white.opacity(0.6))
                        .fixedSize(horizontal: false, vertical: true)
                }
                .legible()
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    /// The connector between beats — the green thread the flow follows.
    private func connector(_ next: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: "arrow.down")
                .font(.system(size: 11, weight: .heavy))
                .foregroundStyle(CueColor.say.opacity(0.7))
            Text(next)
                .font(cueFont(13, weight: .semibold))
                .foregroundStyle(CueColor.say.opacity(0.85))
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(.leading, 4)
        .legible()
    }

    private func beatScreenCueText(_ beat: BeatCue) -> String? {
        if let view = conciseViewLabel(beat.view) {
            return view
        }
        return conciseViewLabel(beat.onScreen)
    }

    private func conciseViewLabel(_ raw: String?) -> String? {
        guard let raw else { return nil }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let parts = trimmed.split(separator: " ", maxSplits: 1).map(String.init)
        guard let first = parts.first else { return trimmed }
        if first == "/station" {
            return parts.count > 1 ? "Station \(parts[1])" : "Station Surface Atlas"
        }
        if first.hasPrefix("/station/") {
            return parts.count > 1 ? parts[1] : String(first.dropFirst("/station/".count))
        }
        return trimmed
    }

    // MARK: - Fallback prose blocks (no cue layer)

    private func measuredBlockView(_ block: ScriptBlock) -> some View {
        blockView(block)
            .background(
                GeometryReader { proxy in
                    Color.clear.preference(
                        key: CueBlockFrameKey.self,
                        value: [block.index: proxy.frame(in: .named(CueSheetCoordinateSpace.content))]
                    )
                }
            )
    }

    @ViewBuilder private func blockView(_ block: ScriptBlock) -> some View {
        switch block.kind {
        case .heading:
            VStack(alignment: .leading, spacing: 6) {
                Rectangle().fill(Color.white.opacity(0.10)).frame(height: 1)
                Text(block.text.uppercased())
                    .font(cueFont(12, weight: .heavy))
                    .tracking(0.6)
                    .foregroundStyle(DTC.accent)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(.top, 8)
            .legible()
        case .say:
            VStack(alignment: .leading, spacing: 3) {
                viewCueLine(block.viewCue)
                HStack(alignment: .top, spacing: 8) {
                    sayPill
                    labeledCueText(block.text, base: CueColor.say, bodySize: 19, bodyWeight: .bold)
                }
            }
            .legible()
        case .spoken:
            VStack(alignment: .leading, spacing: 3) {
                viewCueLine(block.viewCue)
                HStack(alignment: .top, spacing: 10) {
                    RoundedRectangle(cornerRadius: 2).fill(CueColor.say.opacity(0.85)).frame(width: 3)
                    labeledCueText(block.text, base: .white, bodySize: 19, bodyWeight: .semibold)
                }
            }
            .legible()
        case .direction:
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: "arrow.turn.down.right")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(CueColor.direction.opacity(0.9))
                    .padding(.top, 4)
                labeledCueText(block.text, base: CueColor.direction, bodySize: 15, bodyWeight: .medium)
            }
            .legible()
        case .note:
            Text(styled(block.text, base: Color.white.opacity(0.62)))
                .font(cueFont(13, weight: .medium))
                .italic()
                .foregroundStyle(Color.white.opacity(0.62))
                .fixedSize(horizontal: false, vertical: true)
                .legible()
        case .mono:
            Text(block.text)
                .font(cueFont(12, weight: .regular, design: .monospaced))
                .foregroundStyle(Color.white.opacity(0.82))
                .padding(7)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: 6).fill(Color.black.opacity(0.28)))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    @ViewBuilder private func viewCueLine(_ raw: String?) -> some View {
        if let label = conciseViewLabel(raw) {
            Text(label)
                .font(cueFont(10, weight: .semibold))
                .foregroundStyle(CueColor.direction.opacity(0.72))
                .lineLimit(1)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private struct CueLeadSplit {
        var lead: String?
        var body: String
    }

    private func splitCueLead(_ raw: String) -> CueLeadSplit {
        guard let range = raw.range(of: "::") else {
            return CueLeadSplit(lead: nil, body: raw)
        }
        let lead = raw[..<range.lowerBound].trimmingCharacters(in: .whitespaces)
        let body = raw[range.upperBound...].trimmingCharacters(in: .whitespaces)
        guard !lead.isEmpty, lead.count <= 32, !body.isEmpty else {
            return CueLeadSplit(lead: nil, body: raw)
        }
        return CueLeadSplit(lead: lead, body: body)
    }

    private func labeledCueText(
        _ raw: String,
        base: Color,
        bodySize: CGFloat,
        bodyWeight: Font.Weight
    ) -> some View {
        let split = splitCueLead(raw)
        return HStack(alignment: .firstTextBaseline, spacing: 7) {
            if let lead = split.lead {
                Text(lead.uppercased())
                    .font(cueFont(max(9, bodySize * 0.68), weight: .heavy))
                    .tracking(0.4)
                    .foregroundStyle(CueColor.highlight)
                    .lineLimit(1)
            }
            Text(styled(split.body, base: base))
                .font(cueFont(bodySize, weight: bodyWeight))
                .foregroundStyle(base)
                .layoutPriority(1)
                .fixedSize(horizontal: false, vertical: true)
        }
        .fixedSize(horizontal: false, vertical: true)
    }

    /// Inline markdown emphasis as colour: **bold** -> cyan highlight, `code` ->
    /// accent. Non-emphasised runs keep the block's base colour.
    private func styled(_ raw: String, base: Color) -> AttributedString {
        var attr: AttributedString
        if let parsed = try? AttributedString(
            markdown: raw,
            options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        ) {
            attr = parsed
        } else {
            attr = AttributedString(raw)
        }
        for run in attr.runs {
            guard let intent = run.inlinePresentationIntent else { continue }
            if intent.contains(.code) {
                attr[run.range].foregroundColor = DTC.accent
            } else if intent.contains(.stronglyEmphasized) {
                attr[run.range].foregroundColor = CueColor.highlight
            }
        }
        return attr
    }

    /// The honest recovery body when there is nothing to show.
    private var recoveryBody: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("RECOVERY")
                .font(.system(size: 14, weight: .heavy))
                .foregroundStyle(DTC.attention)
            Text(session.selectedRecipientID == nil
                 ? "No recipient selected. Use Overlay \u{25B8} Select Recipient."
                 : "Script unavailable. Close honestly: thank them, state the one bounded ask, stop.")
                .font(cueFont(17, weight: .bold))
                .foregroundStyle(.white)
                .fixedSize(horizontal: false, vertical: true)
            if let err = session.lastError {
                Text(err)
                    .font(.system(size: 12, design: .monospaced))
                    .foregroundStyle(Color.white.opacity(0.5))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .legible()
    }
}

// MARK: - Content height plumbing

private struct ContentHeightKey: PreferenceKey {
    static let defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = max(value, nextValue())
    }
}

private enum CueSheetCoordinateSpace {
    static let content = "cue-sheet-scroll-content"
}

private struct CueBlockFrameKey: PreferenceKey {
    static let defaultValue: [Int: CGRect] = [:]
    static func reduce(value: inout [Int: CGRect], nextValue: () -> [Int: CGRect]) {
        value.merge(nextValue(), uniquingKeysWith: { _, next in next })
    }
}

private struct CueBlockLineMeasurementSpec {
    var text: String
    var font: NSFont
    var topInset: CGFloat
    var horizontalReserve: CGFloat

    init(block: ScriptBlock, textScale: CGFloat) {
        let scale = textScale.clamped(OverlaySession.minCueTextScale, OverlaySession.maxCueTextScale)
        switch block.kind {
        case .heading:
            text = Self.plainInlineText(block.text).uppercased()
            font = Self.systemFont(size: 12, weight: .heavy, scale: scale)
            topInset = 15
            horizontalReserve = 0
        case .say:
            let body = Self.splitCueLead(block.text)
            text = Self.plainInlineText(body.body)
            font = Self.systemFont(size: 19, weight: .bold, scale: scale)
            topInset = Self.viewCueTopInset(block, scale: scale)
            horizontalReserve = 39 + Self.leadReserve(body.lead, bodySize: 19, scale: scale)
        case .spoken:
            let body = Self.splitCueLead(block.text)
            text = Self.plainInlineText(body.body)
            font = Self.systemFont(size: 19, weight: .semibold, scale: scale)
            topInset = Self.viewCueTopInset(block, scale: scale)
            horizontalReserve = 13 + Self.leadReserve(body.lead, bodySize: 19, scale: scale)
        case .direction:
            let body = Self.splitCueLead(block.text)
            text = Self.plainInlineText(body.body)
            font = Self.systemFont(size: 15, weight: .medium, scale: scale)
            topInset = 0
            horizontalReserve = 22 + Self.leadReserve(body.lead, bodySize: 15, scale: scale)
        case .note:
            text = Self.plainInlineText(block.text)
            font = Self.systemFont(size: 13, weight: .medium, scale: scale)
            topInset = 0
            horizontalReserve = 0
        case .mono:
            text = block.text
            font = NSFont.monospacedSystemFont(ofSize: max(8, 12 * scale), weight: .regular)
            topInset = 7
            horizontalReserve = 14
        }
        if text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            text = block.text
        }
    }

    private struct CueLeadSplit {
        var lead: String?
        var body: String
    }

    private static func splitCueLead(_ raw: String) -> CueLeadSplit {
        guard let range = raw.range(of: "::") else {
            return CueLeadSplit(lead: nil, body: raw)
        }
        let lead = raw[..<range.lowerBound].trimmingCharacters(in: .whitespaces)
        let body = raw[range.upperBound...].trimmingCharacters(in: .whitespaces)
        guard !lead.isEmpty, lead.count <= 32, !body.isEmpty else {
            return CueLeadSplit(lead: nil, body: raw)
        }
        return CueLeadSplit(lead: lead, body: body)
    }

    private static func plainInlineText(_ raw: String) -> String {
        if let parsed = try? AttributedString(
            markdown: raw,
            options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        ) {
            return String(parsed.characters)
        }
        return raw
    }

    private static func leadReserve(_ lead: String?, bodySize: CGFloat, scale: CGFloat) -> CGFloat {
        guard let lead else { return 0 }
        let font = systemFont(size: max(9, bodySize * 0.68), weight: .heavy, scale: scale)
        let width = ceil((lead.uppercased() as NSString).size(withAttributes: [.font: font]).width)
        return width + 7
    }

    private static func viewCueTopInset(_ block: ScriptBlock, scale: CGFloat) -> CGFloat {
        guard let cue = block.viewCue?.trimmingCharacters(in: .whitespacesAndNewlines),
              !cue.isEmpty else { return 0 }
        let font = systemFont(size: 10, weight: .semibold, scale: scale)
        return ceil(font.ascender - font.descender + font.leading) + 3
    }

    private static func systemFont(size: CGFloat, weight: NSFont.Weight, scale: CGFloat) -> NSFont {
        NSFont.systemFont(ofSize: max(8, size * scale), weight: weight)
    }
}

private enum CueTextLineMeasurer {
    static func lineOffsets(text: String, font: NSFont, width: CGFloat) -> [CGFloat] {
        guard width.isFinite, width > 1 else { return [] }
        guard !text.isEmpty else { return [] }

        let storage = NSTextStorage(string: text, attributes: [.font: font])
        let manager = NSLayoutManager()
        let container = NSTextContainer(
            containerSize: NSSize(width: width, height: CGFloat.greatestFiniteMagnitude)
        )
        container.lineFragmentPadding = 0
        container.lineBreakMode = .byWordWrapping
        container.maximumNumberOfLines = 0
        manager.addTextContainer(container)
        storage.addLayoutManager(manager)
        manager.ensureLayout(for: container)

        var offsets: [CGFloat] = []
        var glyphIndex = 0
        while glyphIndex < manager.numberOfGlyphs {
            var range = NSRange(location: 0, length: 0)
            let rect = manager.lineFragmentUsedRect(forGlyphAt: glyphIndex, effectiveRange: &range)
            if rect.minY.isFinite {
                offsets.append(rect.minY)
            }
            let nextIndex = NSMaxRange(range)
            glyphIndex = nextIndex > glyphIndex ? nextIndex : glyphIndex + 1
        }
        return offsets.isEmpty ? [0] : offsets
    }
}

/// Full run sheets often open with nonspoken section labels such as
/// "THE MIC SURFACE" and "Open". For a camera-top teleprompter, the first visible
/// line must be speakable text, not scaffold. Once the spoken stream starts,
/// headings stay out of the projected reading surface entirely.
struct ScriptBlockTeleprompterOrder: Equatable {
    var visibleBlocks: [ScriptBlock]

    static func speakableFirst(_ blocks: [ScriptBlock]) -> ScriptBlockTeleprompterOrder {
        guard let firstSpeakable = blocks.firstIndex(where: { $0.isSpeakableCueText }) else {
            return ScriptBlockTeleprompterOrder(visibleBlocks: blocks)
        }
        let visible = blocks[firstSpeakable...].filter { $0.kind != .heading }
        return ScriptBlockTeleprompterOrder(visibleBlocks: Array(visible))
    }
}

private extension ScriptBlock {
    var isSpeakableCueText: Bool {
        kind == .say || kind == .spoken
    }
}

/// The teleprompter's role palette. Spoken word is green, direction-to-you is
/// amber, and inline key phrases pop in cyan — three colours the eye can sort at a
/// glance while talking.
private enum CueColor {
    static let say       = DTC.success                              // speak / land
    static let direction = DTC.attention                            // do this
    static let highlight = Color(red: 0.42, green: 0.86, blue: 1.0) // key phrase pop
}

private extension View {
    /// Drop shadow so coloured text stays readable against any background showing
    /// through the see-through glass.
    func legible() -> some View {
        self.shadow(color: .black.opacity(0.75), radius: 3, x: 0, y: 1)
    }
}
