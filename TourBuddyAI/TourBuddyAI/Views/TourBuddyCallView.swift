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

            VStack(spacing: 20) {

                // Header
                Text("TourBuddy AI")
                    .font(.title2.bold())
                    .foregroundStyle(.white)

                // Orb
                TourBuddyOrb()

                // Agent state
                Text(agentStateText)
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.7))

                // Transcript
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {

                        ForEach(vm.turns, id: \.rowID) { turn in
                            TranscriptRow(turn: turn)
                        }
                    }
                    .padding(.horizontal)
                }
                .background(Color.clear)

                // Controls
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
                            Color.white.opacity(0.12),
                            in: RoundedRectangle(cornerRadius: 14)
                        )
                        .foregroundStyle(.white)
                    }

                    // End Tour
                    Button {
                        vm.end()
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
            }
            .padding()
        }
        .onAppear(perform: requestMicPermission)
    }

    private var agentStateText: String {

        switch vm.agentState {

        case .idle:
            return "Ready"

        case .silent:
            return "Listening..."

        case .listening:
            return "Listening..."

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

    private var isAgent: Bool {
        turn.type == .agent
    }

    var body: some View {

        HStack {

            if isAgent {
                agentBubble
                Spacer()
            } else {
                Spacer()
                userBubble
            }
        }
    }

    // MARK: Agent Bubble

    private var agentBubble: some View {

        VStack(alignment: .leading, spacing: 4) {

            Text("TourBuddy")
                .font(.caption.bold())
                .foregroundStyle(.white.opacity(0.6))

            Text(turn.text)
                .foregroundStyle(.white)
                .padding(12)
                .background(
                    Color.white.opacity(0.10),
                    in: RoundedRectangle(cornerRadius: 14)
                )
        }
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
