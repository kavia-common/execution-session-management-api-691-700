from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


MAX_LOG_LINES = 1000

# Case status constants
CASE_NOTRUN = "NOTRUN"
CASE_SCHEDULE = "SCHEDULE"
CASE_TESTING = "TESTING"
CASE_PASS = "PASS"
CASE_FAIL = "FAIL"
CASE_SKIP = "SKIP"


@dataclass
class LogLine:
    timestamp: float
    level: str
    message: str


@dataclass
class Progress:
    total_steps: int = 0
    current_step: int = 0

    @property
    def percent(self) -> float:
        if self.total_steps <= 0:
            return 0.0
        return round((self.current_step / max(1, self.total_steps)) * 100.0, 2)


@dataclass
class Stats:
    duration_seconds: float = 0.0
    success: bool = False
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    artifacts: Dict[str, str] = field(default_factory=dict)


@dataclass
class SessionState:
    session_id: str
    status: str = "PENDING"
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    progress: Progress = field(default_factory=Progress)
    stats: Stats = field(default_factory=Stats)
    logs: List[LogLine] = field(default_factory=list)
    # New fields for Phase 4
    ui_lock: bool = False
    # map case name -> status
    case_status: Dict[str, str] = field(default_factory=dict)
    # current test info
    current_case_name: Optional[str] = None
    current_case_doc: Optional[str] = None


