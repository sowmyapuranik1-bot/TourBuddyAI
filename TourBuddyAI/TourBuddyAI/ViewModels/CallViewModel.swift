import Foundation
import Observation
import AgoraAgentClientToolkit

/// `@Observable` call state machine. Owns the `BackendApi` and the
/// `AgoraSession`, drives connect/end, and upserts transcript turns by `turnId`.
@MainActor
@Observable
final class CallViewModel {
    enum Phase: Equatable {
        case idle
        case connecting
        case inCall
        case error(String)
    }

    private(set) var phase: Phase = .idle
    private(set) var turns: [Transcript] = []
    private(set) var agentState: AgentState = .idle
    // Observable by the call view when the backend poller receives a navigation event.
    private(set) var navigationEvent: NavigationEvent?
    var micMuted = false

    private let api: BackendApi
    private var session: AgoraSession?
    private var agentId: String?
    private var channelName: String?
    @ObservationIgnored
    nonisolated(unsafe) private var navigationPollingTask: Task<Void, Never>?

    init() {
        let urlString = (Bundle.main.object(forInfoDictionaryKey: "AGENT_BACKEND_URL") as? String)
            ?? "http://localhost:8000"
        let baseURL = URL(string: urlString) ?? URL(string: "http://localhost:8000")!
        self.api = BackendApi(baseURL: baseURL)
    }

    deinit {
        navigationPollingTask?.cancel()
    }

    func connect() async {
        guard phase == .idle || isErrorPhase else { return }
        phase = .connecting
        do {
            let config = try await api.getConfig()
            self.channelName = config.channelName
            startNavigationPolling(channelName: config.channelName)

            let session = AgoraSession(
                onTranscript: { [weak self] transcript in self?.upsert(transcript) },
                onState: { [weak self] state in self?.agentState = state }
            )
            self.session = session
            try await session.start(config: config)

            let rtcUid = Int(config.agentUid) ?? 0
            let userUid = Int(config.uid) ?? 0
            self.agentId = try await api.startAgent(
                channelName: config.channelName, rtcUid: rtcUid, userUid: userUid
            )
            phase = .inCall
        } catch {
            navigationPollingTask?.cancel()
            navigationPollingTask = nil
            phase = .error(error.localizedDescription)
        }
    }

    func end() {
        navigationPollingTask?.cancel()
        navigationPollingTask = nil
        if let channelName { session?.stop(channelName: channelName) }
        if let agentId {
            Task { try? await api.stopAgent(agentId: agentId) }
        }
        session = nil
        agentId = nil
        channelName = nil
        turns = []
        agentState = .idle
        navigationEvent = nil
        micMuted = false
        phase = .idle
    }

    func toggleMic() {
        micMuted.toggle()
        session?.setMicMuted(micMuted)
    }

    private var isErrorPhase: Bool {
        if case .error = phase { return true }
        return false
    }

    private func startNavigationPolling(channelName: String) {
        guard navigationPollingTask == nil else { return }

        navigationPollingTask = Task { [weak self] in
            while !Task.isCancelled {
                guard let api = self?.api else { return }
                do {
                    if let event = try await api.getNavigationEvent(channelName: channelName) {
                        self?.navigationEvent = event
                    }
                } catch {
                    // Keep polling; transient request errors should not end the call.
                }

                do {
                    try await Task.sleep(nanoseconds: 1_000_000_000)
                } catch {
                    break
                }
            }
        }
    }

    /// Upsert a transcript row. A user utterance and the agent's reply share a
    /// `turnId` but differ by `type`, so they are distinct rows — key on both,
    /// otherwise the agent reply overwrites the user's line. Order by turn, then
    /// user before agent within a turn.
    private func upsert(_ transcript: Transcript) {
        if let index = turns.firstIndex(where: {
            $0.turnId == transcript.turnId && $0.type == transcript.type
        }) {
            turns[index] = transcript
        } else {
            turns.append(transcript)
        }
        turns.sort {
            if $0.turnId != $1.turnId { return $0.turnId < $1.turnId }
            return ($0.type == .user ? 0 : 1) < ($1.type == .user ? 0 : 1)
        }
    }
}
