import os
import re
import json
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

def get_groq_client():
    """Dynamically retrieves or re-initializes Groq client if GROQ_API_KEY is updated in .env"""
    load_dotenv(override=True)
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key or key == "your_groq_api_key_here":
        return None
    try:
        from groq import Groq
        return Groq(api_key=key)
    except Exception as e:
        print(f"Notice: Groq client creation failed: {e}")
        return None

class NegotiationEngine:
    """
    Implements dialogue strategy informed by EACL 2024 Survey ('Let's Negotiate!')
    Powered by Groq Llama 3 (sub-300ms) with Company Stance Enforcement.
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
        whisper_instruction: str = "",
        company_stance: str = "Our company policy requires strict budget compliance and bundled value"
    ) -> Dict[str, Any]:
        """
        Evaluates vendor response and determines agent's spoken counter-speech.
        Enforces company stance and prevents premature agreement on early rounds.
        """
        client = get_groq_client()
        if client:
            try:
                return cls._evaluate_with_groq(
                    client=client,
                    user_text=user_text,
                    current_target=current_target,
                    last_offer=last_offer,
                    round_num=round_num,
                    batna_price=batna_price,
                    whisper_instruction=whisper_instruction,
                    company_stance=company_stance
                )
            except Exception as e:
                print(f"Notice: Groq Llama 3 API error: {e}. Gracefully falling back to EACL rule engine.")

        return cls._evaluate_rule_based(
            user_text=user_text,
            current_target=current_target,
            last_offer=last_offer,
            round_num=round_num,
            batna_price=batna_price,
            whisper_instruction=whisper_instruction,
            company_stance=company_stance
        )

    @classmethod
    def _evaluate_with_groq(
        cls,
        client: Any,
        user_text: str,
        current_target: float,
        last_offer: float,
        round_num: int,
        batna_price: float,
        whisper_instruction: str,
        company_stance: str
    ) -> Dict[str, Any]:
        effective_batna = batna_price if batna_price > 0 else round(current_target * 1.15, 2)
        
        system_prompt = f"""You are 'The Negotiator', an expert procurement voice AI agent negotiating live over the phone with a business vendor.
You speak naturally, confidently, with short conversational phone cadence (1 to 2 sentences maximum! No bullet points, no robotic speech).

Company Procurement Mandate & Stance:
"{company_stance}"

Negotiation Parameters:
- Client Target Budget Cap: ${current_target:,.2f}
- Alternative Competitor Quote (BATNA): ${effective_batna:,.2f}
- Current Negotiation Round: {round_num}
- Human Co-Pilot Whisper Instruction: "{whisper_instruction}"

