# The Negotiator — Voice AI Agent (Backend Engine)

The autonomous procurement engine that conducts multi-agent voice negotiations, extracts verified discounts, and logs tamper-proof audio evidence.

## Features
- **100% Free Neural Voice Engine**: Uses Microsoft Edge Neural TTS via `edge-tts` (zero API keys, sub-400ms synthesis).
- **Interactive Roleplay API**: Real-time STT $\rightarrow$ Negotiation Reasoning $\rightarrow$ Spoken Counter-Response.
- **Multi-Vendor War Room**: Simulates concurrent 3-vendor negotiation rounds using game-theory leverage.
- **Scout Vendor Discovery**: Discovers vendor candidates, pricing baselines, and leverage points.
- **Verifiable Evidence Vault**: Stores timestamped agreements and generates audio proof snippets.

## Quick Start

### 1. Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the Server
```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 3. API Documentation
Open your browser to:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Endpoints
- `POST /api/tts`: Streaming MP3 neural speech generation.
- `POST /api/roleplay`: Judge/User mic objection handler.
- `POST /api/war-room`: 3-way concurrent vendor negotiation engine.
- `POST /api/scout`: Vendor candidate discovery.
- `GET /api/records`: Evidence vault records with verified audio quotes.
