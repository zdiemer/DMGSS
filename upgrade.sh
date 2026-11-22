#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
RELEASE="${RELEASE:-dmgss}"
NAMESPACE="${NAMESPACE:-games}"
# No app secrets. The intentionally empty template is not injected or materialized.
# Fail rather than silently ignore references added by a future change.
if grep -q '^[^#[:space:]]' "$HERE/values.local.tpl.yaml"; then
  echo 'Secret references now exist: implement op inject via the shared conventions first.' >&2
  exit 1
fi
helm upgrade --install "$RELEASE" "$HERE" -n "$NAMESPACE" --create-namespace -f "$HERE/values.yaml" --atomic --cleanup-on-fail --timeout 180s
kubectl -n "$NAMESPACE" rollout status "deployment/$RELEASE" --timeout=180s
