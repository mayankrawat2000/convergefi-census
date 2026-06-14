"""
MongoDB connection and session persistence layer.
Database: convergefi
Collection: sessions

Session document schema:
{
    "_id": "<uuid session_id>",
    "title": "First 60 chars of first question",
    "created_at": datetime,
    "updated_at": datetime,
    "history": [                    # Used by LLM context
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ],
    "messages": [                   # Full UI messages for replay
        {
            "role": "user",
            "question": "...",
            "timestamp": "..."
        },
        {
            "role": "assistant",
            "answer": "...",
            "citations": [...],
            "artifacts": [...],
            "timestamp": "..."
        }
    ]
}
"""

import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

load_dotenv()

_MONGO_URI = os.getenv("MONGO_DB_SRV_CONNECTION_STRING", "")
_client: Optional[MongoClient] = None


def _get_client() -> MongoClient:
    global _client
    if _client is None:
        if not _MONGO_URI:
            raise RuntimeError("MONGO_DB_SRV_CONNECTION_STRING is not set in .env")
        _client = MongoClient(_MONGO_URI, serverSelectionTimeoutMS=5000)
        # Validate connection
        _client.admin.command("ping")
        print("✅ MongoDB connected successfully")
    return _client


def _get_collection():
    return _get_client()["convergefi"]["sessions"]


# ─── Public helpers ────────────────────────────────────────────────────────────

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Return the full session document, or None if not found."""
    try:
        return _get_collection().find_one({"_id": session_id})
    except Exception as e:
        print(f"[MongoDB] get_session error: {e}")
        return None


def load_history(session_id: str) -> List[Dict[str, Any]]:
    """Return the LLM context history list (role/content dicts)."""
    doc = get_session(session_id)
    if doc:
        return doc.get("history", [])
    return []


def save_turn(
    session_id: str,
    user_message: str,
    assistant_raw: str,
    citations: List[Dict] = None,
    artifacts: List[Dict] = None,
):
    """
    Upsert the session document with a new user+assistant turn.
    - history: minimal role/content pairs for LLM context
    - messages: full structured objects for UI replay
    """
    now = datetime.now(timezone.utc)
    citations = citations or []
    artifacts = artifacts or []

    # Extract clean answer text for UI display if assistant_raw is a JSON string
    answer_text = assistant_raw
    if isinstance(assistant_raw, str) and assistant_raw.strip().startswith("{"):
        try:
            import json
            parsed = json.loads(assistant_raw)
            answer_text = parsed.get("answer", assistant_raw)
            # Use parsed citations/artifacts if not already provided
            if not citations and "citations" in parsed:
                citations = parsed["citations"]
            if not artifacts and "artifacts" in parsed:
                artifacts = parsed["artifacts"]
        except Exception:
            pass

    # Append to history (LLM context)
    history_push = [
        {"role": "user",      "content": user_message},
        {"role": "assistant", "content": assistant_raw},
    ]

    # Append to messages (UI replay)
    messages_push = [
        {
            "role": "user",
            "question": user_message,
            "timestamp": now.isoformat(),
        },
        {
            "role": "assistant",
            "answer": answer_text,
            "citations": citations,
            "artifacts": artifacts,
            "timestamp": now.isoformat(),
        },
    ]

    try:
        col = _get_collection()
        existing = col.find_one({"_id": session_id}, {"title": 1})
        title = existing["title"] if existing else (user_message[:60] + ("…" if len(user_message) > 60 else ""))

        col.update_one(
            {"_id": session_id},
            {
                "$set":  {"updated_at": now, "title": title},
                "$setOnInsert": {"created_at": now},
                "$push": {
                    "history":  {"$each": history_push},
                    "messages": {"$each": messages_push},
                },
            },
            upsert=True,
        )
    except Exception as e:
        print(f"[MongoDB] save_turn error: {e}")


def list_sessions(limit: int = 50) -> List[Dict[str, Any]]:
    """Return sessions sorted newest first, projection for sidebar listing."""
    try:
        docs = _get_collection().find(
            {},
            {"_id": 1, "title": 1, "updated_at": 1, "created_at": 1}
        ).sort("updated_at", DESCENDING).limit(limit)
        results = []
        for d in docs:
            results.append({
                "session_id":  d["_id"],
                "title":       d.get("title", "Untitled"),
                "updated_at":  d.get("updated_at", d.get("created_at", datetime.now(timezone.utc))).isoformat(),
                "created_at":  d.get("created_at", datetime.now(timezone.utc)).isoformat(),
            })
        return results
    except Exception as e:
        print(f"[MongoDB] list_sessions error: {e}")
        return []


def delete_session(session_id: str) -> bool:
    """Delete a session document. Returns True if deleted."""
    try:
        result = _get_collection().delete_one({"_id": session_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"[MongoDB] delete_session error: {e}")
        return False


def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    """Return the full messages array for UI replay, parsing any raw JSON strings."""
    doc = get_session(session_id)
    if not doc:
        return []
        
    messages = doc.get("messages", [])
    cleaned_messages = []
    import json
    
    for m in messages:
        if m.get("role") == "assistant":
            answer = m.get("answer", "")
            citations = m.get("citations", [])
            artifacts = m.get("artifacts", [])
            
            # If the stored answer is raw JSON string, clean it up for backward compatibility
            if isinstance(answer, str) and answer.strip().startswith("{"):
                try:
                    parsed = json.loads(answer)
                    answer = parsed.get("answer", answer)
                    if not citations and "citations" in parsed:
                        citations = parsed["citations"]
                    if not artifacts and "artifacts" in parsed:
                        artifacts = parsed["artifacts"]
                except Exception:
                    pass
            
            cleaned_m = dict(m)
            cleaned_m["answer"] = answer
            cleaned_m["citations"] = citations
            cleaned_m["artifacts"] = artifacts
            cleaned_messages.append(cleaned_m)
        else:
            cleaned_messages.append(m)
            
    return cleaned_messages
