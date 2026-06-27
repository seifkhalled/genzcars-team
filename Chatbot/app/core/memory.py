import time
from typing import Optional


class SessionMemory:
    def __init__(self):
        self._sessions: dict[str, dict] = {}
        self.max_turns = 20
        self.ttl = 24 * 3600

    def get_or_create(self, session_token: str, user_id: Optional[str] = None,
                      context_ad_id: Optional[str] = None) -> dict:
        now = time.time()
        if session_token in self._sessions:
            session = self._sessions[session_token]
            session["last_active"] = now
            return session

        session = {
            "session_token": session_token,
            "user_id": user_id,
            "context_ad_id": context_ad_id,
            "history": [],
            "preferences": {},
            "turn_count": 0,
            "last_active": now,
            "created_at": now,
        }
        self._sessions[session_token] = session
        return session

    def get(self, session_token: str) -> Optional[dict]:
        session = self._sessions.get(session_token)
        if session and (time.time() - session["last_active"]) > self.ttl:
            del self._sessions[session_token]
            return None
        return session

    def add_message(self, session_token: str, role: str, content: str,
                    intent: Optional[str] = None) -> None:
        session = self._sessions.get(session_token)
        if not session:
            return
        session["history"].append({
            "role": role,
            "content": content,
            "intent": intent,
        })
        session["turn_count"] += 1
        session["last_active"] = time.time()
        if session["turn_count"] > self.max_turns:
            self._summarize_oldest(session)

    def _summarize_oldest(self, session: dict) -> None:
        oldest = session["history"][:10]
        text = "\n".join(
            f"{m['role']}: {m['content']}" for m in oldest
        )
        summary = f"[Previous conversation summary: {text[:200]}...]"
        session["history"] = [{"role": "system", "content": summary}] + session["history"][10:]

    def update_preferences(self, session_token: str, prefs: dict) -> None:
        session = self._sessions.get(session_token)
        if not session:
            return
        current = session.get("preferences", {})
        for key, val in prefs.items():
            if val is None:
                continue
            if isinstance(val, list):
                existing = current.get(key, [])
                for item in val:
                    if item not in existing:
                        existing.append(item)
                current[key] = existing
            else:
                current[key] = val
        session["preferences"] = current

    def cleanup(self) -> None:
        now = time.time()
        expired = [
            tok for tok, sess in self._sessions.items()
            if (now - sess["last_active"]) > self.ttl
        ]
        for tok in expired:
            del self._sessions[tok]
