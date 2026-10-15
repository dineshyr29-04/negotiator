from typing import List, Dict, Any

class ScoutService:
    @staticmethod
    def discover_vendors(query: str, target_budget: float) -> List[Dict[str, Any]]:
        """
        Discovers local business vendors and catalog pricing for negotiation.
        """
        clean_q = query.strip() or "Corporate Services"
        
        return [
            {
                "id": "scout-1",
                "name": f"{clean_q.title()} - Apex Group",
                "rating": 4.8,
                "reviews": 142,
                "phone": "+1 (555) 019-2831",
                "address": "Downtown Commerce Plaza, Suite 400",
                "estimated_quote": round(target_budget * 1.30, 2),
                "leverage_point": "Has surplus capacity this month"
            },
            {
                "id": "scout-2",
                "name": f"{clean_q.title()} - Metro Central",
                "rating": 4.9,
                "reviews": 289,
                "phone": "+1 (555) 024-8891",
                "address": "742 Industrial Blvd",
                "estimated_quote": round(target_budget * 1.40, 2),
                "leverage_point": "Compromises on price for cash upfront"
            },
            {
                "id": "scout-3",
                "name": f"{clean_q.title()} - Summit Alliance",
                "rating": 4.6,
                "reviews": 88,
                "phone": "+1 (555) 038-7712",
                "address": "1200 Westside Expressway",
                "estimated_quote": round(target_budget * 1.25, 2),
                "leverage_point": "Matches competitor written estimates"
            }
        ]