STRICT PHASE RULES (MANDATORY):
1. REJECTION PHASE (If vendor's price > ${current_target:,.2f}):
   - You MUST EXPLICITLY REJECT their price! Say: "I must reject that offer" or "We cannot accept $X as our company stance strictly caps this at ${current_target:,.2f}."
   - Till the vendor actually drops to ${current_target:,.2f}, KEEP REJECTING and hold your stance firmly.
   - Set "phase": "REJECTING_ABOVE_CAP" and "phase_label": "🛑 Phase 1: Firm Rejection (Above ${current_target:,.2f} Cap)"

2. DEAL CONFIRMATION PHASE (When vendor concedes to ${current_target:,.2f} or matches company perks):
   - DO NOT agree silently! You MUST ASK the vendor: "That meets our company requirement of ${current_target:,.2f}. Do we have a deal? Shall I send the written contract to lock this in?"
   - Set "phase": "ASKING_CONFIRMATION" and "phase_label": "🤝 Phase 2: Stance Met — Asking Deal Confirmation"
   - Set "status": "deal_pending"

3. DEAL FINALIZED PHASE (If vendor says yes, agrees, or confirms):
   - Say: "Deal finalized! I will dispatch the formal agreement and release payment. Thank you!"
   - Set "phase": "DEAL_FINALIZED" and "phase_label": "✅ Phase 3: Deal Locked & Finalized"
   - Set "status": "deal_closed"

Return ONLY a valid JSON object with EXACTLY this structure:
{{
  "agent_speech": "What you speak aloud to the vendor (1-2 sentences clearly stating your stance, rejection, or confirmation question)",
  "counter_price": 1500.0,
  "detected_price": 1950.0,
  "phase": "REJECTING_ABOVE_CAP" / "ASKING_CONFIRMATION" / "DEAL_FINALIZED",
  "phase_label": "Brief human readable badge name for the UI",
  "company_stance_summary": "Brief 1-sentence interpretation of how company stance was applied",
  "dialogue_act": "Rejection & Stance Assertion / BATNA Leverage / Confirmation Inquiry / Deal Agreement",
  "sentiment": "Firm Rejection / Negotiating / Deal Confirmed",
  "status": "counter_offered" or "deal_pending" or "deal_closed"
}}"""

        # Primary model requested: qwen/qwen3.8-27b on Groq
        target_model = "qwen/qwen3.8-27b"
        try:
            available_models = [m.id for m in client.models.list().data]
            if "qwen/qwen3.8-27b" not in available_models:
                # Fallback candidates
                for candidate in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-20b"]:
                    if candidate in available_models:
                        target_model = candidate
                        break
        except Exception:
            pass

        completion = client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Vendor just said: \"{user_text}\""}
            ],
            temperature=0.6,
            max_completion_tokens=2048,
            top_p=0.95
        )

        content = completion.choices[0].message.content or ""
        
        # Robust JSON extraction
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            data = json.loads(json_match.group(0))
        else:
            data = json.loads(content)

        data["round"] = round_num + 1
        data["batna_price"] = effective_batna
        if "agent_speech" not in data or not data["agent_speech"]:
            data["agent_speech"] = f"Our company stance is firm at ${current_target:,.2f}. We cannot accept anything higher. Can you meet our budget?"
        if "phase" not in data:
            data["phase"] = "REJECTING_ABOVE_CAP" if (data.get("detected_price", 2000) > current_target) else "ASKING_CONFIRMATION"
            data["phase_label"] = "🛑 Phase 1: Firm Rejection" if data["phase"] == "REJECTING_ABOVE_CAP" else "🤝 Phase 2: Verifying Agreement"
        return data

    @classmethod
    def _evaluate_rule_based(
        cls,
        user_text: str,
        current_target: float,
        last_offer: float,
        round_num: int,
        batna_price: float,
        whisper_instruction: str,
        company_stance: str
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

        # Check if vendor is confirming deal
        is_confirmation = any(w in lower_text for w in ["yes", "deal", "agreed", "agree", "done", "confirm", "confirmed", "lock it in", "sounds good"])

        if detected_price <= current_target:
            if is_confirmation or round_num >= 3:
                # Phase 3: Finalized
                dialogue_act = "Agreement & Package Closure"
                agent_speech = (
                    f"{whisper_prefix}Deal finalized at ${detected_price:,.2f}! "
                    "Thank you, I will send our written contract and dispatch the payment immediately."
                )
                phase = "DEAL_FINALIZED"
                phase_label = f"✅ Phase 3: Deal Locked at ${detected_price:,.2f}"
                status = "deal_closed"
                counter = detected_price
                sentiment = "Agreement Secured"
            else:
                # Phase 2: Ask for confirmation
                dialogue_act = "Confirmation Inquiry"
                agent_speech = (
                    f"{whisper_prefix}That meets our company stance of ${detected_price:,.2f}. "
                    "Do we have a confirmed deal? Shall I finalize and send the agreement?"
                )
                phase = "ASKING_CONFIRMATION"
                phase_label = f"🤝 Phase 2: Stance Met (${detected_price:,.2f}) — Asking Confirmation"
                status = "deal_pending"
                counter = detected_price
                sentiment = "Asking Confirmation"
        else:
            # Phase 1: REJECT! Offers higher than company stance are rejected!
            phase = "REJECTING_ABOVE_CAP"
            phase_label = f"🛑 Phase 1: Firm Rejection (Above ${current_target:,.2f} Cap)"
            status = "counter_offered"
            counter = current_target
            sentiment = "Firm Rejection (Policy Cap)"
            dialogue_act = "Stance Rejection & Policy Enforcement"
            agent_speech = (
                f"{whisper_prefix}I must reject ${detected_price:,.2f}. Our company policy strictly enforces a ${current_target:,.2f} budget cap with guaranteed terms. "
                f"We cannot approve anything above this limit. Can you meet our ${current_target:,.2f} budget?"
            )
            status = "counter_offered"
            sentiment = "Constructive Bargaining"

        return {
            "agent_speech": agent_speech,
            "counter_price": counter,
            "detected_price": detected_price,
            "phase": phase,
            "phase_label": phase_label,
            "company_stance_summary": f"Enforced {company_stance}",
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
                    {"speaker": "Agent", "text": f"Our company policy caps this at ${round(target):,}. What volume concession can you authorize?"},
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
                    {"speaker": "Agent", "text": f"Our mandate requires beating Apex's quote of ${round(target * 1.02):,}. Match under ${round(target):,} and you have the deal."},
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
                    {"speaker": "Agent", "text": f"Our company stance cannot approve that without matching competitor rates."},
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
