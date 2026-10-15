import os
import io
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import edge_tts

app = FastAPI(title="The Negotiator - Voice AI Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-US-GuyNeural"
    rate: Optional[str] = "+0%"
    pitch: Optional[str] = "+0Hz"

class NegotiateRequest(BaseModel):
    vendor_name: str
    target_price: float
    vendor_offer: float
    message: str
    round: Optional[int] = 1

# Pre-seeded evidence-backed call records
MOCK_CALL_RECORDS = [
    {
        "id": "call-101",
        "vendor": "Apex Grand Hotel & Suites",
        "category": "Corporate Venue Booking",
        "initial_quote": 2200,
        "negotiated_price": 1650,
        "savings": 550,
        "savings_pct": 25.0,
        "status": "Deal Secured",
        "timestamp": "Today, 11:42 AM",
        "duration": "2m 14s",
        "perks": "Free high-speed Wi-Fi, late checkout & continental breakfast included",
        "audio_text": "Alright, if you sign the agreement by 4 PM today, we will honor $1,650 and throw in the complimentary breakfast vouchers.",
        "voice": "en-US-JennyNeural"
    },
    {
        "id": "call-102",
        "vendor": "BlueWave Office Supplies",
        "category": "Bulk Hardware & Chairs",
        "initial_quote": 1850,
        "negotiated_price": 1420,
        "savings": 430,
        "savings_pct": 23.2,
        "status": "Deal Secured",
        "timestamp": "Today, 10:15 AM",
        "duration": "1m 48s",
        "perks": "Free 2-day pallet delivery + 2 extra spare ergonomic chairs",
        "audio_text": "We can match your target at $1,420 if you commit to paying via ACH transfer today.",
        "voice": "en-US-GuyNeural"
    },
    {
        "id": "call-103",
        "vendor": "Gourmet Catering Co.",
        "category": "Event Catering (80 Guests)",
        "initial_quote": 3100,
        "negotiated_price": 2480,
        "savings": 620,
        "savings_pct": 20.0,
        "status": "Deal Secured",
        "timestamp": "Yesterday, 4:30 PM",
        "duration": "3m 05s",
        "perks": "Dessert bar upgrade included at zero surcharge",
        "audio_text": "I spoke with chef Marco. Because of your recurring schedule, we can lock you in at $2,480 flat.",
        "voice": "en-US-AriaNeural"
    }
]

@app.get("/api/voices")
async def get_popular_voices():
    return [
        {"id": "en-US-GuyNeural", "name": "Guy (Assertive Negotiator)", "gender": "Male", "accent": "US"},
        {"id": "en-US-JennyNeural", "name": "Jenny (Warm & Professional)", "gender": "Female", "accent": "US"},
        {"id": "en-US-AriaNeural", "name": "Aria (Executive & Polite)", "gender": "Female", "accent": "US"},
        {"id": "en-US-AndrewNeural", "name": "Andrew (Calm Confident)", "gender": "Male", "accent": "US"},
        {"id": "en-GB-RyanNeural", "name": "Ryan (British Diplomat)", "gender": "Male", "accent": "UK"},
        {"id": "en-IN-PrabhatNeural", "name": "Prabhat (Clear International)", "gender": "Male", "accent": "IN"}
    ]

@app.post("/api/tts")
async def text_to_speech(req: TTSRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    try:
        communicate = edge_tts.Communicate(
            text=req.text,
            voice=req.voice or "en-US-GuyNeural",
            rate=req.rate or "+0%",
            pitch=req.pitch or "+0Hz"
        )
        audio_stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])
        
        audio_stream.seek(0)
        return StreamingResponse(audio_stream, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

@app.get("/api/records")
async def get_records():
    return MOCK_CALL_RECORDS

@app.post("/api/negotiate")
async def negotiate_turn(req: NegotiateRequest):
    """
    Intelligent negotiation engine:
    Evaluates vendor speech/offer against target price and generates counter-strategy.
    """
    target = req.target_price
    offer = req.vendor_offer
    
    diff = offer - target
    if diff <= 0:
        reply_text = f"That sounds fair. We are happy to lock in ${offer:,.2f}. Please send over the written contract and we will approve immediately."
        outcome = "deal_closed"
        counter = offer
    elif diff < (target * 0.15):
        # Close to target - offer split
        counter = round(target + (diff * 0.4), 2)
        reply_text = f"We appreciate you coming down to ${offer:,.2f}. If you can meet us at ${counter:,.2f} with immediate payment today, we can close right now."
        outcome = "counter_offer"
    else:
        # Far from target - use leverage
        counter = round(target * 1.05, 2)
        reply_text = f"Thank you for the quote of ${offer:,.2f}. However, our procurement cap is ${target:,.2f}, and competing vendors have offered comparable packages within that range. Could you do ${counter:,.2f} if we commit to an upfront deposit?"
        outcome = "aggressive_counter"

    return {
        "reply_text": reply_text,
        "counter_price": counter,
        "outcome": outcome,
        "round": req.round + 1,
        "suggested_voice": "en-US-GuyNeural"
    }

# Mount static folder
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))
