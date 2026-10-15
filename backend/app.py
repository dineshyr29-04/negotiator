import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from voice_service import VoiceService
from negotiation_engine import NegotiationEngine
from scout_service import ScoutService
from database import HistoryDatabase

app = FastAPI(title="The Negotiator Backend Engine", version="1.1.0")

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
    voice: Optional[str] = "en-US-JennyNeural"
    rate: Optional[str] = "+0%"
    pitch: Optional[str] = "+0Hz"

class RoleplayRequest(BaseModel):
    user_speech: str
    target_price: float
    last_offer: float
    round: Optional[int] = 1
    batna_price: Optional[float] = 0.0
    whisper_instruction: Optional[str] = ""
    company_stance: Optional[str] = "Our company policy limits this category to our target budget with guaranteed terms"

class WarRoomRequest(BaseModel):
    category: str
    target_budget: float

class ScoutRequest(BaseModel):
    query: str
    target_budget: float

class RecordSaveRequest(BaseModel):
    merchant_name: str
    company_stance: Optional[str] = "Strict budget enforcement"
    target_price: float
    initial_offer: float
    final_price: float
    savings: float
    status: Optional[str] = "Deal Secured"
    dialogue_history: List[Dict[str, Any]]
    evidence_quote: Optional[str] = ""

# WebSocket Connection Manager for Multi-Device Sync (Phone <-> Laptop)
active_call_sockets: List[WebSocket] = []

async def broadcast_call_event(data: dict):
    for ws in list(active_call_sockets):
        try:
            await ws.send_json(data)
        except Exception:
            if ws in active_call_sockets:
                active_call_sockets.remove(ws)

@app.get("/api/voices")
async def get_voices():
    return VoiceService.get_voices()

@app.post("/api/tts")
async def text_to_speech(req: TTSRequest):
    try:
        stream = await VoiceService.synthesize(
            text=req.text,
            voice=req.voice or "en-US-JennyNeural",
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
    and returns the autonomous agent's spoken counter-speech with human intervention & company stance support.
    """
    evaluation = NegotiationEngine.evaluate_roleplay_turn(
        user_text=req.user_speech,
        current_target=req.target_price,
        last_offer=req.last_offer,
        round_num=req.round or 1,
        batna_price=req.batna_price or 0.0,
        whisper_instruction=req.whisper_instruction or "",
        company_stance=req.company_stance or "Our company policy limits this category to our target budget"
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
                merchant_name = data.get("merchant_name", "General Merchant")
                company_stance = data.get("company_stance", "Strict budget enforcement")

                eval_result = NegotiationEngine.evaluate_roleplay_turn(
                    user_text=user_text,
                    current_target=target_price,
                    last_offer=last_offer,
                    round_num=round_num,
                    batna_price=batna,
                    whisper_instruction=whisper,
                    company_stance=company_stance
                )

                await broadcast_call_event({
                    "type": "turn_update",
                    "merchant_name": merchant_name,
                    "company_stance": company_stance,
                    "vendor_speech": user_text,
                    "agent_speech": eval_result["agent_speech"],
                    "counter_price": eval_result["counter_price"],
                    "detected_price": eval_result["detected_price"],
                    "dialogue_act": eval_result.get("dialogue_act", "Bargaining"),
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

# MongoDB / History Storage Endpoints
@app.post("/api/records/save")
async def save_record(req: RecordSaveRequest):
    record_id = HistoryDatabase.save_record(req.dict())
    return {"status": "success", "record_id": record_id, "merchant": req.merchant_name}

@app.get("/api/merchants")
async def get_grouped_merchants():
    return HistoryDatabase.get_grouped_by_merchant()

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
    grouped = HistoryDatabase.get_grouped_by_merchant()
    flattened = []
    for merchant, records in grouped.items():
        for r in records:
            flattened.append({
                "id": r.get("created_at", "rec-1"),
                "vendor": merchant,
                "category": r.get("company_stance", "Procurement"),
                "initial_quote": r.get("initial_offer", 2000),
                "negotiated_price": r.get("final_price", 1600),
                "savings": r.get("savings", 400),
                "savings_pct": round(((r.get("initial_offer", 2000) - r.get("final_price", 1600)) / max(1, r.get("initial_offer", 2000))) * 100, 1),
                "status": r.get("status", "Deal Secured"),
                "timestamp": r.get("timestamp", "Recent"),
                "duration": "2m 10s",
                "perks": "Verified in MongoDB audit vault",
                "evidence_quote": r.get("evidence_quote", "Deal closed within budget threshold."),
                "voice": "en-US-GuyNeural",
                "transcripts": r.get("dialogue_history", [])
            })
    return flattened

# Dedicated Routes for Dual-Device Call Screen & Merchant History
@app.get("/call")
@app.get("/phone")
async def call_page():
    phone_path = os.path.join(STATIC_DIR, "phone.html")
    if os.path.exists(phone_path):
        return FileResponse(phone_path)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/history")
@app.get("/merchants")
async def history_page():
    hist_path = os.path.join(STATIC_DIR, "history.html")
    if os.path.exists(hist_path):
        return FileResponse(hist_path)
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
