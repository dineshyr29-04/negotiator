import os
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "").strip()
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
LOCAL_BACKUP_FILE = os.path.join(DATA_DIR, "merchant_histories.json")

# Initialize MongoDB client if URI provided or accessible
mongo_client = None
db = None
collection = None

if MONGO_URI:
    try:
        from pymongo import MongoClient
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        # Check connection
        mongo_client.admin.command('ping')
        db = mongo_client["negotiator_db"]
        collection = db["merchant_records"]
        print("Connected to MongoDB successfully.")
    except Exception as e:
        print(f"MongoDB Notice: Could not connect to {MONGO_URI} ({e}). Using local robust storage fallback.")
        mongo_client = None
        collection = None

class HistoryDatabase:
    """
    Stores and retrieves multi-turn negotiation records grouped by Merchant Name.
    Uses MongoDB as primary storage, with automatic fallback to local JSON.
    """

    @classmethod
    def _read_local_records(cls) -> List[Dict[str, Any]]:
        if not os.path.exists(LOCAL_BACKUP_FILE):
            return []
        try:
            with open(LOCAL_BACKUP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @classmethod
    def _write_local_records(cls, records: List[Dict[str, Any]]):
        with open(LOCAL_BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

    @classmethod
    def save_record(cls, record_data: Dict[str, Any]) -> str:
        record = {
            "merchant_name": record_data.get("merchant_name", "General Merchant").strip() or "General Merchant",
            "company_stance": record_data.get("company_stance", "Strict budget enforcement with value trade-offs"),
            "target_price": float(record_data.get("target_price", 1500)),
            "initial_offer": float(record_data.get("initial_offer", 2000)),
            "final_price": float(record_data.get("final_price", 1650)),
            "savings": float(record_data.get("savings", 350)),
            "status": record_data.get("status", "deal_closed"),
            "dialogue_history": record_data.get("dialogue_history", []),
            "evidence_quote": record_data.get("evidence_quote", ""),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "created_at": datetime.now().isoformat()
        }

        # Try MongoDB first
        if collection is not None:
            try:
                res = collection.insert_one(record)
                return str(res.inserted_id)
            except Exception as e:
                print(f"MongoDB Insert failed: {e}. Writing to local file.")

        # Local storage fallback
        records = cls._read_local_records()
        records.insert(0, record)
        cls._write_local_records(records)
        return "local-id-" + str(len(records))

    @classmethod
    def get_grouped_by_merchant(cls) -> Dict[str, List[Dict[str, Any]]]:
        all_records = []
        if collection is not None:
            try:
                docs = list(collection.find({}, {"_id": 0}).sort("created_at", -1))
                all_records = docs
            except Exception as e:
                print(f"MongoDB query failed: {e}. Falling back to local storage.")
                all_records = cls._read_local_records()
        else:
            all_records = cls._read_local_records()

        # Seed with initial default records if empty
        if not all_records:
            all_records = cls._get_default_seed_records()
            cls._write_local_records(all_records)

        # Group by merchant_name
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in all_records:
            name = r.get("merchant_name", "Uncategorized Merchant")
            if name not in grouped:
                grouped[name] = []
            grouped[name].append(r)

        return grouped

    @classmethod
    def _get_default_seed_records(cls) -> List[Dict[str, Any]]:
        return [
            {
                "merchant_name": "Apex Grand Hotel & Suites",
                "company_stance": "Strict cap of $1,500 for 50 suites with complimentary breakfast",
                "target_price": 1500,
                "initial_offer": 2200,
                "final_price": 1650,
                "savings": 550,
                "status": "Deal Secured",
                "evidence_quote": "Alright, if you sign the agreement by 4 PM today, we will honor $1,650 and throw in the breakfast vouchers.",
                "timestamp": "2026-10-15 11:42:00",
                "dialogue_history": [
                    {"speaker": "Agent", "text": "Our company policy limits conference accommodations to $1,500. What is your volume rate?"},
                    {"speaker": "Vendor", "text": "Our list rate is $2,200. We can't go down that far."},
                    {"speaker": "Agent", "text": "We have an active alternative at $1,680. If we pay 100% upfront today, can we meet in the middle at $1,650?"},
                    {"speaker": "Vendor", "text": "Alright, if you sign the agreement by 4 PM today, we will honor $1,650 and throw in the breakfast vouchers."}
                ]
            },
            {
                "merchant_name": "BlueWave Office Supplies",
                "company_stance": "Zero freight fees + match rival catalog pricing",
                "target_price": 1400,
                "initial_offer": 1850,
                "final_price": 1420,
                "savings": 430,
                "status": "Deal Secured",
                "evidence_quote": "We can match your target at $1,420 if you commit to paying via ACH transfer today.",
                "timestamp": "2026-10-15 10:15:00",
                "dialogue_history": [
                    {"speaker": "Agent", "text": "Our mandate requires free delivery and a sub-$1,400 tier for 20 ergonomic chairs."},
                    {"speaker": "Vendor", "text": "List is $1,850 plus $150 freight."},
                    {"speaker": "Agent", "text": "We cannot absorb freight charges. Staples waives shipping for POs of this size."},
                    {"speaker": "Vendor", "text": "We can match your target at $1,420 if you commit to paying via ACH transfer today."}
                ]
            }
        ]
