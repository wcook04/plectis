import Dispatch
import Testing
@testable import DemoTakeConsoleApp

struct AudioRecordingContinuationStateTests {
    private enum ExpectedError: Error, Equatable {
        case failed
    }

    @Test
    func startContinuationCanFinishFromAudioQueue() async throws {
        let state = AudioRecordingContinuationState()

        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            state.setStart(continuation)
            DispatchQueue(label: "ai.workflow.demo-take-console.test-audio-start").async {
                state.finishStart(.success(()))
                state.finishStart(.success(()))
            }
        }
    }

    @Test
    func startContinuationPropagatesFailureFromAudioQueue() async {
        let state = AudioRecordingContinuationState()

        do {
            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
                state.setStart(continuation)
                DispatchQueue(label: "ai.workflow.demo-take-console.test-audio-start-failure").async {
                    state.finishStart(.failure(ExpectedError.failed))
                    state.finishStart(.success(()))
                }
            }
            Issue.record("Expected audio start continuation failure")
        } catch {
            #expect(error as? ExpectedError == .failed)
        }
    }

    @Test
    func stopContinuationCanFinishAfterStartContinuationAlreadyResolved() async throws {
        let state = AudioRecordingContinuationState()

        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            state.setStart(continuation)
            state.finishStart(.success(()))
        }

        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            state.setStop(continuation)
            DispatchQueue(label: "ai.workflow.demo-take-console.test-audio-stop").async {
                state.finishStop(.success(()))
                state.finishStop(.success(()))
            }
        }
    }
}
