//
//  TourBuddyCallView.swift
//  TourBuddyAI
//
//  Created by Sowmya on 03/10/26.
//

import SwiftUI
import AVFoundation
import AgoraAgentClientToolkit

struct TourBuddyCallView: View {

    let vm: CallViewModel
    @Environment(\.openURL) private var openURL

    var body: some View {
        ZStack {

            // Background
            LinearGradient(
                colors: [
                    Color(red: 0.035, green: 0.025, blue: 0.10),
                    Color(red: 0.10, green: 0.045, blue: 0.20),
                    Color(red: 0.045, green: 0.07, blue: 0.16),
                    Color(red: 0.025, green: 0.025, blue: 0.07)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: 0) {

                // Keep the visual identity in its own fixed region above the conversation.
                VStack(spacing: 0) {
                    Text("TourBuddy AI")
                        .font(.title2.bold())
                        .foregroundStyle(.white)

                    TourBuddyOrb()
                        .scaleEffect(0.75)
                        .frame(height: 240)
                        .clipped()

                    Text(agentStateText)
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundStyle(.white.opacity(0.82))
                        .padding(.bottom, 14)
                }
                .background(alignment: .bottom) {
                    Ellipse()
                        .fill(Color.purple.opacity(0.12))
                        .frame(width: 280, height: 56)
                        .blur(radius: 24)
                        .offset(y: 20)
                        .allowsHitTesting(false)
                }

                // The transparent scroll view stays bounded between the orb and controls.
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 12) {

                            ForEach(vm.turns, id: \.rowID) { turn in
                                let mapLinkEvent = turn.rowID == mapLinkResponseRowID
                                    ? vm.mapLinkEvent
                                    : nil
                                TranscriptRow(turn: turn, mapLinkEvent: mapLinkEvent)
                                    .id(turn.rowID)
                            }
                        }
                        .padding(.horizontal)
                        .padding(.top, 60)
                        .padding(.bottom, 12)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color.clear)
                    .mask(alignment: .top) {
                        VStack(spacing: 0) {
                            LinearGradient(
                                stops: [
                                    .init(color: .clear, location: 0),
                                    .init(color: .black.opacity(0.35), location: 0.45),
                                    .init(color: .black, location: 1),
                                ],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                            .frame(height: 60)
                            Rectangle().fill(.black)
                        }
                    }
                    .onChange(of: vm.turns.last?.rowID, initial: true) { _, rowID in
                        guard let rowID else { return }
                        withAnimation {
                            proxy.scrollTo(rowID, anchor: .bottom)
                        }
                    }
                }

                // Controls remain outside the transcript's scroll region.
                HStack(spacing: 16) {

                    // Mute
                    Button {
                        vm.toggleMic()
                    } label: {
                        Label(
                            vm.micMuted ? "Unmute" : "Mute",
                            systemImage: vm.micMuted
                                ? "mic.slash.fill"
                                : "mic.fill"
                        )
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(
                            vm.micMuted ? Color.red.opacity(0.8) : Color.white.opacity(0.12),
                            in: RoundedRectangle(cornerRadius: 14)
                        )
                        .foregroundStyle(.white)
                    }

                    // End Tour
                    Button {
                        Task { await vm.end() }
                    } label: {
                        Label(
                            "End Tour",
                            systemImage: "phone.down.fill"
                        )
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(
                            Color.red.opacity(0.8),
                            in: RoundedRectangle(cornerRadius: 14)
                        )
                        .foregroundStyle(.white)
                    }
                }
                .padding(.top, 12)
            }
            .padding(.horizontal)
            .padding(.top, 8)
        }
        .onAppear(perform: requestMicPermission)
        // Only an explicit navigation action creates this event; ordinary place
        // questions, searches, and distance answers never trigger the Maps handoff.
        .onChange(of: navigationEventKey, initial: true) { _, newKey in
            guard newKey != nil,
                  let event = vm.navigationEvent,
                  let url = appleMapsURL(for: event) else { return }
            openURL(url)
        }
    }

    private var navigationEventKey: String? {
        guard let event = vm.navigationEvent else { return nil }
        return "\(event.channelName)|\(event.source ?? "")|\(event.latitude)|\(event.longitude)|\(event.label)"
    }

    private var mapLinkResponseRowID: String? {
        guard vm.mapLinkEvent != nil,
              let requestIndex = vm.turns.lastIndex(where: { turn in
                  guard turn.type == .user else { return false }
                  let text = turn.text.lowercased()
                  guard text.contains("google map") else { return false }
                  let asksForLink = text.contains("link") || text.contains("url")
                  let asksToShowPlace =
                      (text.contains("show") || text.contains("view")) &&
                      !["direction", "route", "navigate", "take me to", "go to", "open "]
                          .contains(where: { text.contains($0) })
                  return asksForLink || asksToShowPlace
              }) else { return nil }

        return vm.turns.dropFirst(requestIndex + 1)
            .first(where: { $0.type == .agent })?.rowID
    }

    private func appleMapsURL(for event: NavigationEvent) -> URL? {
        var components = URLComponents()
        components.scheme = "http"
        components.host = "maps.apple.com"
        var queryItems = [
            URLQueryItem(name: "daddr", value: "\(event.latitude),\(event.longitude)"),
        ]
        if let source = event.source?.trimmingCharacters(in: .whitespacesAndNewlines),
           !source.isEmpty {
            queryItems.append(URLQueryItem(name: "saddr", value: source))
        }
        components.queryItems = queryItems
        return components.url
    }

    private var agentStateText: String {
        if case .speaking = vm.agentState {
            return "Speaking..."
        }

        switch vm.agentState {

        case .idle:
            return "Ready"

        case .silent:
            return vm.micMuted ? "Muted" : "Listening"

        case .listening:
            return vm.micMuted ? "Muted" : "Listening"

        case .thinking:
            return "Thinking..."

        case .speaking:
            return "Speaking..."

        case .unknown:
            return "Connected"

        @unknown default:
            return "Connected"
        }
    }
}

