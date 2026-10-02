//
//  TapToTalkButton.swift
//  TourBuddyAI
//
//  Created by Sowmya on 01/10/26.
//

import SwiftUI

struct TapToTalkButton: View {
    var body: some View {
        Button {
            // Agora voice will be connected later
        } label: {
            HStack(spacing: 10) {
                Image(systemName: "mic.fill")

                Text("Tap to Talk")
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
    }
}

#Preview {
    ZStack {
        Color.black.ignoresSafeArea()
        TapToTalkButton()
    }
}
