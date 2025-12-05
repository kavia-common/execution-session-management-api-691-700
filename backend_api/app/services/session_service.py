from __future__ import annotations

from typing import Dict, Optional, List

from app.state_manager import StateManager
from app.robot_runner import RobotRunner


class SessionService:
    """
    PUBLIC_INTERFACE
    High-level service bridging Flask routes with StateManager and RobotRunner.
    Creates sessions, starts Robot runs, and exposes read views for progress, stats, logs, and new state endpoints.
    """

    def __init__(self) -> None:
        self.state = StateManager()
        self.runner = RobotRunner(self.state)

    # PUBLIC_INTERFACE
    def create_session(self, payload: Dict):
        """
        Create a session and start Robot execution asynchronously.
        Payload supports:
          - suite (project name, used for output grouping)
          - tests_root (path to robot tests)
          - test_name (optional suite/file within tests_root)
          - test_cases (optional list of test case names)
          - config_folder (optional path containing Robot_Setting.yaml)
        """
        suite = payload.get("suite") or "default"
        tests_root = payload.get("tests_root") or "."
        test_name = payload.get("test_name")
        test_cases = payload.get("test_cases") or []
        config_folder = payload.get("config_folder")

        # Create a session
        s = self.state.create_session()
        # Initialize case statuses for selected cases as SCHEDULE
        if test_cases:
            self.state.initialize_cases(s.session_id, test_cases)
        # Lock UI early for safety
        self.state.set_ui_lock(s.session_id, True)
        # Persist initial payload in logs
        self.state.append_log(s.session_id, "INFO", f"Received payload: {payload}")

        # Start robot in background
        self.runner.start(
            s.session_id,
            project=suite,
            tests_root=tests_root,
            test_name=test_name,
            test_cases=test_cases,
            config_folder=config_folder,
        )
        # Return a lightweight view (mimic previous response fields)
        sess = self.state.get(s.session_id)
        return type("SessionView", (), {
            "session_id": s.session_id,
            "status": sess.status if sess else "PENDING",
            "created_at": sess.created_at if sess else 0.0,
            "updated_at": sess.updated_at if sess else 0.0,
        })

    # PUBLIC_INTERFACE
    def get_progress(self, session_id: str) -> Optional[Dict]:
        """Get progress view for a session."""
        return self.state.get_progress_view(session_id)

    # PUBLIC_INTERFACE
    def get_stats(self, session_id: str) -> Optional[Dict]:
        """Get stats view for a session."""
        return self.state.get_stats_view(session_id)

    # PUBLIC_INTERFACE
    def get_logs(self, session_id: str, level: Optional[str] = None, limit: Optional[int] = None) -> Optional[List[Dict]]:
        """Get logs view for a session."""
        return self.state.get_logs_view(session_id, level=level, limit=limit)

    # PUBLIC_INTERFACE
    def get_case_status(self, session_id: str) -> Optional[Dict]:
        """Get per-case status view."""
        return self.state.get_case_status_view(session_id)

    # PUBLIC_INTERFACE
    def get_current_case_info(self, session_id: str) -> Optional[Dict]:
        """Get current case info view."""
        return self.state.get_current_case_info_view(session_id)

    # PUBLIC_INTERFACE
    def get_ui_lock(self, session_id: str) -> Optional[Dict]:
        """Get UI lock view."""
        return self.state.get_ui_lock_view(session_id)


# Singleton instance
session_service = SessionService()