private func requestMicPermission() {
    AVAudioApplication.requestRecordPermission { _ in }
}


// MARK: - Transcript Row

private struct TranscriptRow: View {

    let turn: Transcript
    let mapLinkEvent: MapLinkEvent?

    private var isAgent: Bool {
        turn.type == .agent
    }

    var body: some View {

        HStack {

            if isAgent {
                if !displayedText.isEmpty || mapLinkURL != nil {
                    agentBubble
                }
                Spacer()
            } else {
                Spacer()
                userBubble
            }
        }
    }

    // MARK: Agent Bubble

    private var agentBubble: some View {

        VStack(alignment: .leading, spacing: 8) {

            Text("TourBuddy")
                .font(.caption.bold())
                .foregroundStyle(.white.opacity(0.6))

            VStack(alignment: .leading, spacing: 6) {
                if !displayedText.isEmpty {
                    Text(displayedText)
                        .foregroundStyle(.white)
                }
                if let event = mapLinkEvent, let url = mapLinkURL {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(event.type == "apple_maps_link" ? "Apple Maps:" : "Google Maps:")
                            .foregroundStyle(.white)
                        Link(destination: url) {
                            Text(event.url)
                                .foregroundStyle(.cyan)
                                .underline()
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        .frame(maxWidth: 280, alignment: .leading)
                    }
                }
            }
        }
    }

    private var displayedText: String {
        guard isAgent else { return turn.text }
        return turn.text
            .replacingOccurrences(of: #"\[[^\]]+\]\([^)]*\)"#, with: "", options: .regularExpression)
            .replacingOccurrences(of: #"(?i)\[here\]"#, with: "", options: .regularExpression)
            .replacingOccurrences(of: #"(?i)\b(?:https?://)?(?:www\.)?(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/\S*)?"#, with: "", options: .regularExpression)
            .replacingOccurrences(of: #"\s{2,}"#, with: " ", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var mapLinkURL: URL? {
        guard let event = mapLinkEvent else { return nil }
        return URL(string: event.url)
    }

    // MARK: User Bubble

    private var userBubble: some View {

        VStack(alignment: .trailing, spacing: 4) {

            Text("You")
                .font(.caption.bold())
                .foregroundStyle(.white.opacity(0.6))

            Text(turn.text)
                .foregroundStyle(.white)
                .padding(12)
                .background(
                    Color.purple.opacity(0.45),
                    in: RoundedRectangle(cornerRadius: 14)
                )
        }
    }
}


// MARK: - Transcript ID

extension Transcript {

    var rowID: String {
        "\(turnId)-\(type.rawValue)"
    }
}
