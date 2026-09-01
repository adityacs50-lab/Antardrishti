#!/usr/bin/env bash
# Prove the offline claim, rather than asserting it on a slide.
#
#   ./scripts/verify_offline.sh            full run
#   ./scripts/verify_offline.sh --static   skip the live boot (static checks only)
#
# Four checks, each of which can fail the build:
#
#   A  no runtime module imports anything network-capable
#   B  no runtime file (or built frontend bundle) contains an external URL
#   C  every model artefact present matches its recorded checksum
#   D  the whole stack boots, seeds, classifies a report correctly and stops,
#      with outbound traffic pointed at a black hole so any accidental call
#      fails loudly instead of silently succeeding on a connected laptop
#
# Exit 0 = safe to demo with the network off.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

PY="${PYTHON:-python3}"
API_PORT="${PRAHARI_API_PORT:-8021}"
RUNTIME="backend/prahari"
STATIC_ONLY=0
[ "${1:-}" = "--static" ] && STATIC_ONLY=1

FAILURES=0
WARNINGS=0
BOLD=""; RED=""; GRN=""; YEL=""; DIM=""; OFF=""
if [ -t 1 ]; then BOLD=$'\e[1m'; RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; DIM=$'\e[2m'; OFF=$'\e[0m'; fi

hdr()  { printf '\n%s%s%s\n%s\n' "$BOLD" "$1" "$OFF" "$(printf '%.0s-' {1..70})"; }
pass() { printf '  %s[PASS]%s %s\n' "$GRN" "$OFF" "$1"; }
fail() { printf '  %s[FAIL]%s %s\n' "$RED" "$OFF" "$1"; FAILURES=$((FAILURES+1)); }
warn() { printf '  %s[WARN]%s %s\n' "$YEL" "$OFF" "$1"; WARNINGS=$((WARNINGS+1)); }
note() { printf '  %s%s%s\n' "$DIM" "$1" "$OFF"; }

printf '\n%s  prahari · offline verification%s\n' "$BOLD" "$OFF"
note "repo: $REPO"

# --------------------------------------------------------------------------
hdr "0. Preflight"
# --------------------------------------------------------------------------
# The demo laptop may not be the one this was built on. Missing prerequisites
# should say so in one line, not surface later as a boot timeout.
command -v "$PY" >/dev/null 2>&1 && pass "python: $("$PY" --version 2>&1)" \
                                 || { fail "python3 not found (set PYTHON=/path/to/python)"; }
command -v curl >/dev/null 2>&1 && pass "curl present" || fail "curl not found — required for the live check"

MISSING_PKGS=""
for mod in fastapi sqlalchemy pydantic uvicorn; do
  "$PY" -c "import $mod" >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS $mod"
done
if [ -n "$MISSING_PKGS" ]; then
  fail "missing Python packages:$MISSING_PKGS"
  note "         fix with:  make setup   (needs a network, once)"
else
  pass "backend dependencies importable (fastapi, sqlalchemy, pydantic, uvicorn)"
fi

if [ -s data/synthetic_reports.jsonl ]; then
  pass "corpus present ($(wc -l < data/synthetic_reports.jsonl | tr -d " ") reports)"
else
  fail "data/synthetic_reports.jsonl missing — run: make seed"
fi

# --------------------------------------------------------------------------
hdr "A. Banned imports in runtime code"
# --------------------------------------------------------------------------
# Build-time training scripts are excluded on purpose: they run on a machine
# that HAS a network, and a test asserts nothing at runtime imports them.
BANNED='^[[:space:]]*(import|from)[[:space:]]+(requests|urllib3|urllib\.request|httpx|aiohttp|http\.client|socket|ftplib|smtplib|telnetlib|openai|anthropic|cohere|boto3|botocore|google\.cloud|azure|psycopg2|pymongo|redis|elasticsearch|huggingface_hub|transformers|torch|peft|datasets)\b'

