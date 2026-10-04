# TourBuddy AI — Talk. Explore. Discover.

Voice-first AI travel companion built with SwiftUI and Agora Conversational AI.

TourBuddy AI lets users talk naturally with an AI tour guide to explore places, learn about destinations, calculate routes, and start navigation using Apple Maps.

## 🎥 Screenshot

<img width="502" height="952" alt="Screenshot 2026-10-04 at 10 04 06 PM" src="https://github.com/user-attachments/assets/433232d3-bd37-4dd5-bb54-6ef06f28e962" />

<img width="1206" height="2622" alt="Simulator Screenshot - iPhone 17 Pro - 2026-10-04 at 22 30 20" src="https://github.com/user-attachments/assets/ff8cd2cd-084f-4709-baba-1ec86b89f190" />

## ✨ Features

- 🎙️ Voice-first interaction using Agora Conversational AI
- 🤖 AI-powered conversational tour guide
- 📍 Google Maps MCP for place discovery
- 🔎 Explore destinations and places
- 🛣️ Calculate routes and travel distances
- 🗺️ Start navigation using Apple Maps
- 🔗 Google Maps links for explicit link requests
- 💬 Live conversation transcript
- 🔊 AI voice responses
- 💜 Dark/purple conversational UI with animated orb

## 🏗️ Architecture

```text
User speaks
    ↓
Agora Voice AI
    ↓
Speech-to-Text
    ↓
AI Conversational Agent
    ↓
Google Maps MCP
    ↓
Place / Route Information
    ↓
AI Voice Response
    ↓
TourBuddy SwiftUI
    ↓
Apple Maps Navigation
