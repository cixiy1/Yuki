"""会话对象与持久化：JSONL 消息 + SQLite 索引。"""

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Session:
    def __init__(
        self,
        session_id: Optional[str] = None,
        name: str = "",
        messages: Optional[list[dict[str, Any]]] = None,
        created_at: Optional[str] = None,
    ):
        self.session_id = session_id or uuid.uuid4().hex
        self.name = name
        self.messages = messages or []
        self.approved_tools: dict[str, float] = {}
        self.created_at = created_at or _now()
        self.updated_at = self.created_at

    def approve(self, tool_name: str, minutes: Optional[int] = None) -> None:
        if minutes is None:
            self.approved_tools[tool_name] = float("inf")
        else:
            self.approved_tools[tool_name] = time.time() + minutes * 60

    def is_approved(self, tool_name: str) -> bool:
        expiry = self.approved_tools.get(tool_name)
        if expiry is None:
            return False
        return expiry == float("inf") or expiry > time.time()


@dataclass
class SessionMeta:
    session_id: str
    name: str
    created_at: str
    updated_at: str


class SessionStore:
    """会话保存/加载/列表。"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.sessions_dir = data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = data_dir / "sessions.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create(self, name: str = "") -> Session:
        return Session(name=name)

    def save(self, session: Session) -> None:
        path = self.sessions_dir / f"{session.session_id}.jsonl"
        lines = [json.dumps(msg, ensure_ascii=False) for msg in session.messages]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        session.updated_at = _now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    name = excluded.name,
                    updated_at = excluded.updated_at
                """,
                (session.session_id, session.name, session.created_at, session.updated_at),
            )

    def load(self, session_id: str) -> Optional[Session]:
        path = self.sessions_dir / f"{session_id}.jsonl"
        if not path.exists():
            return None
        messages: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                messages.append(json.loads(line))
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT name, created_at, updated_at FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        session = Session(session_id=session_id, name=row[0], messages=messages, created_at=row[1])
        session.updated_at = row[2]
        return session

    def list(self) -> list[SessionMeta]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT session_id, name, created_at, updated_at
                FROM sessions
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [SessionMeta(*row) for row in rows]
