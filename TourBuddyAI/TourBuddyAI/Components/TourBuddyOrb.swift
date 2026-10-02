//
//  TourBuddyOrb.swift
//  TourBuddyAI
//
//  Created by Sowmya on 01/10/26.
//

import SwiftUI

struct TourBuddyOrb: View {
    
    @State private var isAnimating = false
    
    var body: some View {
        ZStack {
            
            // Outer glow
            Circle()
                .fill(
                    RadialGradient(
                        colors: [
                            Color.purple.opacity(0.95),
                            Color.purple.opacity(0.55),
                            Color.blue.opacity(0.25),
                            Color.clear
                        ],
                        center: .center,
                        startRadius: 5,
                        endRadius: 150
                    )
                )
                .frame(width: 320, height: 320)
                .blur(radius: 12)
                .scaleEffect(isAnimating ? 1.12 : 0.92)
                .opacity(isAnimating ? 1.0 : 0.75)
            
            // Main orb
            Circle()
                .fill(
                    RadialGradient(
                        colors: [
                            Color.white.opacity(0.9),
                            Color.purple,
                            Color.blue.opacity(0.8)
                        ],
                        center: .topLeading,
                        startRadius: 10,
                        endRadius: 100
                    )
                )
                .frame(width: 120, height: 120)
                .shadow(
                    color: Color.purple.opacity(0.7),
                    radius: 25
                )
            
            // Sparkle
            Image(systemName: "sparkles")
                .font(.system(size: 38))
                .foregroundStyle(.white)
        }
        .onAppear {
            withAnimation(
                .easeInOut(duration: 1.8)
                .repeatForever(autoreverses: true)
            ) {
                isAnimating = true
            }
        }
    }
}

#Preview {
    ZStack {
        Color.black
            .ignoresSafeArea()
        
        TourBuddyOrb()
    }
}
