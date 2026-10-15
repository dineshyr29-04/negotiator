import io
import asyncio
from typing import Optional
import edge_tts

# Curated neural voices
VOICE_CATALOG = {
    "agent_assertive": "en-US-GuyNeural",
    "agent_diplomatic": "en-US-AndrewNeural",
    "vendor_corporate": "en-US-JennyNeural",
    "vendor_polite": "en-US-AriaNeural",
    "vendor_firm": "en-GB-RyanNeural",
}

class VoiceService:
    @staticmethod
    async def synthesize(text: str, voice: str = "en-US-GuyNeural", rate: str = "+0%", pitch: str = "+0Hz") -> io.BytesIO:
        """
        Synthesizes text into realistic human speech using Microsoft Edge Neural TTS.
        100% Free, zero API key needed.
        """
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Text cannot be empty")

        communicate = edge_tts.Communicate(
            text=clean_text,
            voice=voice,
            rate=rate,
            pitch=pitch
        )
        audio_stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])
        
        audio_stream.seek(0)
        return audio_stream

    @staticmethod
    def get_voices():
        return [
            {"id": "en-US-GuyNeural", "name": "Guy (Assertive Negotiator)", "role": "Agent", "gender": "Male"},
            {"id": "en-US-AndrewNeural", "name": "Andrew (Calm Procurement)", "role": "Agent", "gender": "Male"},
            {"id": "en-US-JennyNeural", "name": "Jenny (Vendor Rep)", "role": "Vendor", "gender": "Female"},
            {"id": "en-US-AriaNeural", "name": "Aria (Executive Vendor)", "role": "Vendor", "gender": "Female"},
            {"id": "en-GB-RyanNeural", "name": "Ryan (British Supplier)", "role": "Vendor", "gender": "Male"}
        ]
