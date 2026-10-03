import AgoraRtcKit
import AgoraRtmKit
import AgoraAgentClientToolkit

/// Owns the Agora RTC + RTM engines and `ConversationalAIAPIImpl`,
/// and conforms to `ConversationalAIAPIEventHandler` to surface transcript and
/// agent-state updates to the caller.
/// RTC carries the voice session; RTM connects the client toolkit to the agent's session events.
///
/// Lifecycle (the exact toolkit sequence):
///   1. create RTC engine, `loadAudioSettings()`, join channel
///   2. create + login RTM
///   3. build `ConversationalAIAPIImpl`, `addHandler`, `subscribeMessage`
///      BEFORE the backend `startAgent` call
///   4. on stop: `unsubscribeMessage` -> leave RTC -> logout RTM -> destroy
@MainActor
final class AgoraSession: NSObject, ConversationalAIAPIEventHandler {
    private var rtc: AgoraRtcEngineKit?
    private var rtm: AgoraRtmClientKit?
    private var api: ConversationalAIAPIImpl?
    private let onTranscript: (Transcript) -> Void
    private let onState: (AgentState) -> Void

    init(onTranscript: @escaping (Transcript) -> Void, onState: @escaping (AgentState) -> Void) {
        self.onTranscript = onTranscript
        self.onState = onState
    }

    func start(config c: AgentConfig) async throws {
        // 1. RTC engine.
        let rtc = AgoraRtcEngineKit.sharedEngine(withAppId: c.appId, delegate: nil)
        self.rtc = rtc

        // 2. RTM 2.0: init with (appId, userId) then login with the same token.
        let rtmConfig = AgoraRtmClientConfig(appId: c.appId, userId: c.uid)
        let rtm = try AgoraRtmClientKit(rtmConfig, delegate: nil)
        self.rtm = rtm
        try await withCheckedThrowingContinuation { (k: CheckedContinuation<Void, Error>) in
            rtm.login(c.token) { _, error in
                if let error { k.resume(throwing: error) } else { k.resume() }
            }
        }

        // 3. Build the toolkit, register self, and load audio best practices
        //    before joining the channel.
        let cfg = ConversationalAIAPIConfig(rtcEngine: rtc, rtmEngine: rtm, renderMode: .text)
        let api = ConversationalAIAPIImpl(config: cfg)
        api.addHandler(handler: self)
        self.api = api
        api.loadAudioSettings()

        // Publish the mic (so the agent hears the user) and subscribe to the
        // agent's audio. Without media options the legacy join publishes nothing,
        // so the agent receives silence and stays idle.
        let options = AgoraRtcChannelMediaOptions()
        options.clientRoleType = .broadcaster
        options.publishMicrophoneTrack = true
        options.autoSubscribeAudio = true
        rtc.joinChannel(byToken: c.token, channelId: c.channelName, uid: UInt(c.uid) ?? 0, mediaOptions: options)

        // 4. Subscribe to RTM messages BEFORE the agent is started so no
        //    transcript turns are missed.
        await withCheckedContinuation { (k: CheckedContinuation<Void, Never>) in
            api.subscribeMessage(channelName: c.channelName) { _ in k.resume() }
        }
    }

    func setMicMuted(_ muted: Bool) {
        rtc?.muteLocalAudioStream(muted)
    }

    func stop(channelName: String) {
        api?.unsubscribeMessage(channelName: channelName) { _ in }
        api?.destroy()
        rtc?.leaveChannel(nil)
        rtm?.logout { _, _ in }
        AgoraRtcEngineKit.destroy()
        api = nil
        rtc = nil
        rtm = nil
    }

    // MARK: - ConversationalAIAPIEventHandler (all 9 required methods)
    //
    // The toolkit invokes these from RTC/RTM callback queues, so they are
    // `nonisolated`; the two that mutate UI state hop to the main actor.

    nonisolated func onTranscriptUpdated(agentUserId: String, transcript: Transcript) {
        Task { @MainActor in self.onTranscript(transcript) }
    }
    nonisolated func onAgentStateChanged(agentUserId: String, event: StateChangeEvent) {
        let state = event.state
        Task { @MainActor in self.onState(state) }
    }
    nonisolated func onAgentInterrupted(agentUserId: String, event: InterruptEvent) {}
    nonisolated func onAgentMetrics(agentUserId: String, metrics: Metric) {}
    nonisolated func onAgentError(agentUserId: String, error: ModuleError) {}
    nonisolated func onMessageReceiptUpdated(agentUserId: String, messageReceipt: MessageReceipt) {}
    nonisolated func onMessageError(agentUserId: String, error: MessageError) {}
    nonisolated func onAgentVoiceprintStateChanged(agentUserId: String, event: VoiceprintStateChangeEvent) {}
    nonisolated func onDebugLog(log: String) {}
}
