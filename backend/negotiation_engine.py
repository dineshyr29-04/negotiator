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

CRITICAL NEGOTIATION RULES (DO NOT ACCEPT EASILY):
1. State and enforce the Company Stance clearly to the vendor!
2. In Round 1 or 2, DO NOT accept immediately even if the price looks reasonable! Always probe for added value, free delivery, payment terms, or a further discount before agreeing.
3. If vendor offers above target, explain why the company stance forbids it and apply BATNA leverage (${effective_batna:,.2f}) or upfront ACH settlement as trade-offs.
4. Only close and agree ('deal_closed') if Round >= 2 AND the vendor has conceded to or below the target cap (${current_target:,.2f}) or matched all company perks.
5. If human whisper instruction is given, you MUST incorporate it directly into your speech.

Return ONLY a valid JSON object with EXACTLY this structure:
{{
  "agent_speech": "What you speak aloud to the vendor (1-2 sentences clearly stating your stance and counter)",
  "counter_price": 1650.0,
  "detected_price": 1950.0,
  "company_stance_summary": "Brief 1-sentence interpretation of how company stance was applied",
  "dialogue_act": "Stance Assertion / BATNA Leverage / Package Bargaining / Concession Curve / Agreement",
  "sentiment": "Enforcing Company Stance / Vendor Yielding / Agreement Secured",
  "status": "counter_offered" or "deal_closed"
}}"""

        # Determine best available model for this Groq key
        target_model = "llama-3.3-70b-versatile"
        try:
            available_models = [m.id for m in client.models.list().data]
            for candidate in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama3-70b-8192", "llama3-8b-8192"]:
                if candidate in available_models:
                    target_model = candidate
                    break
        except Exception:
            pass

        response = client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Vendor just said: \"{user_text}\""}
            ],
            response_format={"type": "json_object"},
            temperature=0.35,
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

        # In round 1, do not immediately accept — enforce stance and demand perks
        if round_num == 1:
            counter = round(current_target * 0.95, 2)
            agent_speech = (
                f"{whisper_prefix}Our company stance is strict: our procurement cap is ${current_target:,.2f} and we require guaranteed terms. "
                f"We cannot proceed at ${detected_price:,.2f}. Could you come down to ${counter:,.2f} if we pay the full deposit today?"
            )
            dialogue_act = "Stance Assertion & Initial Anchor"
            status = "counter_offered"
            sentiment = "Enforcing Company Stance"
        elif detected_price <= current_target and round_num >= 2:
            dialogue_act = "Agreement & Package Closure"
            agent_speech = (
                f"{whisper_prefix}That meets our company stance. At ${detected_price:,.2f}, we are prepared to finalize. "
                "Please send the written agreement and our accounts team will release the payment today."
            )
            status = "deal_closed"
            counter = detected_price
            sentiment = "Agreement Secured"
        elif is_concession or (detected_price < last_offer):
            dialogue_act = "Calculated Concession & Package Trade"
            concession_step = round(zopa_spread * 0.35, 2)
            counter = round(current_target + concession_step, 2)
            agent_speech = (
                f"{whisper_prefix}We appreciate the movement down to ${detected_price:,.2f}, but our policy strictly limits us to ${current_target:,.2f}. "
                f"If you can meet us at ${counter:,.2f} with complimentary delivery, we can sign off immediately."
            )
            status = "counter_offered"
            sentiment = "Vendor Yielding"
        elif is_rejection:
            dialogue_act = "BATNA Leverage & Policy Defense"
            counter = round(current_target * 1.05, 2)
            agent_speech = (
                f"{whisper_prefix}I understand, but our corporate policy cannot approve ${detected_price:,.2f} when our alternative quote (BATNA) is ${effective_batna:,.2f}. "
                f"If we commit to an upfront ACH transfer, could we bridge the gap at ${counter:,.2f}?"
            )
            status = "leverage_applied"
            sentiment = "Overcoming Resistance"
        else:
            dialogue_act = "Exploratory Counter"
            counter = round(current_target + (zopa_spread * 0.4), 2)
            agent_speech = (
                f"{whisper_prefix}Our company stance requires all vendors to stay within our ${current_target:,.2f} benchmark. "
                f"Can we meet at ${counter:,.2f} to get this contract executed today?"
            )
            status = "counter_offered"
            sentiment = "Constructive Bargaining"

        return {
            "agent_speech": agent_speech,
            "counter_price": counter,
            "detected_price": detected_price,
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
