"""Persistance de la memoire de conversation (SQLite)."""
import json
import sqlite3
from pathlib import Path


class MemoryStore:
    """Sauvegarde l'historique de conversation sur disque pour qu'il survive aux redemarrages."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT,
                tool_calls TEXT,
                tool_call_id TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        self._conn.commit()

    def load_messages(self) -> list[dict]:
        """Recharge l'historique persiste (hors system prompt, jamais stocke)."""
        rows = self._conn.execute(
            "SELECT role, content, tool_calls, tool_call_id FROM messages ORDER BY id"
        ).fetchall()

        messages = []
        for role, content, tool_calls, tool_call_id in rows:
            msg = {"role": role, "content": content}
            if tool_calls:
                msg["tool_calls"] = json.loads(tool_calls)
            if tool_call_id:
                msg["tool_call_id"] = tool_call_id
            messages.append(msg)
        return messages

    def replace_all(self, messages: list[dict]) -> None:
        """Remplace tout l'historique persiste par la liste donnee (hors system prompt)."""
        with self._conn:
            self._conn.execute("DELETE FROM messages")
            self._conn.executemany(
                "INSERT INTO messages (role, content, tool_calls, tool_call_id) VALUES (?, ?, ?, ?)",
                [
                    (
                        m.get("role"),
                        m.get("content"),
                        json.dumps(m["tool_calls"]) if m.get("tool_calls") else None,
                        m.get("tool_call_id"),
                    )
                    for m in messages
                ],
            )

    def close(self) -> None:
        self._conn.close()
