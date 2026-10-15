# 🎙️ The Negotiator — Autonomous Voice AI Agent

An autonomous procurement voice AI agent that calls businesses, conducts multi-turn game-theory negotiation, supports real-time human intervention (whisper & live mic takeover), and returns verifiable evidence-backed recommendations.

Built for hackathons with **$0.00 infrastructure cost** using high-cadence neural voice synthesis and academic principles from the **EACL 2024 Survey: *"Let's Negotiate! A Survey of Negotiation Dialogue Systems"***.

---

## 🌟 Key Capabilities

### 1. 🎙️ 100% Free Neural Voice Synthesis & STT
* **Zero Telephony Tolls & API Fees**: Powered by Microsoft Edge Neural TTS (`en-US-GuyNeural`, `en-US-JennyNeural`, `en-US-AriaNeural`).
* **Sub-350ms Spoken Latency**: Fast, fluid, human-cadence conversation.
* **HTML5 Web Speech Integration**: Native browser speech recognition for zero-latency live voice interaction.

### 2. 🚨 Real-Time Human Intervention & Takeover
* **🤫 Whisper Mode (Human Co-Pilot)**: Send private tactical advice (e.g. *"Demand free 2-day delivery before agreeing"*) that the agent seamlessly weaves into its next spoken sentence.
* **🎙️ Live Mic Takeover**: Press one button to immediately mute the AI agent and patch your live microphone directly through to the caller.
* **Emergency Walkaway (E-Stop)**: Instant polite exit if a vendor refuses fair market terms.

### 3. 🧠 EACL 2024 Negotiation Framework
* **ZOPA Estimation**: Continuously calculates the *Zone of Possible Agreement* between your budget ceiling and the vendor's reservation threshold.
* **BATNA Benchmarking**: Cites verified alternative competitor quotes as objective leverage without hostile posturing.
* **Dialogue Acts Taxonomy**: Explicitly tracks negotiation acts: *Anchoring*, *Tit-for-Tat Concession Curves*, *Inquiry*, and *Package Bargaining* (trading volume/payment terms for discounts).

### 4. ⚡ Autonomous 3-Vendor War Room
* Dials 3 competing suppliers in parallel.
* Dynamically cross-references quotes to extract concessions.
* Crowns the optimal bidder based on total value (price + bundled perks).

### 5. 📜 Evidence Locker & Audit Vault
* Every agreed deal includes timestamped transcript lines.
* Clickable **"Play Audio Proof"** snippet that replays the exact verbal agreement.
* Printable **Executive Deal Memo** export for audit compliance.

---

## 🏗️ Architecture

```
                      ┌───────────────────────────────────────┐
                      │    Mobile & Desktop Command Center    │
                      │  (Warm Editorial Human UI + Call HUD) │
                      └──────────────────┬────────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
      [Speech-to-Text (STT)]                      [Live Intervention HUD]
   • Web Speech API (Microphone)               • Private Whisper Co-Pilot
   • Instant Transcription Stream              • Human Mic Takeover / E-Stop
                   │                                           │
                   └─────────────────────┬─────────────────────┘
                                         ▼
                     ┌───────────────────────────────────────┐
                     │     Negotiator State Engine (FastAPI) │
                     │  • ZOPA / BATNA Strategy (EACL 2024)  │
                     │  • Concession & Leverage Analyzer     │
                     └───────────────────┬───────────────────┘
                                         ▼
                     ┌───────────────────────────────────────┐
                     │    Free Edge Neural Voice Service     │
                     │  • Guy & Jenny Neural Audio Streaming │
                     │  • Sub-350ms Audio Byte Delivery      │
                     └───────────────────┬───────────────────┘
                                         ▼
                     ┌───────────────────────────────────────┐
                     │   Evidence Vault & Deal Verification  │
                     │  • Timestamped Audio Snippet Proof    │
                     │  • Executive Deal Memo Export         │
                     └───────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
* Python 3.10+
* Google Chrome or Microsoft Edge (for Web Speech STT)

### 1. Setup & Install
```bash
# Clone the repository
git clone https://github.com/dineshyr29-04/negotiator.git
cd negotiator

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install lightweight dependencies
pip install -r backend/requirements.txt
```

### 2. Run the Engine
```bash
python -m uvicorn app:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

### 3. Open in Browser
Open **`http://localhost:8000`** in Chrome or Edge.

---

## 📂 Repository Structure

```
negotiator/
├── backend/
│   ├── app.py                  # Main FastAPI application & REST endpoints
│   ├── negotiation_engine.py   # EACL 2024 multi-turn negotiation state machine
│   ├── voice_service.py        # 100% Free Neural TTS synthesis engine
│   ├── scout_service.py        # Autonomous vendor catalog discovery
│   ├── requirements.txt        # Backend dependencies
│   ├── .gitignore              # Dedicated backend ignore rules
│   └── README.md               # Backend module documentation
├── static/
│   └── index.html              # Mobile-responsive frontend with Call HUD & Evidence Vault
├── .gitignore                  # Global ignore rules
└── README.md                   # Project overview & documentation
```

---

## 📜 Academic Reference
This project implements the negotiation dialogue taxonomy and strategic models described in:
* **"Let's Negotiate! A Survey of Negotiation Dialogue Systems"** (Zhan et al., *Findings of the Association for Computational Linguistics: EACL 2024*, pages 2019–2031). [DOI: 10.18653/v1/2024.findings-eacl.136](https://aclanthology.org/2024.findings-eacl.136/)