HITS=$(grep -rInE "$BANNED" "$RUNTIME" --include='*.py' 2>/dev/null | grep -v "/ml/training/" || true)
if [ -n "$HITS" ]; then
  fail "network-capable or training-only imports found in runtime code:"
  printf '%s\n' "$HITS" | sed 's/^/         /'
else
  pass "no runtime module imports a network client, transformers or torch"
fi

TRAINING_LEAK=$(grep -rInE '(import|from)[[:space:]]+.*ml\.training' "$RUNTIME" --include='*.py' 2>/dev/null | grep -v "/ml/training/" || true)
if [ -n "$TRAINING_LEAK" ]; then
  fail "runtime code imports a build-time training module:"
  printf '%s\n' "$TRAINING_LEAK" | sed 's/^/         /'
else
  pass "no runtime module reaches into ml/training/"
fi

# --------------------------------------------------------------------------
hdr "B. External URL literals"
# --------------------------------------------------------------------------
# citations.py is exempt: those URLs are provenance for published safety
# literature. They are never fetched, and a test enforces that exemption is
# the only one.
ALLOW='localhost|127\.0\.0\.1|0\.0\.0\.0|schemas?\.|w3\.org|json-schema|sqlalche\.me|example\.com'

PY_URLS=$(grep -rInE 'https?://' "$RUNTIME" --include='*.py' 2>/dev/null \
          | grep -v "/ml/training/" \
          | grep -v "citations.py" \
          | grep -vE "$ALLOW" || true)
if [ -n "$PY_URLS" ]; then
  fail "external URLs in runtime Python:"
  printf '%s\n' "$PY_URLS" | sed 's/^/         /'
else
  pass "no external URLs in runtime Python (citations.py exempt, never fetched)"
fi

WEB_URLS=$(grep -rInE 'https?://' web/src web/index.html 2>/dev/null | grep -vE "$ALLOW" || true)
if [ -n "$WEB_URLS" ]; then
  fail "external URLs in frontend source:"
  printf '%s\n' "$WEB_URLS" | sed 's/^/         /'
else
  pass "no external URLs in frontend source"
fi

FONT_HITS=$(grep -rInE 'fonts\.(googleapis|gstatic)|@import[[:space:]]+url|cdn\.' web/src web/index.html 2>/dev/null || true)
if [ -n "$FONT_HITS" ]; then
  fail "web font or CDN reference in the frontend:"
  printf '%s\n' "$FONT_HITS" | sed 's/^/         /'
else
  pass "no web fonts, no CDN (system font stack only)"
fi

