#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(awk '/^  repository:/{print $2; exit}' "$HERE/values.yaml")"
TAG="$(awk -F'"' '/^  tag:/{print $2; exit}' "$HERE/values.yaml")"
IMAGE="${REPO}:${TAG}"
if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
  docker build -t "$IMAGE" "$HERE"
  docker push "$IMAGE"
elif command -v buildctl >/dev/null; then
  buildctl build --frontend dockerfile.v0 --local context="$HERE" --local dockerfile="$HERE" --output "type=image,\"name=$IMAGE\",push=true"
else
  echo 'A running Docker daemon or configured buildctl is required.' >&2
  exit 1
fi
