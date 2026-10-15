import os
import re
import json
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# Optional Groq client initialization
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
groq_client = None
if GROQ_API_KEY:
    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"Notice: Groq initialization deferred: {e}")

class NegotiationEngine:
    """
    Implements dialogue strategy informed by EACL 2024 Survey ('Let's Negotiate!')
    Powered by Groq Llama 3 (sub-300ms) with seamless rule-based fallback.
    """

    @staticmethod
    def extract_price(text: str) -> float | None:
        match = re.search(r'\$?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+)', text)
        if match:
            clean = match.group(1).replace(',', '')
            try:
                return float(clean)
            except ValueError:
                return None
        return None

    @classmethod
    def evaluate_roleplay_turn(
        cls,
        user_text: str,
        current_target: float,
        last_offer: float,
        round_num: int,
        batna_price: float = 0.0,
        whisper_instruction: str = ""
    ) -> Dict[str, Any]:
        """
        Evaluates vendor response and determines agent's spoken counter-speech.
        Uses Groq LLM if GROQ_API_KEY is available, otherwise uses EACL rule engine.
        """
        # If Groq client is active, use high-speed LLM reasoning
        if groq_client:
            try:
                return cls._evaluate_with_groq(
                    user_text=user_text,
                    current_target=current_target,
                    last_offer=last_offer,
                    round_num=round_num,
                    batna_price=batna_price,
                    whisper_instruction=whisper_instruction
                )
            except Exception as e:
                print(f"Groq API call failed or timed out: {e}. Falling back to EACL rule engine.")

        # Fallback to EACL 2024 Rule Engine
        return cls._evaluate_rule_based(
            user_text=user_text,
            current_target=current_target,
            last_offer=last_offer,
            round_num=round_num,
            batna_price=batna_price,
            whisper_instruction=whisper_instruction
        )

    @classmethod
    def _evaluate_with_groq(
        cls,
        user_text: str,
        current_target: float,
        last_offer: float,
        round_num: int,
        batna_price: float,
        whisper_instruction: str
    ) -> Dict[str, Any]:
        effective_batna = batna_price if batna_price > 0 else round(current_target * 1.15, 2)
        
        system_prompt = f"""You are 'The Negotiator', an expert procurement voice AI agent negotiating live over the phone with a business vendor.
You speak naturally, confidently, with short conversational phone cadence (1 to 2 sentences maximum! No bullet points, no robotic speech).

Negotiation Parameters:
- Client Target Budget: ${current_target:,.2f}
- Alternative Competitor Quote (BATNA): ${effective_batna:,.2f}
- Current Round: {round_num}
- Human Co-Pilot Whisper Instruction: "{whisper_instruction}"

Rules from EACL 2024 ('Let's Negotiate!'):
1. If human whisper instruction is given, you MUST incorporate it into your reply.
2. If vendor price <= ${current_target:,.2f}, close the deal enthusiastically.
3. If vendor resists or rejects, cite your BATNA (${effective_batna:,.2f}) as polite leverage and offer package incentives (immediate payment, recurring renewal).
4. Do not concede in big leaps; concede incrementally.

Return ONLY a valid JSON object with EXACTLY this structure:
{{
  "agent_speech": "What you speak aloud to the vendor (1-2 sentences)",
  "counter_price": 1650.0,
  "detected_price": 1950.0,
  "dialogue_act": "BATNA Leverage / Concession Curve / Agreement",
  "sentiment": "Vendor Yielding / Agreement Secured / Firm Resistance",
  "status": "counter_offered" or "deal_closed"
}}"""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Vendor just said: \"{user_text}\""}
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=300
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        data["round"] = round_num + 1
        data["batna_price"] = effective_batna
        return data

    @classmethod
    def _evaluate_rule_based(
        cls,
        user_text: str,
        current_target: float,
        last_offer: float,
        round_num: int,
        batna_price: float,
        whisper_instruction: str
    ) -> Dict[str, Any]:
        detected_price = cls.extract_price(user_text) or last_offer
        lower_text = user_text.lower()
        effective_batna = batna_price if batna_price > 0 else round(current_target * 1.15, 2)

        is_rejection = any(w in lower_text for w in ["no", "cannot", "impossible", "take it or leave", "firm", "final", "bottom line"])
        is_concession = any(w in lower_text for w in ["can do", "maybe", "discount", "meet in middle", "deal", "fine", "ok", "okay", "alright"])

        whisper_prefix = ""
        if whisper_instruction.strip():
            whisper_prefix = f"Regarding {whisper_instruction.strip()}, "

        zopa_spread = detected_price - current_target

        if detected_price <= current_target:
            dialogue_act = "Agreement & Package Closure"
            agent_speech = (
                f"{whisper_prefix}That is acceptable. At ${detected_price:,.2f}, we have an agreement. "
                "Please send over the contract and our procurement team will approve the deposit today."
            )
            status = "deal_closed"
            counter = detected_price
            sentiment = "Agreement Secured"
        elif is_concession or (detected_price < last_offer):
            dialogue_act = "Calculated Concession (Tit-for-Tat)"
            concession_step = round(zopa_spread * 0.35, 2)
            counter = round(current_target + concession_step, 2)
            agent_speech = (
                f"{whisper_prefix}We appreciate the movement to ${detected_price:,.2f}. "
                f"If you can bridge the difference at ${counter:,.2f} and include complimentary standard handling, we will sign off immediately."
            )
            status = "counter_offered"
            sentiment = "Vendor Yielding"
        elif is_rejection:
            dialogue_act = "BATNA Leverage & Value Trade"
            counter = round(current_target * 1.06, 2)
            agent_speech = (
                f"{whisper_prefix}I understand your position. However, our alternative option (BATNA) is currently quoted at ${effective_batna:,.2f}. "
                f"We prefer working with you—if we guarantee immediate ACH settlement, can you meet at ${counter:,.2f}?"
            )
            status = "leverage_applied"
            sentiment = "Overcoming Resistance"
        else:
            dialogue_act = "Exploratory Counter & Package Bargain"
            counter = round(current_target + (zopa_spread * 0.45), 2)
            agent_speech = (
                f"{whisper_prefix}Thank you for clarifying. At ${detected_price:,.2f}, that sits just outside our budget ceiling. "
                f"Can we meet in the middle at ${counter:,.2f} for an immediate order?"
            )
            status = "counter_offered"
            sentiment = "Constructive Bargaining"

        return {
            "agent_speech": agent_speech,
            "counter_price": counter,
            "detected_price": detected_price,
            "status": status,
            "sentiment": sentiment,
            "dialogue_act": dialogue_act,
            "batna_price": effective_batna,
            "round": round_num + 1
        }

    @classmethod
    def generate_war_room_simulation(cls, category: str, target: float) -> List[Dict[str, Any]]:
        vendors_data = [
            {
                "vendor_name": "Apex Premier Logistics",
                "phone": "+1 (555) 392-1044",
                "initial_quote": round(target * 1.35, 2),
                "final_price": round(target * 1.02, 2),
                "rounds": [
                    {"speaker": "Vendor", "text": f"Our corporate base quote is ${round(target * 1.35):,}."},
                    {"speaker": "Agent", "text": f"We are working with a strict budget of ${round(target):,}. What volume concession can you offer?"},
                    {"speaker": "Vendor", "text": f"With a 24-hour signature, I can authorize ${round(target * 1.02):,}."}
                ],
                "perks": "Free expedited tracking & insured transit",
                "evidence_quote": f"I can authorize ${round(target * 1.02):,} with 24-hour signature.",
                "dialogue_act": "Concession via Settlement Speed",
                "voice_vendor": "en-US-JennyNeural"
            },
            {
                "vendor_name": "Metro Skyline Services",
                "phone": "+1 (555) 781-9021",
                "initial_quote": round(target * 1.45, 2),
                "final_price": round(target * 0.98, 2),
                "rounds": [
                    {"speaker": "Vendor", "text": f"Normally we quote ${round(target * 1.45):,} for this specification."},
                    {"speaker": "Agent", "text": f"Apex offered us near ${round(target * 1.02):,}. If you beat that under ${round(target):,}, the contract is yours today."},
                    {"speaker": "Vendor", "text": f"Understood. We will match and beat at ${round(target * 0.98):,} flat, and bundle the priority package."}
                ],
                "perks": "Priority tier upgrade + zero cancellation fee",
                "evidence_quote": f"We will beat at ${round(target * 0.98):,} flat, and bundle the priority package.",
                "dialogue_act": "Competitive BATNA Undercut (Winner)",
                "voice_vendor": "en-US-AriaNeural",
                "is_winner": True
            },
            {
                "vendor_name": "Summit Global Supply",
                "phone": "+1 (555) 204-8832",
                "initial_quote": round(target * 1.25, 2),
                "final_price": round(target * 1.15, 2),
                "rounds": [
                    {"speaker": "Vendor", "text": f"Our rate is fixed at ${round(target * 1.25):,}."},
                    {"speaker": "Agent", "text": f"Can you match ${round(target):,} for immediate purchase order execution?"},
                    {"speaker": "Vendor", "text": f"Bottom line is ${round(target * 1.15):,}, we cannot go lower."}
                ],
                "perks": "Standard warranty only",
                "evidence_quote": f"Bottom line is ${round(target * 1.15):,}, we cannot go lower.",
                "dialogue_act": "Firm Reservation Threshold (Walkaway Candidate)",
                "voice_vendor": "en-GB-RyanNeural"
            }
        ]

        results = []
        for v in vendors_data:
            savings = round(v["initial_quote"] - v["final_price"], 2)
            savings_pct = round((savings / v["initial_quote"]) * 100, 1)
            results.append({
                **v,
                "savings": savings,
                "savings_pct": savings_pct,
                "status": "Deal Won (Best ZOPA)" if v.get("is_winner") else "Negotiation Complete"
            })
        return results
