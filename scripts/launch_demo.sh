#!/usr/bin/env bash
# Start the API and a static file server for the built frontend, print the
# banner, open a browser, and shut both down cleanly on Ctrl-C.
#
# Deliberately serves web/dist rather than the Vite dev server: nothing should
# be able to recompile, hot-reload or throw an overlay mid-presentation.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

PY="${PYTHON:-python3}"
API_PORT="${PRAHARI_API_PORT:-8000}"
WEB_PORT="${PRAHARI_WEB_PORT:-5173}"
API_PID=""; WEB_PID=""

shutdown() {
  printf '\n  Shutting down...\n'
  [ -n "$WEB_PID" ] && kill "$WEB_PID" 2>/dev/null || true
  [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  printf '  Stopped.\n\n'
}
trap shutdown EXIT INT TERM

if [ ! -d web/dist ]; then
  echo "  web/dist missing — run 'make build' first."; exit 1
fi

( cd backend && PYTHONPATH=. "$PY" -m uvicorn prahari.main:app \
    --host 127.0.0.1 --port "$API_PORT" --log-level warning ) &
API_PID=$!

for _ in $(seq 1 60); do
  curl -fsS --noproxy '*' "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1 && break
  sleep 0.5
done

if ! curl -fsS --noproxy '*' "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1; then
  echo "  API failed to start. Try: make reset"; exit 1
fi

# A plain static server. The SPA needs unknown paths rewritten to index.html,
# which python's http.server will not do, so this handler adds exactly that.
( cd web/dist && "$PY" - "$WEB_PORT" <<'PYEOF' ) &
import http.server, os, socketserver, sys

PORT = int(sys.argv[1])

class SPA(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        target = path.lstrip("/")
        if path.startswith("/api") or path == "/health":
            self.send_error(502, "Call the API on its own port")
            return
        if target and os.path.exists(target) and not os.path.isdir(target):
            return super().do_GET()
        self.path = "/index.html"
        return super().do_GET()

    def log_message(self, *args):  # quiet
        pass

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", PORT), SPA) as httpd:
    httpd.serve_forever()
PYEOF
WEB_PID=$!
sleep 1

URL="http://localhost:$WEB_PORT"
for opener in xdg-open open "cmd.exe /c start" wslview; do
  if command -v "${opener%% *}" >/dev/null 2>&1; then
    $opener "$URL" >/dev/null 2>&1 && break
  fi
done

printf '\n  %s\n' "$(printf '%.0s=' {1..64})"
printf '  UI   %s\n  API  http://localhost:%s/docs\n' "$URL" "$API_PORT"
printf '  %s\n' "$(printf '%.0s=' {1..64})"
printf '  Runbook: DEMO.md      Reset: make reset      Ctrl-C to stop\n\n'

wait