if [ -d web/dist ]; then
  BUNDLE=$(grep -ohE 'https?://[a-zA-Z0-9./?=_-]+' web/dist/assets/* web/dist/index.html 2>/dev/null \
           | grep -vE "$ALLOW|react\.dev|reactjs\.org|fb\.me|rollupjs|vitejs" | sort -u || true)
  if [ -n "$BUNDLE" ]; then
    fail "built bundle references external hosts:"
    printf '%s\n' "$BUNDLE" | sed 's/^/         /'
  else
    pass "built bundle (web/dist) references no external hosts"
  fi
else
  note "web/dist not built yet — run 'make build' to include the bundle in this check"
fi

# --------------------------------------------------------------------------
hdr "C. Model artefacts and checksums"
# --------------------------------------------------------------------------
MANIFEST="models/MANIFEST.sha256"
if [ -f "$MANIFEST" ]; then
  MISSING=0
  while read -r sum file; do
    [ -z "${file:-}" ] && continue
    if [ ! -f "models/$file" ]; then
      fail "declared artefact missing: models/$file"
      MISSING=1
      continue
    fi
    actual=$(sha256sum "models/$file" | awk '{print $1}')
    if [ "$actual" != "$sum" ]; then
      fail "checksum mismatch: models/$file"
      note "         expected $sum"
      note "         actual   $actual"
      MISSING=1
    else
      pass "models/$file  $(du -h "models/$file" | cut -f1)  sha256 ok"
    fi
  done < "$MANIFEST"
  [ "$MISSING" = "0" ] && pass "all declared model artefacts verified"
else
  # A missing model is a SUPPORTED state, not a failure: the extractor falls
  # back to the deterministic keyword path and every verdict remains fully
  # traceable. What would be a failure is claiming a model is loaded when it
  # is not — which is why the banner prints the live path.
  if [ -f models/prahari.onnx ]; then
    warn "models/prahari.onnx exists but $MANIFEST does not — checksums unverified"
    note "         create it with: make model-manifest"
  else
    pass "no model artefacts; the keyword fallback is the expected demo path"
    note "         (train + export, then 'make model-manifest', to switch to ONNX)"
  fi
fi

# --------------------------------------------------------------------------
if [ "$STATIC_ONLY" = "1" ]; then
  hdr "D. Live boot  —  SKIPPED (--static)"
else
hdr "D. Live boot, seed, classify, teardown"
# --------------------------------------------------------------------------
# Any accidental outbound call is routed to a black hole, so a connected
# laptop cannot mask a dependency that would fail on the demo floor.
export HTTP_PROXY="http://127.0.0.1:9"
export HTTPS_PROXY="http://127.0.0.1:9"
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export NO_PROXY="localhost,127.0.0.1"
export no_proxy="$NO_PROXY"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
note "outbound traffic pointed at 127.0.0.1:9 (discard) for this section"

VERIFY_DB="${TMPDIR:-/tmp}/prahari-verify/verify.db"
rm -f "$VERIFY_DB" "$VERIFY_DB-wal" "$VERIFY_DB-shm" "$VERIFY_DB-journal" 2>/dev/null || true
mkdir -p "$(dirname "$VERIFY_DB")"
export PRAHARI_DB_PATH="$VERIFY_DB"
note "using a throwaway database: $VERIFY_DB"

LOG=$(mktemp); SRV_PID=""
cleanup() {
  if [ -n "$SRV_PID" ] && kill -0 "$SRV_PID" 2>/dev/null; then
    kill "$SRV_PID" 2>/dev/null || true
    wait "$SRV_PID" 2>/dev/null || true
  fi
  rm -f "$LOG"
}
trap cleanup EXIT

( cd backend && PYTHONPATH=. "$PY" -m prahari.cli seed --limit 120 ) >"$LOG" 2>&1
if grep -q "Seeded" "$LOG"; then
  pass "seeded $(grep -oE 'Seeded [0-9]+' "$LOG" | head -1 | awk '{print $2}') reports with no network"
else
  if grep -q "already holds" "$LOG"; then
    pass "database already seeded (reusing existing state)"
  else
    fail "seeding failed"; tail -6 "$LOG" | sed 's/^/         /'
  fi
fi

( cd backend && PYTHONPATH=. "$PY" -m uvicorn prahari.main:app --host 127.0.0.1 --port "$API_PORT" --log-level warning ) >>"$LOG" 2>&1 &
SRV_PID=$!

READY=0
for _ in $(seq 1 60); do
  if curl -fsS --noproxy '*' "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1; then READY=1; break; fi
  sleep 0.5
done

if [ "$READY" != "1" ]; then
  fail "API did not come up on port $API_PORT"
  tail -15 "$LOG" | sed 's/^/         /'
else
  HEALTH=$(curl -fsS --noproxy '*' "http://127.0.0.1:$API_PORT/health")
  pass "API booted with the network blocked"
  note "         $(printf '%s' "$HEALTH" | "$PY" -c 'import json,sys; d=json.load(sys.stdin); print("extractor=%s engine=%s reports=%s" % (d["extractor"], d["engine_version"], d["report_count"]))')"

  # The assertion that matters: a high-energy report with no direct control
  # and NO INJURY must come back as uncontrolled fatal potential. If this
  # regresses, the demo's whole argument collapses.
  VERDICT=$(curl -fsS --noproxy '*' -X POST "http://127.0.0.1:$API_PORT/api/analyze" \
    -H 'Content-Type: application/json' \
    -d '{"text":"On 12.08.2026 at abt 1430 hrs, Sri B. Gogoi (roustabout) was working at the monkey board at approx 8 mtr height at Rig No. 12, Naoholia. He was not wearing safety belt and no fall arrest arrangement was provided at the location. He lost balance and slipped from the board. There was no injury to any personnel."}' \
    | "$PY" -c 'import json,sys; d=json.load(sys.stdin); v=d["verdict"]; print(v["classification"], v["energy_source"], v["primary_lsr"], len(d["evidence_spans"]), len(v["fired_rules"]))' 2>/dev/null)

  set -- $VERDICT
  CLS="${1:-none}"; ENERGY="${2:-none}"; LSR="${3:-none}"; SPANS="${4:-0}"; RULES="${5:-0}"
  if [ "$CLS" = "psif" ]; then
    pass "POST /api/analyze -> psif (uncontrolled fatal potential, no injury)"
    note "         energy=$ENERGY  lsr=$LSR  spans=$SPANS  rules=$RULES"
  else
    fail "expected classification 'psif', got '$CLS'"
  fi
  [ "$ENERGY" = "gravity" ] && pass "energy source resolved to gravity" || fail "expected energy 'gravity', got '$ENERGY'"
  [ "$LSR" = "working_at_height" ] && pass "Life-Saving Rule tagged Working at Height" || fail "expected lsr 'working_at_height', got '$LSR'"
  [ "$SPANS" -ge 8 ] 2>/dev/null && pass "$SPANS evidence spans returned for highlighting" || fail "too few evidence spans ($SPANS)"
  [ "$RULES" -ge 6 ] 2>/dev/null && pass "$RULES named rules fired (verdict is traceable)" || fail "too few rules fired ($RULES)"

  # The low-energy trap: a real injury that is NOT a SIF.
  TRAP=$(curl -fsS --noproxy '*' -X POST "http://127.0.0.1:$API_PORT/api/analyze" \
    -H 'Content-Type: application/json' \
    -d '{"text":"On 03.07.2026, Sri R. Das (fitter) was cutting GI sheet at the workshop, Duliajan. Hand gloves were not worn while doing the job. The blade slipped and he sustained a cut on the left index finger. First aid was given at the installation and he resumed duty."}' \
    | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["verdict"]["classification"])' 2>/dev/null)
  [ "$TRAP" = "low_severity" ] && pass "visible injury with no fatal potential -> low_severity (not a SIF)" \
                               || fail "expected 'low_severity' for the injury trap, got '$TRAP'"

  for ep in /api/triage /api/analytics/density /api/analytics/lsr /api/analytics/accumulation; do
    code=$(curl -fsS --noproxy '*' -o /dev/null -w '%{http_code}' "http://127.0.0.1:$API_PORT$ep" 2>/dev/null || echo 000)
    [ "$code" = "200" ] && pass "GET $ep -> 200" || fail "GET $ep -> $code"
  done
fi

cleanup; trap - EXIT
pass "stack torn down"
fi

# --------------------------------------------------------------------------
printf '\n%s\n' "$(printf '%.0s=' {1..70})"
if [ "$FAILURES" -eq 0 ]; then
  printf '%s  OFFLINE VERIFICATION PASSED%s' "$GRN$BOLD" "$OFF"
  [ "$WARNINGS" -gt 0 ] && printf '   (%s warning(s))' "$WARNINGS"
  printf '\n  Safe to demo with the network off.\n'
  printf '%s\n\n' "$(printf '%.0s=' {1..70})"
  exit 0
else
  printf '%s  OFFLINE VERIFICATION FAILED — %s check(s)%s\n' "$RED$BOLD" "$FAILURES" "$OFF"
  printf '  Do NOT demo until these are fixed.\n'
  printf '%s\n\n' "$(printf '%.0s=' {1..70})"
  exit 1
fi
