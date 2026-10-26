import AppKit
import SwiftUI

private enum ReviewRailMode: String, CaseIterable, Identifiable {
    case transcript = "Transcript"
    case browse = "Browse"

    var id: String { rawValue }
}

struct ReviewInspectionRail: View {
    @ObservedObject var store: RecorderStore
    @ObservedObject var transcript: TranscriptController
    @ObservedObject var atlas: ObservationAtlasController
    @State private var mode: ReviewRailMode = .transcript

    var body: some View {
        VStack(spacing: 8) {
            HStack(spacing: 8) {
                Picker("", selection: $mode) {
                    ForEach(ReviewRailMode.allCases) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }
                .pickerStyle(.segmented)
                .frame(width: 190)

                Text(statusLine)
                    .font(.system(size: 10))
                    .foregroundStyle(DTC.textTertiary)
                    .lineLimit(1)

                Spacer(minLength: 0)
            }

            Group {
                switch mode {
                case .transcript:
                    transcriptPanel
                case .browse:
                    ObservationAtlasPanel(store: store, atlas: atlas)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private var statusLine: String {
        switch mode {
        case .transcript:
            return "\(transcript.cueCount) cues · \(transcript.coverageLine)"
        case .browse:
            return atlas.summaryLine
        }
    }

    @ViewBuilder private var transcriptPanel: some View {
        if transcript.cues.isEmpty {
            TranscriptMissingBar(store: store, transcript: transcript)
        } else {
            TranscriptSyncRail(store: store, transcript: transcript)
        }
    }
}

struct ObservationAtlasPanel: View {
    @ObservedObject var store: RecorderStore
    @ObservedObject var atlas: ObservationAtlasController

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            header
            switch atlas.status {
            case .notChecked:
                emptyState("Browse digest not checked", systemImage: "rectangle.stack")
            case .missing:
                emptyState("Browse digest not built", systemImage: "rectangle.stack.badge.minus")
            case .failed(let reason):
                emptyState(reason, systemImage: "xmark.octagon")
            case .ready:
                if atlas.hasBrowseData {
                    browseContent
                } else {
                    emptyState("Browse digest not built", systemImage: "rectangle.stack.badge.minus")
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .dtcCard(DTC.card, padding: 10)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Text("BROWSE DIGEST")
                    .font(.system(size: 10, weight: .semibold))
                    .tracking(0.8)
                    .foregroundStyle(DTC.textTertiary)
                Spacer()
                if let takeID = atlas.atlas?.takeId {
                    Text(takeID)
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(DTC.textTertiary)
                        .lineLimit(1)
                }
            }
            Text(atlas.summaryLine)
                .font(.system(size: 11))
                .foregroundStyle(DTC.textSecondary)
                .lineLimit(1)
            if !atlas.storageLine.isEmpty {
                Text(atlas.storageLine)
                    .font(.system(size: 10))
                    .foregroundStyle(DTC.textTertiary)
                    .lineLimit(1)
            }
        }
    }

    private var browseContent: some View {
        HStack(alignment: .top, spacing: 10) {
            ScrollView {
                VStack(alignment: .leading, spacing: 8) {
                    if !atlas.chapters.isEmpty {
                        chapterList
                    }
                    if !atlas.candidateClips.isEmpty {
                        clipList
                    }
                }
            }
            .frame(width: 174, alignment: .topLeading)

            ScrollView(.horizontal) {
                LazyHStack(alignment: .top, spacing: 8) {
                    ForEach(atlas.phraseCards) { card in
                        PhraseCardTile(
                            card: card,
                            takeRoot: store.activeTakeURL,
                            isActive: isActive(card)
                        ) {
                            store.seekPlayback(to: card.seekSeconds)
                        }
                    }
                }
                .padding(.vertical, 1)
            }
            .frame(maxHeight: .infinity)
        }
        .frame(maxHeight: .infinity)
    }

    private var chapterList: some View {
        VStack(alignment: .leading, spacing: 5) {
            listLabel("Chapters")
            ForEach(atlas.chapters.prefix(3)) { chapter in
                Button { store.seekPlayback(to: chapter.seekSeconds) } label: {
                    HStack(alignment: .top, spacing: 6) {
                        Image(systemName: "list.bullet.rectangle")
                            .font(.system(size: 11))
                            .foregroundStyle(DTC.accent)
                            .frame(width: 14)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(chapter.title ?? chapter.id)
                                .font(.system(size: 11, weight: .semibold))
                                .foregroundStyle(DTC.textPrimary)
                                .lineLimit(1)
                            Text(chapter.displayTime ?? dtcCueTime(chapter.seekSeconds))
                                .font(.system(size: 10, design: .monospaced))
                                .foregroundStyle(DTC.textTertiary)
                                .lineLimit(1)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 7)
                    .padding(.vertical, 6)
                    .background(RoundedRectangle(cornerRadius: 7).fill(DTC.card.opacity(0.72)))
                }
                .buttonStyle(.plain)
                .help("Seek to \(chapter.title ?? chapter.id)")
            }
        }
    }

    private var clipList: some View {
        VStack(alignment: .leading, spacing: 5) {
            listLabel("Clips")
            ForEach(atlas.candidateClips.prefix(3)) { clip in
                HStack(spacing: 5) {
                    Button { store.seekPlayback(to: clip.seekSeconds) } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(clip.title)
                                .font(.system(size: 11, weight: .semibold))
                                .foregroundStyle(DTC.textPrimary)
                                .lineLimit(1)
                            Text(clip.displayTime ?? dtcCueTime(clip.seekSeconds))
                                .font(.system(size: 10, design: .monospaced))
                                .foregroundStyle(DTC.textTertiary)
                                .lineLimit(1)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .buttonStyle(.plain)
                    .help("Seek to \(clip.title)")

                    if let url = clip.renderedClipURL(in: store.activeTakeURL) {
                        Button { NSWorkspace.shared.open(url) } label: {
                            Image(systemName: "play.rectangle")
                                .font(.system(size: 11))
                                .frame(width: 18, height: 18)
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(DTC.accent)
                        .help("Open rendered clip")
                    }
                }
                .padding(.horizontal, 7)
                .padding(.vertical, 6)
                .background(RoundedRectangle(cornerRadius: 7).fill(DTC.card.opacity(0.72)))
            }
        }
    }

    private func listLabel(_ title: String) -> some View {
        Text(title.uppercased())
            .font(.system(size: 9, weight: .semibold))
            .tracking(0.7)
            .foregroundStyle(DTC.textTertiary)
    }

    private func emptyState(_ text: String, systemImage: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: systemImage)
                .font(.system(size: 14))
                .foregroundStyle(DTC.textTertiary)
            Text(text)
                .font(.system(size: 11))
                .foregroundStyle(DTC.textSecondary)
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 8).fill(DTC.card.opacity(0.55)))
    }

    private func isActive(_ card: ObservationPhraseCard) -> Bool {
        let position = store.playbackPosition
        let start = card.seekSeconds
        let end = card.activeEndSeconds ?? ObservationTimeParser.endSeconds(from: card.displayTime) ?? start
        return position >= start - 0.08 && position <= end + 0.08
    }
}

struct PhraseCardTile: View {
    let card: ObservationPhraseCard
    let takeRoot: URL?
    let isActive: Bool
    var select: () -> Void