class StateManager:
    """
    PUBLIC_INTERFACE
    Thread-safe in-memory state manager for execution sessions.
    Stores per-session: status, timestamps, progress, stats, logs (bounded), artifacts,
    per-case statuses, current test info, and UI lock state.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}
        self._lock = threading.RLock()

    # PUBLIC_INTERFACE
    def create_session(self) -> SessionState:
        """Create a new session with a unique id and initial state."""
        with self._lock:
            sid = str(uuid.uuid4())
            now = time.time()
            s = SessionState(session_id=sid, status="PENDING", created_at=now, updated_at=now)
            self._sessions[sid] = s
            self.append_log(sid, "INFO", "Session created.")
            return s

    # PUBLIC_INTERFACE
    def get(self, session_id: str) -> Optional[SessionState]:
        """Get session by id."""
        with self._lock:
            return self._sessions.get(session_id)

    # PUBLIC_INTERFACE
    def append_log(self, session_id: str, level: str, message: str) -> None:
        """Append a log message, keeping at most MAX_LOG_LINES per session."""
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return
            s.logs.append(LogLine(timestamp=time.time(), level=level.upper(), message=str(message)))
            # bound the logs
            if len(s.logs) > MAX_LOG_LINES:
                s.logs[:] = s.logs[-MAX_LOG_LINES:]
            s.updated_at = time.time()

    # PUBLIC_INTERFACE
    def set_status(self, session_id: str, status: str) -> None:
        """Update session status."""
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return
            s.status = status
            s.updated_at = time.time()

    # PUBLIC_INTERFACE
    def set_artifacts(self, session_id: str, artifacts: Dict[str, str]) -> None:
        """Set artifacts map for a session."""
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return
            s.stats.artifacts.update(artifacts or {})
            s.updated_at = time.time()

    # PUBLIC_INTERFACE
    def set_progress(self, session_id: str, *, current_step: int, total_steps: int) -> None:
        """Set progress metrics for a session."""
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return
            s.progress.current_step = max(0, int(current_step))
            s.progress.total_steps = max(0, int(total_steps))
            s.updated_at = time.time()

    # PUBLIC_INTERFACE
    def initialize_cases(self, session_id: str, cases: List[str]) -> None:
        """Initialize per-case statuses to SCHEDULE for selected cases."""
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return
            s.case_status = {}
            for c in cases or []:
                if c:
                    s.case_status[c] = CASE_SCHEDULE
            s.updated_at = time.time()
            if cases:
                self.append_log(session_id, "INFO", f"Initialized {len(cases)} test cases as SCHEDULE.")

    # PUBLIC_INTERFACE
    def set_ui_lock(self, session_id: str, locked: bool) -> None:
        """Set UI lock flag for session."""
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return
            s.ui_lock = bool(locked)
            s.updated_at = time.time()

    # PUBLIC_INTERFACE
    def mark_started(self, session_id: str) -> None:
        """Mark a session as started."""
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return
            s.status = "RUNNING"
            s.started_at = time.time()
            s.updated_at = s.started_at
            self.append_log(session_id, "INFO", "Execution started.")

    # PUBLIC_INTERFACE
    def mark_finished(self, session_id: str, *, success: bool, totals: Dict[str, int], started_at: Optional[float]) -> None:
        """Mark a session finished with stats."""
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return
            s.status = "COMPLETED" if success else "FAILED"
            s.finished_at = time.time()
            s.updated_at = s.finished_at
            duration = 0.0
            if started_at:
                duration = max(0.0, s.finished_at - started_at)
            s.stats.duration_seconds = round(duration, 3)
            s.stats.success = bool(success)
            s.stats.passed = int(totals.get("passed", 0))
            s.stats.failed = int(totals.get("failed", 0))
            s.stats.skipped = int(totals.get("skipped", 0))
            # Unlock UI on completion
            s.ui_lock = False
            self.append_log(session_id, "INFO", f"Execution finished. Success={success} "
                                                f"(Passed={s.stats.passed}, Failed={s.stats.failed}, Skipped={s.stats.skipped}).")

    # Case tracking helpers

    # PUBLIC_INTERFACE
    def set_current_case(self, session_id: str, name: Optional[str], documentation: Optional[str] = None) -> None:
        """Set current running case and mark it TESTING. Prior TESTING moves back to SCHEDULE if different."""
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return
            # Move any previously testing case back to schedule if it's different and still unknown result
            if s.current_case_name and s.current_case_name != name:
                prev = s.current_case_name
                if prev in s.case_status and s.case_status[prev] == CASE_TESTING:
                    s.case_status[prev] = CASE_SCHEDULE
            s.current_case_name = name
            s.current_case_doc = documentation
            if name:
                # ensure exists in map
                if name not in s.case_status:
                    s.case_status[name] = CASE_SCHEDULE
                s.case_status[name] = CASE_TESTING
            s.updated_at = time.time()

    # PUBLIC_INTERFACE
    def set_case_result(self, session_id: str, name: str, outcome: str) -> None:
        """Set final status for a case to PASS/FAIL/SKIP."""
        if outcome not in {CASE_PASS, CASE_FAIL, CASE_SKIP}:
            return
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return
            if name not in s.case_status:
                s.case_status[name] = CASE_NOTRUN
            s.case_status[name] = outcome
            # if the current running is same, clear current
            if s.current_case_name == name:
                s.current_case_name = None
                s.current_case_doc = None
            s.updated_at = time.time()

    # Views for new endpoints

    # PUBLIC_INTERFACE
    def get_case_status_view(self, session_id: str) -> Optional[Dict]:
        """Return per-case statuses for a session."""
        s = self.get(session_id)
        if not s:
            return None
        cases = [{"name": k, "status": v} for k, v in s.case_status.items()]
        return {"session_id": s.session_id, "cases": cases}

    # PUBLIC_INTERFACE
    def get_current_case_info_view(self, session_id: str) -> Optional[Dict]:
        """Return current test case info for a session."""
        s = self.get(session_id)
        if not s:
            return None
        return {
            "session_id": s.session_id,
            "name": s.current_case_name,
            "documentation": s.current_case_doc,
        }

    # PUBLIC_INTERFACE
    def get_ui_lock_view(self, session_id: str) -> Optional[Dict]:
        """Return the UI lock state."""
        s = self.get(session_id)
        if not s:
            return None
        return {"session_id": s.session_id, "locked": bool(s.ui_lock)}

    # PUBLIC_INTERFACE
    def get_progress_view(self, session_id: str) -> Optional[Dict]:
        """Return a public view for progress endpoint."""
        s = self.get(session_id)
        if not s:
            return None
        return {
            "total_steps": s.progress.total_steps,
            "current_step": s.progress.current_step,
            "percent": s.progress.percent,
        }

    # PUBLIC_INTERFACE
    def get_stats_view(self, session_id: str) -> Optional[Dict]:
        """Return a public view for stats endpoint."""
        s = self.get(session_id)
        if not s:
            return None
        return {
            "duration_seconds": s.stats.duration_seconds,
            "steps_completed": s.progress.current_step,
            "success": s.stats.success,
            "artifacts": s.stats.artifacts,
            "passed": s.stats.passed,
            "failed": s.stats.failed,
            "skipped": s.stats.skipped,
            "started_at": s.started_at,
            "finished_at": s.finished_at,
            "status": s.status,
        }

    # PUBLIC_INTERFACE
    def get_logs_view(self, session_id: str, *, level: Optional[str] = None, limit: Optional[int] = None) -> Optional[List[Dict]]:
        """Return a public list of log entries with optional filter and limit."""
        s = self.get(session_id)
        if not s:
            return None
        logs = s.logs
        if level:
            lvl = level.upper()
            logs = [l for l in logs if l.level == lvl]
        if limit is not None and limit >= 0:
            logs = logs[-limit:]
        return [{"timestamp": l.timestamp, "level": l.level, "message": l.message} for l in logs]
