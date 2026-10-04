# TourBuddy AI — Talk. Explore. Discover.

Voice-first AI travel companion built with SwiftUI and Agora Conversational AI.

TourBuddy AI lets users talk naturally with an AI tour guide to explore places, learn about destinations, calculate routes, and start navigation using Apple Maps.

## 🎥 Screenshots

<img width="502" height="952" alt="Screenshot 2026-10-04 at 10 04 06 PM" src="https://github.com/user-attachments/assets/433232d3-bd37-4dd5-bb54-6ef06f28e962" />

<img width="502" height="952" alt="Screenshot 2026-10-04 at 10 38 15 PM" src="https://github.com/user-attachments/assets/7195a9d0-b281-49f6-855e-f73c64bbeee9" />

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
