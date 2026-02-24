#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker CLI not found"
  exit 2
fi

DOCKERD_LOG="${DOCKERD_LOG:-/tmp/robot_policy_dockerd.log}"
started_dockerd=0

cleanup() {
  docker rm -f robot-api-mock-test >/dev/null 2>&1 || true
  if [[ "$started_dockerd" -eq 1 ]]; then
    kill "$DOCKERD_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if ! docker info >/dev/null 2>&1; then
  echo "Starting dockerd in constrained mode..."
  nohup dockerd --iptables=false --storage-driver=vfs --bridge=none >"$DOCKERD_LOG" 2>&1 &
  DOCKERD_PID=$!
  started_dockerd=1

  for _ in {1..30}; do
    docker info >/dev/null 2>&1 && break
    sleep 1
  done
fi

if ! docker info >/dev/null 2>&1; then
  echo "docker daemon unavailable in this environment"
  echo "See log: $DOCKERD_LOG"
  exit 2
fi

echo "Building images..."
docker build -t robot-policy-mcp:test -f Dockerfile .
docker build -t robot-api-mock:test -f Dockerfile.mock-robot-api .

echo "Running mock API container..."
docker run --rm -d --name robot-api-mock-test -p 18080:8080 robot-api-mock:test >/dev/null
sleep 2

echo "Running latency check against containerized mock API..."
python3 scripts/run_e2e_latency_check.py --base-url http://127.0.0.1:18080 --runs 8

echo "Docker self-test complete."
