import re
from typing import Dict, Any, List

class NegotiationEngine:
    """
    Implements dialogue strategy informed by EACL 2024 Survey ('Let's Negotiate!'):
    - ZOPA (Zone of Possible Agreement) Calculation
    - BATNA (Best Alternative to a Negotiated Agreement) Reference
    - Dialogue Acts Taxonomy (Anchor, Inquiry, Concession, Leverage, Agreement)
    """

    @staticmethod
    def extract_price(text: str) -> float | None:
        """Finds numeric price mentions like $1,500, 1500, etc."""
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
        Evaluates vendor response and determines the agent's next dialogue act and counter-offer.
        Incorporates user 'Whisper' interventions and BATNA leverage.
        """
        detected_price = cls.extract_price(user_text) or last_offer
        lower_text = user_text.lower()
        effective_batna = batna_price if batna_price > 0 else round(current_target * 1.15, 2)

        # Classify Vendor Dialogue Act (EACL 2024 Taxonomy)
        is_rejection = any(w in lower_text for w in ["no", "cannot", "impossible", "take it or leave", "firm", "final", "bottom line"])
        is_concession = any(w in lower_text for w in ["can do", "maybe", "discount", "meet in middle", "deal", "fine", "ok", "okay", "alright"])

        # Check if user injected a human whisper instruction
        whisper_prefix = ""
        if whisper_instruction.strip():
            whisper_prefix = f"[Human Intervened: '{whisper_instruction.strip()}'] "

        # ZOPA Check: Target to Vendor Offer
        zopa_spread = detected_price - current_target

        if detected_price <= current_target:
            dialogue_act = "Agreement & Package Closure"
            agent_speech = (
                f"{whisper_prefix}That is acceptable. At ${detected_price:,.2f}, we have an agreement. "
                "Please forward the written agreement and our procurement team will release the deposit today."
            )
            status = "deal_closed"
            counter = detected_price
            sentiment = "Agreement Secured"

        elif is_concession or (detected_price < last_offer):
            dialogue_act = "Calculated Concession (Tit-for-Tat)"
            # Concede small fraction towards the vendor
            concession_step = round(zopa_spread * 0.35, 2)
            counter = round(current_target + concession_step, 2)
            
            if whisper_instruction:
                agent_speech = f"{whisper_prefix}Understood. In light of that, could you meet us at ${counter:,.2f} if we finalize right now?"
            else:
                agent_speech = (
                    f"We appreciate the movement down to ${detected_price:,.2f}. "
                    f"If you can bridge the remaining difference at ${counter:,.2f} and include complimentary standard handling, "
                    "we will sign off on the PO immediately."
                )
            status = "counter_offered"
            sentiment = "Vendor Yielding"

        elif is_rejection:
            dialogue_act = "BATNA Leverage & Value Trade"
            counter = round(current_target * 1.06, 2)
            
            if whisper_instruction:
                agent_speech = f"{whisper_prefix}Regarding your quote, we have a firm alternative at ${effective_batna:,.2f}. Can you match ${counter:,.2f}?"
            else:
                agent_speech = (
                    f"I understand your position. However, our alternative option (BATNA) is currently quoted at ${effective_batna:,.2f}. "
                    f"We strongly prefer doing business with you—if we guarantee immediate ACH settlement, can you meet at ${counter:,.2f}?"
                )
            status = "leverage_applied"
            sentiment = "Overcoming Resistance"

        else:
            dialogue_act = "Exploratory Counter & Package Bargain"
            counter = round(current_target + (zopa_spread * 0.45), 2)
            agent_speech = (
                f"Thank you for clarifying. At ${detected_price:,.2f}, that sits just outside our budget ceiling. "
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
            "zopa_gap": zopa_spread,
            "round": round_num + 1
        }

    @classmethod
    def generate_war_room_simulation(cls, category: str, target: float) -> List[Dict[str, Any]]:
        """
        Simulates 3 parallel vendor phone calls applying EACL 2024 principles:
        Anchoring, BATNA comparisons, and package trade-offs.
        """
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
                "final_price": round(target * 0.98, 2),  # Winner below target!
                "rounds": [
                    {"speaker": "Vendor", "text": f"Normally we quote ${round(target * 1.45):,} for this specification."},
                    {"speaker": "Agent", "text": f"Apex has already offered us near ${round(target * 1.02):,}. If you beat that under ${round(target):,}, the contract is yours today."},
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
