from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SessionLog:
    """Represents a single log entry in a session."""
    timestamp: float
    level: str
    message: str


@dataclass
class SessionProgress:
    """Represents progress details for a session."""
    total_steps: int
    current_step: int
    percent: float


@dataclass
class SessionStats:
    """Represents aggregated statistics for a session."""
    duration_seconds: float
    steps_completed: int
    success: bool
    artifacts: Dict[str, str] = field(default_factory=dict)


@dataclass
class Session:
    """Represents an execution session."""
    session_id: str
    status: str
    created_at: float
    updated_at: float
    logs: List[SessionLog] = field(default_factory=list)
    progress: SessionProgress = field(default_factory=lambda: SessionProgress(total_steps=10, current_step=0, percent=0.0))
    stats: Optional[SessionStats] = None


class InMemorySessionService:
    """
    PUBLIC_INTERFACE
    A thread-safe in-memory session service to simulate execution sessions, progress, statistics, and logs.
    """
    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.RLock()

    # PUBLIC_INTERFACE
    def create_session(self, payload: Dict) -> Session:
        """Create a new mock session and start a background thread to simulate progress/logs."""
        with self._lock:
            session_id = str(uuid.uuid4())
            now = time.time()
            session = Session(
                session_id=session_id,
                status="RUNNING",
                created_at=now,
                updated_at=now,
            )
            session.logs.append(SessionLog(timestamp=now, level="INFO", message="Session created"))
            session.logs.append(SessionLog(timestamp=now, level="INFO", message=f"Received payload: {payload}"))
            self._sessions[session_id] = session

            # Start simulation in background
            t = threading.Thread(target=self._simulate_run, args=(session_id,), daemon=True)
            t.start()
            return session

    # PUBLIC_INTERFACE
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    # PUBLIC_INTERFACE
    def get_progress(self, session_id: str) -> Optional[SessionProgress]:
        """Get progress for a session."""
        s = self.get_session(session_id)
        return s.progress if s else None

    # PUBLIC_INTERFACE
    def get_stats(self, session_id: str) -> Optional[SessionStats]:
        """Get statistics for a session."""
        s = self.get_session(session_id)
        return s.stats if s else None

    # PUBLIC_INTERFACE
    def get_logs(self, session_id: str, level: Optional[str] = None, limit: Optional[int] = None) -> Optional[List[SessionLog]]:
        """Get logs for a session with optional level filter and limit."""
        s = self.get_session(session_id)
        if not s:
            return None
        logs = s.logs
        if level:
            logs = [l for l in logs if l.level.upper() == level.upper()]
        if limit is not None and limit >= 0:
            logs = logs[-limit:]
        return logs

    def _simulate_run(self, session_id: str) -> None:
        """Simulate a running session producing progress, logs and final stats."""
        steps = 10
        for i in range(1, steps + 1):
            time.sleep(0.2)
            with self._lock:
                s = self._sessions.get(session_id)
                if not s:
                    return
                s.progress.current_step = i
                s.progress.total_steps = steps
                s.progress.percent = round((i / steps) * 100.0, 2)
                s.updated_at = time.time()
                s.logs.append(SessionLog(timestamp=s.updated_at, level="INFO", message=f"Completed step {i}/{steps}"))
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return
            s.status = "COMPLETED"
            duration = s.updated_at - s.created_at if s.updated_at and s.created_at else steps * 0.2
            s.stats = SessionStats(
                duration_seconds=round(duration, 3),
                steps_completed=steps,
                success=True,
                artifacts={"report_url": f"/artifacts/{session_id}/report.html"}
            )
            s.updated_at = time.time()
            s.logs.append(SessionLog(timestamp=s.updated_at, level="INFO", message="Session completed"))

# Singleton service instance
session_service = InMemorySessionService()
