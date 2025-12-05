# Routes

- health: GET /
- run: POST /run
- progress: GET /progress?session_id=...
- stats: GET /stats?session_id=...
- logs: GET /logs?session_id=...[&level=INFO&limit=50]

## Robot Framework integration: Example usage

1) Start a run (adjust paths to your project):
```bash
curl -sS -X POST http://localhost:3001/run \
  -H "Content-Type: application/json" \
  -d '{
    "suite": "demo_project",
    "tests_root": "tests", 
    "test_name": "suites",
    "test_cases": ["Example Test 1", "Example Test 2"],
    "config_folder": "config"
  }'
```

Response includes the session_id:
```json
{"session_id":"<uuid>","status":"RUNNING","created_at":..., "updated_at":...}
```

2) Poll progress:
```bash
curl -sS "http://localhost:3001/progress?session_id=<uuid>"
```

3) View stats (after completion you will see totals and artifacts):
```bash
curl -sS "http://localhost:3001/stats?session_id=<uuid>"
```

4) Tail logs (last 50 lines):
```bash
curl -sS "http://localhost:3001/logs?session_id=<uuid>&limit=50"
```

Outputs are written under:
```
./output/<suite>/<timestamp>/
```

If a `Robot_Setting.yaml` file exists under `config_folder`, its key/values are passed to Robot via `--variable key:value`.