    var body: some View {
        Button(action: select) {
            VStack(alignment: .leading, spacing: 6) {
                representativeFrame
                    .frame(width: 168, height: 86)
                    .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
                    .overlay(alignment: .bottomLeading) {
                        Text(card.displayTime ?? dtcCueTime(card.seekSeconds))
                            .font(.system(size: 10, weight: .medium, design: .monospaced))
                            .monospacedDigit()
                            .foregroundStyle(.white)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 3)
                            .background(RoundedRectangle(cornerRadius: 5).fill(Color.black.opacity(0.68)))
                            .padding(5)
                    }

                Text(card.displayText)
                    .font(.system(size: 11))
                    .foregroundStyle(DTC.textPrimary)
                    .lineLimit(3)
                    .multilineTextAlignment(.leading)
                    .frame(width: 168, height: 45, alignment: .topLeading)

                HStack(spacing: 5) {
                    if let confidence = card.audioSummary?.speechConfidence {
                        miniPill("\(Int((confidence * 100).rounded()))%", icon: "waveform")
                    }
                    if let motion = card.visualSummary?.motionKind, !motion.isEmpty {
                        miniPill(motion.replacingOccurrences(of: "_", with: " "), icon: "eye")
                    }
                    if !(card.candidateClipRefs ?? []).isEmpty {
                        miniPill("clip", icon: "scissors")
                    }
                }
            }
            .padding(8)
            .background(RoundedRectangle(cornerRadius: 8, style: .continuous).fill(isActive ? DTC.accent.opacity(0.18) : DTC.card))
            .overlay(RoundedRectangle(cornerRadius: 8, style: .continuous).strokeBorder(isActive ? DTC.accent.opacity(0.58) : DTC.stroke, lineWidth: 1))
        }
        .buttonStyle(.plain)
        .help("Seek to \(card.displayTime ?? card.id)")
    }

    @ViewBuilder private var representativeFrame: some View {
        if let url = card.representativeFrameURL(in: takeRoot),
           let image = NSImage(contentsOf: url) {
            Image(nsImage: image)
                .resizable()
                .scaledToFill()
        } else {
            ZStack {
                Rectangle().fill(Color.black.opacity(0.58))
                Image(systemName: "photo")
                    .font(.system(size: 18))
                    .foregroundStyle(DTC.textTertiary)
            }
        }
    }

    private func miniPill(_ text: String, icon: String) -> some View {
        HStack(spacing: 3) {
            Image(systemName: icon).font(.system(size: 8))
            Text(text).font(.system(size: 9)).lineLimit(1)
        }
        .foregroundStyle(DTC.textSecondary)
        .padding(.horizontal, 5)
        .padding(.vertical, 2)
        .background(Capsule().fill(Color.white.opacity(0.05)))
    }
}
