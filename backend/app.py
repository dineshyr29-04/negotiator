import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from voice_service import VoiceService
from negotiation_engine import NegotiationEngine
from scout_service import ScoutService

app = FastAPI(title="The Negotiator Backend Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-US-GuyNeural"
    rate: Optional[str] = "+0%"
    pitch: Optional[str] = "+0Hz"

class RoleplayRequest(BaseModel):
    user_speech: str
    target_price: float
    last_offer: float
    round: Optional[int] = 1
    batna_price: Optional[float] = 0.0
    whisper_instruction: Optional[str] = ""

class WarRoomRequest(BaseModel):
    category: str
    target_budget: float

class ScoutRequest(BaseModel):
    query: str
    target_budget: float

# WebSocket Connection Manager for Multi-Device Sync (Phone <-> Laptop)
active_call_sockets: List[WebSocket] = []

async def broadcast_call_event(data: dict):
    for ws in list(active_call_sockets):
        try:
            await ws.send_json(data)
        except Exception:
            if ws in active_call_sockets:
                active_call_sockets.remove(ws)

# Pre-seeded evidence records
EVIDENCE_RECORDS = [
    {
        "id": "deal-901",
        "vendor": "Apex Grand Hotel & Suites",
        "category": "Corporate Hotel Rooms (50 Units)",
        "initial_quote": 2200,
        "negotiated_price": 1650,
        "savings": 550,
        "savings_pct": 25.0,
        "status": "Deal Secured",
        "timestamp": "Today, 11:42 AM",
        "duration": "2m 14s",
        "perks": "Free high-speed Wi-Fi, late checkout & breakfast vouchers",
        "evidence_quote": "Alright, if you sign the agreement by 4 PM today, we will honor $1,650 and throw in the breakfast vouchers.",
        "voice": "en-US-JennyNeural",
        "transcripts": [
            {"time": "00:15", "speaker": "Agent", "text": "We need 50 suites for a national conference. What is your base quotation?"},
            {"time": "00:32", "speaker": "Vendor", "text": "Our standard conference group rate is $2,200 per night for that block."},
            {"time": "01:05", "speaker": "Agent", "text": "We have an offer from Marriott downtown for $1,800. Can you do $1,600 if we pay in full today?"},
            {"time": "01:42", "speaker": "Vendor", "text": "Alright, if you sign the agreement by 4 PM today, we will honor $1,650 and throw in the breakfast vouchers."}
        ]
    },
    {
        "id": "deal-902",
        "vendor": "BlueWave Office Supplies",
        "category": "Bulk Ergonomic Workstations",
        "initial_quote": 1850,
        "negotiated_price": 1420,
        "savings": 430,
        "savings_pct": 23.2,
        "status": "Deal Secured",
        "timestamp": "Today, 10:15 AM",
        "duration": "1m 48s",
        "perks": "Free 2-day pallet freight + 2 spare ergonomic chairs",
        "evidence_quote": "We can match your target at $1,420 if you commit to paying via ACH transfer today.",
        "voice": "en-US-GuyNeural",
        "transcripts": [
            {"time": "00:10", "speaker": "Agent", "text": "Inquiring about a 20-unit workstation bundle."},
            {"time": "00:25", "speaker": "Vendor", "text": "List price is $1,850 plus $150 freight shipping."},
            {"time": "00:58", "speaker": "Agent", "text": "We need free freight and a sub-$1,450 price point to execute the PO."},
            {"time": "01:22", "speaker": "Vendor", "text": "We can match your target at $1,420 if you commit to paying via ACH transfer today."}
        ]
    },
    {
        "id": "deal-903",
        "vendor": "Gourmet Catering Co.",
        "category": "Annual Gala Catering (80 Guests)",
        "initial_quote": 3100,
        "negotiated_price": 2480,
        "savings": 620,
        "savings_pct": 20.0,
        "status": "Deal Secured",
        "timestamp": "Yesterday, 4:30 PM",
        "duration": "3m 05s",
        "perks": "Artisan dessert station included without surcharge",
        "evidence_quote": "I spoke with chef Marco. Because of your recurring schedule, we can lock you in at $2,480 flat.",
        "voice": "en-US-AriaNeural",
        "transcripts": [
            {"time": "00:12", "speaker": "Agent", "text": "Requesting full catering package for our upcoming 80-person gala."},
            {"time": "00:40", "speaker": "Vendor", "text": "Full buffet plus dessert is standard at $3,100."},
            {"time": "01:20", "speaker": "Agent", "text": "We host 4 of these events every year. If you can do $2,450, we make you our exclusive caterer."},
            {"time": "02:18", "speaker": "Vendor", "text": "I spoke with chef Marco. Because of your recurring schedule, we can lock you in at $2,480 flat."}
        ]
    }
]

@app.get("/api/voices")
async def get_voices():
    return VoiceService.get_voices()

@app.post("/api/tts")
async def text_to_speech(req: TTSRequest):
    try:
        stream = await VoiceService.synthesize(
            text=req.text,
            voice=req.voice or "en-US-GuyNeural",
            rate=req.rate or "+0%",
            pitch=req.pitch or "+0Hz"
        )
        return StreamingResponse(stream, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/roleplay")
async def roleplay_turn(req: RoleplayRequest):
    """
    Evaluates what the judge/user spoke into the mic as the vendor,
    and returns the autonomous agent's spoken counter-speech with human intervention support.
    """
    evaluation = NegotiationEngine.evaluate_roleplay_turn(
        user_text=req.user_speech,
        current_target=req.target_price,
        last_offer=req.last_offer,
        round_num=req.round or 1,
        batna_price=req.batna_price or 0.0,
        whisper_instruction=req.whisper_instruction or ""
    )
    return evaluation

@app.websocket("/ws/call")
async def call_sync_websocket(websocket: WebSocket):
    """
    Real-Time WebSocket Sync between Phone (Handset) & Laptop (Command Terminal).
    Broadcasts spoken turns, AI reasoning, whisper prompts, and deal updates instantaneously!
    """
    await websocket.accept()
    active_call_sockets.append(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type == "vendor_speech":
                user_text = data.get("text", "")
                target_price = float(data.get("target_price", 1500))
                last_offer = float(data.get("last_offer", 2000))
                whisper = data.get("whisper", "")
                batna = float(data.get("batna_price", 1680))
                round_num = int(data.get("round", 1))

                eval_result = NegotiationEngine.evaluate_roleplay_turn(
                    user_text=user_text,
                    current_target=target_price,
                    last_offer=last_offer,
                    round_num=round_num,
                    batna_price=batna,
                    whisper_instruction=whisper
                )

                await broadcast_call_event({
                    "type": "turn_update",
                    "vendor_speech": user_text,
                    "agent_speech": eval_result["agent_speech"],
                    "counter_price": eval_result["counter_price"],
                    "detected_price": eval_result["detected_price"],
                    "dialogue_act": eval_result["dialogue_act"],
                    "status": eval_result["status"],
                    "sentiment": eval_result["sentiment"],
                    "round": eval_result["round"],
                    "whisper_used": whisper
                })

            elif event_type == "whisper":
                await broadcast_call_event({
                    "type": "whisper_alert",
                    "whisper": data.get("whisper", "")
                })

            elif event_type == "takeover":
                await broadcast_call_event({
                    "type": "takeover_state",
                    "is_human": data.get("is_human", False)
                })

    except WebSocketDisconnect:
        if websocket in active_call_sockets:
            active_call_sockets.remove(websocket)

@app.post("/api/war-room")
async def simulate_war_room(req: WarRoomRequest):
    simulation = NegotiationEngine.generate_war_room_simulation(
        category=req.category,
        target=req.target_budget
    )
    return simulation

@app.post("/api/scout")
async def scout_vendors(req: ScoutRequest):
    vendors = ScoutService.discover_vendors(
        query=req.query,
        target_budget=req.target_budget
    )
    return vendors

@app.get("/api/records")
async def get_records():
    return EVIDENCE_RECORDS

# Dedicated Routes for Dual-Device Call Screen
@app.get("/call")
@app.get("/phone")
async def call_page():
    phone_path = os.path.join(STATIC_DIR, "phone.html")
    if os.path.exists(phone_path):
        return FileResponse(phone_path)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# Static hosting
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "The Negotiator Backend is running. Open /docs for API schema."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
