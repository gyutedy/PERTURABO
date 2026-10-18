#!/usr/bin/env bash
# Persiste les questions/réponses du relais oracle sur la branche du run.
# Non bloquant : un échec de persistance ne fait jamais échouer le pipeline.
set -uo pipefail

BRANCH="${1:-${GITHUB_REF_NAME:-}}"
ROOT="${GITHUB_WORKSPACE:-$(git rev-parse --show-toplevel)}"
cd "$ROOT" || exit 0

RELAY_DIR="MONDES_FORGES/CLIPPING/ORACLE"
if [ ! -d "$RELAY_DIR" ]; then
  echo "Relais oracle absent — rien à persister."
  exit 0
fi

git config user.name "OracleRelay"
git config user.email "oracle@perturabo.iron"

git add "$RELAY_DIR/pending" "$RELAY_DIR/answers.json" 2>/dev/null || true
if git diff --cached --quiet; then
  echo "Relais oracle : rien à persister."
  exit 0
fi

git commit -m "chore(oracle): persistance des questions/réponses du relais" || exit 0

if [ -z "$BRANCH" ]; then
  BRANCH="$(git rev-parse --abbrev-ref HEAD)"
fi

for _ in 1 2 3; do
  if git push origin "HEAD:${BRANCH}"; then
    echo "Relais oracle poussé sur ${BRANCH}."
    exit 0
  fi
  git pull --rebase --autostash origin "$BRANCH" || true
  sleep 3
done

echo "::warning::persistance du relais oracle échouée (non bloquant)"
exit 0
