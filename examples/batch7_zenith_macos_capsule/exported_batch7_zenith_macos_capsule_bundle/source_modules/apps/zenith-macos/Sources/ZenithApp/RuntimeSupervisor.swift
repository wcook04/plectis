import Foundation

@MainActor
final class RuntimeSupervisor: ObservableObject {
    @Published private(set) var snapshot: RuntimeSnapshot

    init(initialSnapshot: RuntimeSnapshot = .empty) {
        self.snapshot = initialSnapshot
    }

    func replace(with snapshot: RuntimeSnapshot) {
        self.snapshot = snapshot
    }

    func markDisconnected(repoRoot: String) {
        snapshot = .disconnected(repoRoot: repoRoot)
    }
}
