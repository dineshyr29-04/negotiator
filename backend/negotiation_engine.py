import re
from typing import Dict, Any, List

class NegotiationEngine:
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
    def evaluate_roleplay_turn(cls, user_text: str, current_target: float, last_offer: float, round_num: int) -> Dict[str, Any]:
        """
        Evaluates a real human (judge or user) speaking as the vendor.
        Calculates leverage, sentiment, and the agent's spoken response.
        """
        detected_price = cls.extract_price(user_text) or last_offer
        lower_text = user_text.lower()

        # Check for absolute rejection
        is_rejection = any(w in lower_text for w in ["no", "cannot", "impossible", "take it or leave", "firm", "final"])
        # Check for concessions
        is_concession = any(w in lower_text for w in ["can do", "maybe", "discount", "meet in middle", "deal", "fine", "ok", "okay", "alright"])

        if detected_price <= current_target:
            agent_speech = (
                f"That works for us. At ${detected_price:,.2f}, you have a deal! "
                "Please send over the contract confirmation and we will process the upfront deposit right away."
            )
            status = "deal_closed"
            counter = detected_price
            sentiment = "Agreement Secured"
        elif is_concession or (detected_price < last_offer):
            gap = detected_price - current_target
            counter = round(current_target + (gap * 0.35), 2)
            agent_speech = (
                f"We appreciate your flexibility in coming down to ${detected_price:,.2f}. "
                f"If you can meet us just a bit further at ${counter:,.2f} and include the standard delivery, "
                "we can sign the paperwork immediately today."
            )
            status = "counter_offered"
            sentiment = "Vendor Yielding"
        elif is_rejection:
            # Apply leverage: competitor or upfront cash
            counter = round(current_target * 1.08, 2)
            agent_speech = (
                f"I completely understand your position. However, our budget committee has capped this at ${current_target:,.2f}. "
                f"If we guarantee 100% immediate payment by ACH and agree to a 12-month recurring renewal, "
                f"could you bridge the gap to ${counter:,.2f}?"
            )
            status = "leverage_applied"
            sentiment = "Overcoming Resistance"
        else:
            counter = round(current_target + (detected_price - current_target) * 0.5, 2)
            agent_speech = (
                f"Thanks for clarifying. Considering the volume we're committing to today, "
                f"${detected_price:,.2f} is slightly outside our threshold. Can we split the difference at ${counter:,.2f}?"
            )
            status = "counter_offered"
            sentiment = "Constructive Bargaining"

        return {
            "agent_speech": agent_speech,
            "counter_price": counter,
            "detected_price": detected_price,
            "status": status,
            "sentiment": sentiment,
            "round": round_num + 1
        }

    @classmethod
    def generate_war_room_simulation(cls, category: str, target: float) -> List[Dict[str, Any]]:
        """
        Simulates 3 parallel vendor phone calls with multi-round haggling and verified evidence.
        """
        vendors_data = [
            {
                "vendor_name": "Apex Premier Logistics",
                "phone": "+1 (555) 392-1044",
                "initial_quote": round(target * 1.35, 2),
                "final_price": round(target * 1.02, 2),
                "rounds": [
                    {"speaker": "Vendor", "text": f"Our standard corporate rate for this package is ${round(target * 1.35):,}."},
                    {"speaker": "Agent", "text": f"We have multiple bids under ${round(target):,}. We can book today if you can get closer to our target."},
                    {"speaker": "Vendor", "text": f"If you guarantee payment within 24 hours, I can authorize ${round(target * 1.02):,}."}
                ],
                "perks": "Free expedited tracking & insured transit",
                "evidence_quote": f"I can authorize ${round(target * 1.02):,} with 24h payment.",
                "voice_vendor": "en-US-JennyNeural"
            },
            {
                "vendor_name": "Metro Skyline Services",
                "phone": "+1 (555) 781-9021",
                "initial_quote": round(target * 1.45, 2),
                "final_price": round(target * 0.98, 2),  # Winner!
                "rounds": [
                    {"speaker": "Vendor", "text": f"Normally we quote ${round(target * 1.45):,} for this volume."},
                    {"speaker": "Agent", "text": f"Apex offered us near ${round(target * 1.05):,}. If you can beat that and stay under ${round(target):,}, we sign with Metro."},
                    {"speaker": "Vendor", "text": f"Alright, you drive a hard bargain. We will do ${round(target * 0.98):,} flat, and throw in the premium upgrade."}
                ],
                "perks": "Complimentary premium tier upgrade + zero cancellation fee",
                "evidence_quote": f"We will do ${round(target * 0.98):,} flat, with the premium upgrade.",
                "voice_vendor": "en-US-AriaNeural",
                "is_winner": True
            },
            {
                "vendor_name": "Summit Global Supply",
                "phone": "+1 (555) 204-8832",
                "initial_quote": round(target * 1.25, 2),
                "final_price": round(target * 1.15, 2),
                "rounds": [
                    {"speaker": "Vendor", "text": f"We are priced at ${round(target * 1.25):,}."},
                    {"speaker": "Agent", "text": f"Can you match ${round(target):,} for an immediate purchase order?"},
                    {"speaker": "Vendor", "text": f"Best we can do is ${round(target * 1.15):,}, our margins are tight."}
                ],
                "perks": "Standard warranty only",
                "evidence_quote": f"Best we can do is ${round(target * 1.15):,}.",
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
                "status": "Deal Won" if v.get("is_winner") else "Negotiation Complete"
            })
        return results
