(() => {
  "use strict";

  // Configuration variables near the top for easy editing
  const DEFAULT_SUITE = "demo"; // groups outputs
  const DEFAULT_TESTS_ROOT = "tests";
  const DEFAULT_TEST_NAME = "suites"; // e.g., "suites" or "Test.robot"
  const DEFAULT_CONFIG_FOLDER = "config";
  const POLL_INTERVAL_MS = 1000; // 1s cadence

  // Internal state
  let sessionId = null;
  let pollTimer = null;
  let startedAt = null; // epoch seconds
  let lastRenderedLogCount = 0;
  let isPolling = false;

  // DOM elements
  const progressBar = document.getElementById("progress-bar");
  const progressPercent = document.getElementById("progress-percent");
  const elapsedTimeEl = document.getElementById("elapsed-time");
  const statusBadge = document.getElementById("status-badge");

  const statPass = document.getElementById("stat-pass");
  const statFail = document.getElementById("stat-fail");
  const statSkip = document.getElementById("stat-skip");
  const statNotRun = document.getElementById("stat-notrun");

  const btnStart = document.getElementById("btn-start");
  const btnStop = document.getElementById("btn-stop");
  const testList = document.getElementById("test-list");

  const logOutput = document.getElementById("log-output");
  const logLimitSel = document.getElementById("log-limit");

  // Helper: extract selected test names from the checklist
  function getSelectedTests() {
    const inputs = testList.querySelectorAll('input[type="checkbox"]');
    const selected = [];
    inputs.forEach((inp) => {
      if (inp.checked) selected.push(inp.value);
    });
    return selected;
  }

  // Helper: format elapsed time display from startedAt to now
  function formatElapsed(sec) {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const mm = String(m).padStart(2, "0");
    const ss = String(s).padStart(2, "0");
    return `${mm}:${ss}`;
  }

  // Helper: update header progress UI
  function updateProgressUI(percent) {
    const clamped = Math.max(0, Math.min(100, percent || 0));
    progressBar.style.width = `${clamped}%`;
    progressPercent.textContent = `${clamped.toFixed(0)}%`;
  }

  // Helper: update status badge style/text
  function setStatusBadge(text, type) {
    statusBadge.textContent = text || "IDLE";
    statusBadge.className = `badge ${type || "badge-neutral"}`;
  }

  // Helper: append logs (keeps only last N lines for performance)
  function renderLogs(entries, maxLines) {
    // entries are [{timestamp, level, message}]
    // keep only tail based on maxLines
    const tail = entries.slice(-maxLines);
    const lines = tail.map(
      (e) =>
        `${new Date(e.timestamp * 1000).toLocaleTimeString()} [${e.level}] ${e.message}`
    );
    logOutput.textContent = lines.join("\n");
    // Auto scroll to bottom
    logOutput.scrollTop = logOutput.scrollHeight;
  }

  // Start polling the backend using sessionId
  function startPolling() {
    if (!sessionId || isPolling) return;
    isPolling = true;

    // Poll cadence explanation:
    // - Every second we request progress, stats, and logs
    // - Progress updates the progress bar percent
    // - Stats updates pass/fail/skip and started/finished times for elapsed
    // - Logs tail is displayed (up to the configured limit)
    pollTimer = setInterval(async () => {
      try {
        // Progress
        if (sessionId) {
          const progRes = await fetch(`/progress?session_id=${encodeURIComponent(sessionId)}`);
          if (progRes.ok) {
            const prog = await progRes.json();
            updateProgressUI(prog.percent || 0);
          }
        }

        // Stats
        if (sessionId) {
          const statsRes = await fetch(`/stats?session_id=${encodeURIComponent(sessionId)}`);
          if (statsRes.ok) {
            const stats = await statsRes.json();
            // Update PASS/FAIL/SKIP; NOTRUN is derived from steps vs passed+failed+skipped
            const passed = stats.passed || 0;
            const failed = stats.failed || 0;
            const skipped = stats.skipped || 0;
            const stepsCompleted = stats.steps_completed || 0;
            const notrun = Math.max(0, stepsCompleted - (passed + failed + skipped));

            statPass.textContent = passed;
            statFail.textContent = failed;
            statSkip.textContent = skipped;
            statNotRun.textContent = notrun;

            // status badge
            setStatusBadge(stats.status || "RUNNING", stats.success === true ? "badge-success" : (stats.status === "FAILED" ? "badge-danger" : "badge-info"));

            // elapsed time uses started_at if available, else falls back to now
            if (stats.started_at) startedAt = stats.started_at;
            const base = startedAt ? startedAt : Date.now() / 1000;
            const now = Date.now() / 1000;
            elapsedTimeEl.textContent = `Elapsed: ${formatElapsed(Math.max(0, now - base))}`;
          }
        }

        // Logs (limit controlled by select)
        if (sessionId) {
          const limit = Number(logLimitSel.value) || 200;
          const logsRes = await fetch(`/logs?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`);
          if (logsRes.ok) {
            const logs = await logsRes.json();
            renderLogs(logs, Math.min(500, limit)); // cap to ~500 lines
            lastRenderedLogCount = logs.length;
          }
        }
      } catch (e) {
        console.error("Polling error:", e);
      }
    }, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    isPolling = false;
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  // Start button handler: POST /run with selected tests
  btnStart.addEventListener("click", async () => {
    try {
      const selected = getSelectedTests();
      // Prepare payload; test_name and folders are configurable at the top
      const payload = {
        suite: DEFAULT_SUITE,
        tests_root: DEFAULT_TESTS_ROOT,
        test_name: DEFAULT_TEST_NAME,
        test_cases: selected,
        config_folder: DEFAULT_CONFIG_FOLDER
      };

      btnStart.disabled = true;
      btnStop.disabled = false;
      setStatusBadge("STARTING", "badge-info");
      updateProgressUI(0);
      statPass.textContent = "0";
      statFail.textContent = "0";
      statSkip.textContent = "0";
      statNotRun.textContent = "0";
      logOutput.textContent = "";

      const res = await fetch("/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const msg = await res.text();
        throw new Error(`Failed to start run: ${msg}`);
      }

      const data = await res.json();
      sessionId = data.session_id;
      startedAt = data.created_at || null;
      setStatusBadge("RUNNING", "badge-info");
      startPolling();
    } catch (e) {
      console.error(e);
      alert(`Error: ${e.message}`);
      setStatusBadge("ERROR", "badge-danger");
      btnStart.disabled = false;
      btnStop.disabled = true;
    }
  });

  // Stop button handler: disables polling and shows placeholder message
  btnStop.addEventListener("click", () => {
    // Placeholder for future /stop integration
    stopPolling();
    setStatusBadge("STOPPED (local)", "badge-warning");
    const note = "\n[Local Stop] Polling paused. Future versions will call /stop to cancel server-side runs.";
    logOutput.textContent += note;
    btnStart.disabled = false;
    btnStop.disabled = true;
  });

  // Initial UI state
  btnStart.disabled = false;
  btnStop.disabled = true;
  setStatusBadge("IDLE", "badge-neutral");
  updateProgressUI(0);
  elapsedTimeEl.textContent = "Elapsed: 00:00";
})();
