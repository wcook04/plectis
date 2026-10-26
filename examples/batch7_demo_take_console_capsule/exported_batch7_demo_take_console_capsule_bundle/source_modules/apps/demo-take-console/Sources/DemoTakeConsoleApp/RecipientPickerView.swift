import SwiftUI

// MARK: - Recipient picker (contract §5)
//
// Behind a private menu, NOT inside the cue cards. Shows the generated recording
// overlay queue with explicit readiness sections: ready, needs authoring,
// completed.
// "Done" is a PROJECTION of queue status (take_id/video_path), not an independent
// checkbox DB. Selecting a recipient loads the deck, resets to the opening
// insert, updates all displays atomically, binds the next take, and persists
// across restart. Never switches recipients mid-recording.

struct RecipientPickerView: View {
    @ObservedObject var controller: RecipientCueOverlayController
    @State private var searchText = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            header
            searchField
            snapshotStrip
            if filteredRows.isEmpty {
                Text(controller.recipientRows.isEmpty ? "No recipients loaded." : "No recipients match this search.")
                    .font(.system(size: 13))
                    .foregroundStyle(DTC.textSecondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        section(title: "General Deliverables", rows: generalRows)
                        section(title: "Ready To Record", rows: readyRows)
                        section(title: "Needs Authoring", rows: authoringRows)
                        section(title: "Completed", rows: completedRows)
                    }
                }
            }
            Divider().overlay(DTC.stroke)
            sentinelStrip
        }
        .padding(16)
        .frame(width: 560, height: 640)
        .background(DTC.base)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Recipient Cue Plane")
                .font(.system(size: 16, weight: .bold))
                .foregroundStyle(DTC.textPrimary)
            Text("Private teleprompter. Excluded from capture by construction; prove it per session with the safety check.")
                .font(.system(size: 11))
                .foregroundStyle(DTC.textTertiary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var searchField: some View {
        HStack(spacing: 8) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(DTC.textTertiary)
            TextField("Search name or recipient ID", text: $searchText)
                .textFieldStyle(.plain)
                .font(.system(size: 13))
                .foregroundStyle(DTC.textPrimary)
            if !searchText.isEmpty {
                Button {
                    searchText = ""
                } label: {
                    Image(systemName: "xmark.circle.fill")
                }
                .buttonStyle(.plain)
                .foregroundStyle(DTC.textTertiary)
                .help("Clear search")
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(RoundedRectangle(cornerRadius: 7).fill(DTC.card))
        .overlay(RoundedRectangle(cornerRadius: 7).strokeBorder(DTC.stroke, lineWidth: 1))
    }

    private var snapshotStrip: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: snapshotIcon)
                .foregroundStyle(snapshotColor)
                .frame(width: 16)
            VStack(alignment: .leading, spacing: 2) {
                Text(snapshotTitle)
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(DTC.textPrimary)
                    .lineLimit(1)
                if let detail = snapshotDetail {
                    Text(detail)
                        .font(.system(size: 11))
                        .foregroundStyle(DTC.textTertiary)
                        .lineLimit(2)
                }
            }
            Spacer()
            Text(countSummary)
                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                .foregroundStyle(DTC.textSecondary)
        }
        .padding(10)
        .background(RoundedRectangle(cornerRadius: 7).fill(DTC.rail))
        .overlay(RoundedRectangle(cornerRadius: 7).strokeBorder(DTC.stroke, lineWidth: 1))
    }

    private func section(title: String, rows: [RecipientQueueRow]) -> some View {
        Group {
            if !rows.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(title)
                            .font(.system(size: 11, weight: .bold))
                            .foregroundStyle(DTC.textTertiary)
                        Spacer()
                        Text("\(rows.count)")
                            .font(.system(size: 11, weight: .semibold, design: .monospaced))
                            .foregroundStyle(DTC.textTertiary)
                    }
                    ForEach(rows) { row in
                        recipientRow(row)
                    }
                }
            }
        }
    }

    private func recipientRow(_ row: RecipientQueueRow) -> some View {
        Button {
            controller.selectRecipient(row.recipientID)
        } label: {
            VStack(alignment: .leading, spacing: 5) {
                HStack(spacing: 10) {
                    Text("\(row.recordingOrder)")
                        .font(.system(size: 12, weight: .bold, design: .monospaced))
                        .foregroundStyle(DTC.textTertiary)
                        .frame(width: 22, alignment: .trailing)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(row.recipientName)
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundStyle(row.isRecordable ? (isSelected(row) ? DTC.accent : DTC.textPrimary) : DTC.textSecondary)
                            .lineLimit(1)
                        Text(row.recipientID)
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(DTC.textTertiary)
                            .lineLimit(1)
                    }
                    Spacer()
                    readinessBadge(row)
                    if row.isDoneByProjection {
                        Label("done", systemImage: "checkmark.seal.fill")
                            .labelStyle(.iconOnly)
                            .foregroundStyle(DTC.success)
                            .help("take_id and video_path present (projected done)")
                    }
                    if isSelected(row) {
                        Image(systemName: "largecircle.fill.circle")
                            .foregroundStyle(DTC.accent)
                    }
                }
                if !row.isRecordable || !row.readinessDetail.isEmpty {
                    Text(row.readinessDetail)
                        .font(.system(size: 10))
                        .foregroundStyle(row.isRecordable ? DTC.textTertiary : DTC.attention)
                        .lineLimit(2)
                        .padding(.leading, 32)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected(row) ? DTC.accent.opacity(0.12) : (row.isRecordable ? DTC.card : DTC.rail))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .strokeBorder(isSelected(row) ? DTC.accent.opacity(0.4) : readinessColor(row).opacity(row.isRecordable ? 0.22 : 0.38), lineWidth: 1)
            )
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(controller.session.isRecording || !row.isRecordable)
        .help(row.isRecordable ? "Select \(row.recipientName)" : row.readinessDetail)
    }

    private func readinessBadge(_ row: RecipientQueueRow) -> some View {
        HStack(spacing: 4) {
            Image(systemName: readinessIcon(row))
            Text(row.readinessLabel)
                .lineLimit(1)
        }
        .font(.system(size: 10, weight: .semibold))
        .foregroundStyle(readinessColor(row))
    }

    private var sentinelStrip: some View {
        HStack(spacing: 10) {
            Button {
                Task { await controller.runSafetyCheck() }
            } label: {
                Text(controller.safetyCheckInProgress ? "Checking..." : "Run safety check")
            }
            .buttonStyle(DTCButtonStyle(kind: .primary))
            .disabled(controller.safetyCheckInProgress)

            if let receipt = controller.lastReceipt {
                Label(
                    receipt.passed ? "exclusion verified" : "LEAK / unverified",
                    systemImage: receipt.passed ? "checkmark.shield.fill" : "xmark.shield.fill"
                )
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(receipt.passed ? DTC.success : DTC.recording)
            } else {
                Text("not yet verified this session")
                    .font(.system(size: 12))
                    .foregroundStyle(DTC.attention)
            }
            Spacer()
        }
    }

    private func isSelected(_ row: RecipientQueueRow) -> Bool {
        controller.session.selectedRecipientID == row.recipientID
    }

    private var filteredRows: [RecipientQueueRow] {
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !query.isEmpty else { return controller.recipientRows }
        return controller.recipientRows.filter {
            $0.recipientName.lowercased().contains(query)
                || $0.recipientID.lowercased().contains(query)
        }
    }

    private var generalRows: [RecipientQueueRow] {
        filteredRows.filter { $0.kind == .generalDeliverable }
    }

    private var readyRows: [RecipientQueueRow] {
        filteredRows.filter { $0.kind == .outreachRecipient && $0.isRecordable && !$0.isDoneByProjection }
    }

    private var authoringRows: [RecipientQueueRow] {
        filteredRows.filter { $0.kind == .outreachRecipient && !$0.isRecordable && !$0.isDoneByProjection }
    }

    private var completedRows: [RecipientQueueRow] {
        filteredRows.filter { $0.kind == .outreachRecipient && $0.isDoneByProjection }
    }

    private var countSummary: String {
        "\(generalRows.count) general / \(readyRows.count) ready / \(authoringRows.count) authoring / \(completedRows.count) done"
    }

    private var snapshotTitle: String {
        guard let snapshot = controller.queueSnapshot else { return "No snapshot loaded" }
        switch snapshot.sourceKind {
        case .primaryGeneratedQueue:
            return "Primary generated queue · \(snapshot.countLine)"
        case .frozenTrancheFallback:
            return "Frozen tranche fallback · \(snapshot.countLine)"
        case .degradedFrozenTrancheFallback:
            return "Degraded fallback · \(snapshot.countLine)"
        }
    }

    private var snapshotDetail: String? {
        guard let snapshot = controller.queueSnapshot else { return controller.session.lastError }
        if let reason = snapshot.fallbackReason {
            return reason
        }
        if let generatedAt = snapshot.generatedAt {
            return "generated \(generatedAt)"
        }
        return snapshot.projectionHealthStatus
    }

    private var snapshotIcon: String {
        guard let snapshot = controller.queueSnapshot else { return "exclamationmark.triangle.fill" }
        return snapshot.isDegraded ? "exclamationmark.triangle.fill" : "checkmark.circle.fill"
    }

    private var snapshotColor: Color {
        guard let snapshot = controller.queueSnapshot else { return DTC.attention }
        return snapshot.isDegraded ? DTC.attention : DTC.success
    }

    private func readinessIcon(_ row: RecipientQueueRow) -> String {
        if row.isDoneByProjection { return "checkmark.seal.fill" }
        switch row.contentReadiness.status {
        case "full_cue_deck": return "text.badge.checkmark"
        case "insert_only_usable": return "text.append"
        case "authoring_incomplete": return "pencil.and.list.clipboard"
        default: return row.isRecordable ? "circle.dotted" : "exclamationmark.triangle.fill"
        }
    }

    private func readinessColor(_ row: RecipientQueueRow) -> Color {
        if row.isDoneByProjection { return DTC.success }
        switch row.contentReadiness.status {
        case "full_cue_deck": return DTC.success
        case "insert_only_usable": return DTC.accent
        case "authoring_incomplete": return DTC.attention
        default: return row.isRecordable ? DTC.textSecondary : DTC.recording
        }
    }
}
