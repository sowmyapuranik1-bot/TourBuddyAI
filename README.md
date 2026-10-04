# TourBuddy AI — Talk. Explore. Discover.

Voice-first AI travel companion built with SwiftUI and Agora Conversational AI.

TourBuddy AI lets users talk naturally with an AI tour guide to explore places, learn about destinations, calculate routes, and start navigation using Apple Maps.

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
