//
//  HomeView.swift
//  TourBuddyAI
//
//  Created by Sowmya on 01/10/26.
//

import SwiftUI

struct HomeView: View {

    @State private var viewModel = CallViewModel()
    @State private var isConnecting = false

    var body: some View {

        Group {
            if viewModel.phase == .inCall {
                TourBuddyCallView(vm: viewModel)
            } else {
                homeContent
            }
        }
        .onChange(of: viewModel.phase) { _, phase in
            if phase == .idle {
                isConnecting = false
            }
        }
    }

    private var homeContent: some View {

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

            VStack {

                // Heading
                VStack(spacing: 8) {

                    Text("TourBuddy AI")
                        .font(.largeTitle)
                        .fontWeight(.bold)
                        .foregroundStyle(.white)

                    Text("Talk. Explore. Discover.")
                        .foregroundStyle(.white.opacity(0.7))
                }
                .frame(maxWidth: .infinity)
                .padding(.top, 40)

                Spacer()

                // Main voice area
                VStack(spacing: 28) {

                    TourBuddyOrb()

                    Button {
                        guard !isConnecting else { return }
                        isConnecting = true
                        Task {
                            await viewModel.connect()
                            if viewModel.phase != .inCall {
                                isConnecting = false
                            }
                        }
                    } label: {
                        HStack(spacing: 10) {
                            if isConnecting {
                                ProgressView()
                                    .tint(.white)
                            } else {
                                Image(systemName: "mic.fill")
                            }

                            Text(isConnecting ? "Connecting..." : "Tap to Talk")
                                .fontWeight(.semibold)
                        }
                        .foregroundStyle(.white)
                        .padding(.horizontal, 28)
                        .padding(.vertical, 15)
                        .background(
                            Capsule()
                                .fill(Color.white.opacity(0.12))
                        )
                        .overlay(
                            Capsule()
                                .stroke(Color.white.opacity(0.2), lineWidth: 1)
                        )
                    }
                    .disabled(isConnecting)
                }
                .frame(maxWidth: .infinity)

                Spacer()
            }
            .padding(.horizontal)
        }
    }
}

#Preview {
    HomeView()
}
