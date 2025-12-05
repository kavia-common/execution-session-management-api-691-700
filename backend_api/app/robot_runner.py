from __future__ import annotations

import os
import sys
import time
import threading
import subprocess
import yaml
from typing import Dict, List, Optional, Iterable

from app.state_manager import StateManager, CASE_PASS, CASE_FAIL, CASE_SKIP


def _load_robot_settings(config_folder: Optional[str]) -> Dict:
    """
    Attempt to load Robot variables from Robot_Setting.yaml under the provided config folder.
    Returns empty dict if missing or unreadable. Values are used as --variable key:value.
    """
    if not config_folder:
        return {}
    candidates = [
        os.path.join(config_folder, "Robot_Setting.yaml"),
        os.path.join(config_folder, "Robot_Setting.yml"),
        os.path.join(config_folder, "robot_setting.yaml"),
        os.path.join(config_folder, "robot_setting.yml"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if not isinstance(data, dict):
                    return {}
                return data
            except Exception:
                return {}
    return {}


def _ensure_output_dir(project: str) -> str:
    """
    Create output directory structure: ./output/<project>/<timestamp>/
    Returns the absolute path to the created output directory.
    """
    ts = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    base = os.path.abspath(os.path.join(os.getcwd(), "output"))
    project_dir = os.path.join(base, project or "default")
    out_dir = os.path.join(project_dir, ts)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def _build_robot_command(
    tests_root: str,
    test_name: Optional[str],
    test_cases: Optional[List[str]],
    output_dir: str,
    robot_vars: Dict,
) -> List[str]:
    """
    Build the Robot Framework CLI command.
    """
    cmd: List[str] = [sys.executable, "-m", "robot"]
    cmd += [
        "--outputdir", output_dir,
        "--report", "report.html",
        "--log", "log.html",
        "--xunit", "xunit.xml",
        "--output", "output.xml",
    ]
    for k, v in (robot_vars or {}).items():
        cmd += ["--variable", f"{k}:{v}"]
    if test_cases:
        for tc in test_cases:
            if tc:
                cmd += ["--test", tc]
    target = tests_root
    if test_name:
        candidate = os.path.join(tests_root, test_name)
        target = candidate
    cmd.append(target)
    return cmd


def _iter_stream(stream: Iterable[bytes]) -> Iterable[str]:
    """
    Iterate a stream line by line decoding to utf-8 with fallback.
    """
    for raw in stream:
        try:
            yield raw.decode("utf-8", errors="replace").rstrip("\n")
        except Exception:
            try:
                yield raw.decode("latin-1", errors="replace").rstrip("\n")
            except Exception:
                yield str(raw)


class RobotRunner:
    """
    PUBLIC_INTERFACE
    RobotRunner is responsible for executing Robot Framework tests via subprocess.Popen.
    It streams stdout lines, detects simple PASS/FAIL/SKIP outcomes, and updates a shared
    StateManager for session tracking, progress and statistics.
    """

    def __init__(self, state: StateManager) -> None:
        self.state = state

    # PUBLIC_INTERFACE
    def start(
        self,
        session_id: str,
        *,
        project: str,
        tests_root: str,
        test_name: Optional[str] = None,
        test_cases: Optional[List[str]] = None,
        config_folder: Optional[str] = None,
        extra_args: Optional[Dict] = None,
    ) -> None:
        """
        Start a Robot run asynchronously in a background thread.
        """
        # Lock UI while running
        self.state.set_ui_lock(session_id, True)
        self.state.mark_started(session_id)
        out_dir = _ensure_output_dir(project)
        self.state.set_artifacts(session_id, {
            "report_html": os.path.join(out_dir, "report.html"),
            "log_html": os.path.join(out_dir, "log.html"),
            "xunit_xml": os.path.join(out_dir, "xunit.xml"),
            "output_xml": os.path.join(out_dir, "output.xml"),
        })
        robot_vars = _load_robot_settings(config_folder)

        cmd = _build_robot_command(
            tests_root=tests_root,
            test_name=test_name,
            test_cases=test_cases,
            output_dir=out_dir,
            robot_vars=robot_vars,
        )

        # Log command for transparency
        self.state.append_log(session_id, "INFO", "Starting Robot: " + " ".join(cmd))
        self.state.append_log(session_id, "INFO", "Output dir: " + out_dir)

        t = threading.Thread(
            target=self._run_worker,
            args=(session_id, cmd, out_dir),
            daemon=True,
        )
        t.start()

    # PUBLIC_INTERFACE
    def request_stop(self, session_id: str) -> None:
        """
        Request a stop for a running session. Not implemented; scaffolding only.
        """
        self.state.append_log(session_id, "WARN", "Stop requested (not yet implemented).")

    def _run_worker(self, session_id: str, cmd: List[str], cwd: Optional[str]) -> None:
        started_at = time.time()
        totals = {"passed": 0, "failed": 0, "skipped": 0}
        total_steps = 0
        current_step = 0

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd if os.path.isdir(cwd or "") else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
            )
        except FileNotFoundError:
            self.state.append_log(session_id, "ERROR", "Robot not found. Ensure Robot Framework is installed.")
            self.state.mark_finished(session_id, success=False, totals=totals, started_at=started_at)
            return
        except Exception as e:
            self.state.append_log(session_id, "ERROR", f"Failed to start Robot: {e}")
            self.state.mark_finished(session_id, success=False, totals=totals, started_at=started_at)
            return

        assert proc.stdout is not None
        self.state.set_status(session_id, "RUNNING")
        self.state.append_log(session_id, "INFO", "Robot process started.")

        current_case_name: Optional[str] = None

        for line in _iter_stream(proc.stdout):
            line_str = line.strip()
            if not line_str:
                continue

            # Stream to logs
            self.state.append_log(session_id, "INFO", line_str)

            lowered = line_str.lower()

            # Detect a new test starting (heuristic)
            # Match patterns like "Starting test: <name>" or "Start test ... <name>"
            if "starting test" in lowered or line_str.startswith("START /") or line_str.startswith("Start test"):
                # naive extraction of name after colon if present
                name = None
                if ":" in line_str:
                    parts = line_str.split(":", 1)
                    name = parts[1].strip() or None
                else:
                    # fallback: last token after space
                    toks = line_str.split()
                    if toks:
                        name = toks[-1]

                current_case_name = name
                total_steps += 1
                # set current case as testing
                self.state.set_current_case(session_id, current_case_name, documentation=None)
                # progress update
                self.state.set_progress(
                    session_id,
                    current_step=current_step,
                    total_steps=max(total_steps, 1),
                )
                continue

            # Detect results and map to current case if available
            result_detected = None
            if " | pass" in lowered or lowered.endswith("pass") or lowered.startswith("pass") or " pass " in lowered:
                result_detected = CASE_PASS
                totals["passed"] += 1
            elif " | fail" in lowered or lowered.endswith("fail") or lowered.startswith("fail") or " fail " in lowered:
                result_detected = CASE_FAIL
                totals["failed"] += 1
            elif " | skip" in lowered or lowered.endswith("skip") or lowered.startswith("skip") or " skip " in lowered:
                result_detected = CASE_SKIP
                totals["skipped"] += 1

            if result_detected and current_case_name:
                self.state.set_case_result(session_id, current_case_name, result_detected)
                current_step = min(current_step + 1, max(total_steps, current_step + 1))
                # Update progress after result
                self.state.set_progress(
                    session_id,
                    current_step=current_step,
                    total_steps=max(total_steps, current_step if total_steps == 0 else total_steps),
                )
                # reset current until next start
                current_case_name = None
                continue

            # Otherwise, periodically ensure progress doesn't regress
            self.state.set_progress(
                session_id,
                current_step=current_step,
                total_steps=max(total_steps, current_step if total_steps == 0 else total_steps),
            )

        proc.wait()
        success = proc.returncode == 0
        self.state.append_log(session_id, "INFO", "Robot process finished with code " + str(proc.returncode) + ".")
        self.state.mark_finished(session_id, success=success, totals=totals, started_at=started_at)
