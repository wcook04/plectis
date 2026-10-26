import Dispatch
import Testing
@testable import DemoTakeConsoleApp

struct ScreenCaptureContinuationStateTests {
    private enum ExpectedError: Error, Equatable {
        case failed
    }

    @Test
    func testStartContinuationCanFinishFromScreenCaptureQueue() async throws {
        let state = ScreenCaptureContinuationState()

        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            state.setStart(continuation)
            DispatchQueue(label: "com.screenCaptureKit.streamQueue").async {
                state.finishStart(.success(()))
                state.finishStart(.success(()))
            }
        }
    }

    @Test
    func testStopContinuationPropagatesFailureFromScreenCaptureQueue() async {
        let state = ScreenCaptureContinuationState()

        do {
            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
                state.setStop(continuation)
                DispatchQueue(label: "com.screenCaptureKit.streamQueue").async {
                    state.finishStop(.failure(ExpectedError.failed))
                    state.finishStop(.success(()))
                }
            }
            Issue.record("Expected stop continuation failure")
        } catch {
            #expect(error as? ExpectedError == .failed)
        }
    }
}
