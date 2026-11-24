#!/usr/bin/env bash
# Preflight check for the farmer platform dev environment.
# Usage: bash infra/scripts/preflight.sh
# Exits non-zero if anything required for the next phase is missing.

set -u

PASS=0
FAIL=0
PENDING=0

green() { printf '\033[32m%s\033[0m' "$1"; }
red()   { printf '\033[31m%s\033[0m' "$1"; }
amber() { printf '\033[33m%s\033[0m' "$1"; }

ok()   { PASS=$((PASS+1));    printf '  %s  %s\n' "$(green 'PASS')" "$1"; }
no()   { FAIL=$((FAIL+1));    printf '  %s  %s\n' "$(red 'FAIL')" "$1"; [ -n "${2:-}" ] && printf '         → %s\n' "$2"; }
wait_() { PENDING=$((PENDING+1)); printf '  %s  %s\n' "$(amber 'PEND')" "$1"; }

echo
echo "Farmer platform — environment preflight"
echo "========================================"

# ── Git ────────────────────────────────────────────────────────────
echo
echo "Version control"
if command -v git >/dev/null 2>&1; then
  ok "git $(git --version | awk '{print $3}')"
  if [ -n "$(git config --global --get user.name 2>/dev/null)" ] && \
     [ -n "$(git config --global --get user.email 2>/dev/null)" ]; then
    ok "git identity set ($(git config --global --get user.email))"
  else
    no "git identity not set" "git config --global user.name \"Your Name\"; git config --global user.email \"you@example.com\""
  fi
else
  no "git not found" "winget install -e --id Git.Git"
fi

# ── Node ───────────────────────────────────────────────────────────
echo
echo "Node (mobile + admin)"
if command -v node >/dev/null 2>&1; then
  NODE_V=$(node --version | tr -d 'v')
  NODE_MAJOR=${NODE_V%%.*}
  if [ "$NODE_MAJOR" -ge 20 ] 2>/dev/null; then
    ok "node v$NODE_V (>= 20)"
  else
    no "node v$NODE_V is too old" "winget install -e --id OpenJS.NodeJS.LTS"
  fi
else
  no "node not found" "winget install -e --id OpenJS.NodeJS.LTS"
fi

# ── Python 3.12 ────────────────────────────────────────────────────
echo
echo "Python (backend + ML)"
PY312=""
for cand in "py -3.12" "python3.12" "python3"; do
  if $cand --version >/dev/null 2>&1; then
    V=$($cand --version 2>&1 | awk '{print $2}')
    case "$V" in
      3.12.*) PY312="$cand"; break ;;
    esac
  fi
done
if [ -n "$PY312" ]; then
  ok "Python 3.12 available via '$PY312' ($($PY312 --version 2>&1 | awk '{print $2}'))"
else
  CUR=$( (py --version 2>/dev/null || python --version 2>/dev/null || echo 'none') | awk '{print $2}')
  no "Python 3.12 not found (current default: ${CUR:-none})" "winget install -e --id Python.Python.3.12  — then reopen Git Bash"
fi

# ── Docker ─────────────────────────────────────────────────────────
echo
echo "Docker"
if command -v docker >/dev/null 2>&1; then
  if DOCKER_V=$(docker info --format '{{.ServerVersion}}' 2>/dev/null) && [ -n "$DOCKER_V" ]; then
    ok "Docker engine running (server $DOCKER_V)"
    if docker compose version >/dev/null 2>&1; then
      ok "docker compose $(docker compose version --short 2>/dev/null)"
    else
      no "docker compose plugin missing" "Update Docker Desktop"
    fi
  else
    no "Docker installed but the engine is not running" "Start Docker Desktop and wait for 'Engine running', then retry"
  fi
else
  no "docker not found" "winget install -e --id Docker.DockerDesktop"
fi

# ── Disk & memory ──────────────────────────────────────────────────
echo
echo "Resources"
FREE_GB=$(df -Pk . 2>/dev/null | awk 'NR==2 {print int($4/1024/1024)}')
if [ -n "${FREE_GB:-}" ]; then
  if [ "$FREE_GB" -ge 10 ]; then
    ok "${FREE_GB} GB free disk (need >= 10 GB for images + Postgres)"
  else
    no "only ${FREE_GB} GB free" "Free space: Docker images + Postgres need ~10 GB"
  fi
fi

# ── Keys (optional for Phase 3) ────────────────────────────────────
echo
echo "API keys (not needed until Phase 7+)"
if [ -f .env ]; then
  for pair in "OPENWEATHER_API_KEY:Phase 7 weather" \
              "AGMARKNET_API_KEY:Phase 9 mandi prices" \
              "BHASHINI_API_KEY:Phase 10 voice" \
              "R2_ACCESS_KEY_ID:Phase 8 image storage"; do
    key=${pair%%:*}
    phase=${pair#*:}
    val=$(grep -E "^${key}=" .env 2>/dev/null | head -1 | cut -d= -f2-)
    if [ -n "$val" ] && [ "$val" != "changeme" ]; then
      ok "$key set ($phase)"
    else
      wait_ "$key missing ($phase)"
    fi
  done
else
  wait_ ".env not created yet (Phase 3 generates .env.example)"
fi

# ── Summary ────────────────────────────────────────────────────────
echo
echo "========================================"
printf 'passed: %s   failed: %s   pending: %s\n' "$PASS" "$FAIL" "$PENDING"
echo
if [ "$FAIL" -eq 0 ]; then
  echo "→ Ready for Phase 3 (Docker dev environment)."
  exit 0
else
  echo "→ Fix the FAIL lines above, then re-run this script."
  exit 1
fi
