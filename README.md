# execution-session-management-api-691-700

Robot Framework integration has been added to the backend.

Quickstart (assuming app runs on localhost:3001):
- Start a run:
  curl -sS -X POST http://localhost:3001/run -H "Content-Type: application/json" -d '{"suite":"demo","tests_root":"tests","test_name":"suites","test_cases":["Example Test 1"],"config_folder":"config"}'
- Poll progress:
  curl -sS "http://localhost:3001/progress?session_id=<uuid>"
- View stats:
  curl -sS "http://localhost:3001/stats?session_id=<uuid>"
- Tail logs:
  curl -sS "http://localhost:3001/logs?session_id=<uuid>&limit=50"

Outputs are generated under ./output/<suite>/<timestamp>/.
If present, Robot_Setting.yaml under config_folder is loaded as --variable key:value.