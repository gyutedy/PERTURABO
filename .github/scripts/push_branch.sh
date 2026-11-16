#!/usr/bin/env bash
# Pousse le commit courant sur la branche du run, sans jamais echouer sur un
# rejet non fast-forward.
#
# POURQUOI CE SCRIPT EXISTE
#   Un runner GitHub Actions clone le repo au DEBUT du run. Une transcription
#   dure des heures : pendant ce temps, un humain peut pousser, un autre
#   workflow aussi. Le checkout du runner est alors perime, et un `git push`
#   sec est rejete :
#
#     ! [rejected]  HEAD -> branche (fetch first)
#     error: failed to push some refs
#
#   C'est ce qui est arrive au run 43872241148 (v2927914500) : le commit local
#   426ee5e a ete perdu avec le runner, seul un retry chanceux a sauve les
#   fichiers (b80c1f4). Ce script ferme le trou : fetch, rebase, retry.
#
# USAGE
#   bash .github/scripts/push_branch.sh <branche> [<fichiers a ajouter>...]
#
#   - sans fichiers : pousse le commit DEJA fait par l'appelant
#   - avec fichiers : git add <fichiers>, commit avec $COMMIT_MESSAGE, puis pousse
#
# VARIABLES
#   COMMIT_MESSAGE  message de commit (requis si des fichiers sont passes)
#   GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL  identite (defauts : OracleF00B)
#
# Sortie : 0 si le commit est sur la branche distante (ou s'il n'y avait rien
# a pousser). 0 aussi si un autre acteur a deja pousse exactement notre
# contenu. 1 seulement si les 3 essais echouent : la perte doit etre bruyante.

set -uo pipefail

BRANCH="${1:-${GITHUB_REF_NAME:-}}"
shift || true
FILES=("$@")

ROOT="${GITHUB_WORKSPACE:-$(git rev-parse --show-toplevel)}"
cd "$ROOT" || { echo "::error::workspace introuvable"; exit 1; }

if [ -z "$BRANCH" ]; then
  BRANCH="$(git rev-parse --abbrev-ref HEAD)"
fi

git config user.name "${GIT_AUTHOR_NAME:-OracleF00B}"
git config user.email "${GIT_AUTHOR_EMAIL:-oracle@perturabo.iron}"

# --- 1. Commit optionnel ---------------------------------------------------
if [ "${#FILES[@]}" -gt 0 ]; then
  git add "${FILES[@]}" 2>/dev/null || true
  if git diff --cached --quiet; then
    echo "Rien a committer (contenu identique) : on tente quand meme le push."
  else
    if [ -z "${COMMIT_MESSAGE:-}" ]; then
      echo "::error::COMMIT_MESSAGE manquant alors que des fichiers sont passes"
      exit 1
    fi
    git commit -m "$COMMIT_MESSAGE" || echo "commit impossible : on continue vers le push"
  fi
fi

# --- 2. Se remettre a niveau AVANT de pousser ------------------------------
# HEAD peut etre loin derriere la branche distante : le runner a clone il y a
# des heures. On ne pousse jamais un checkout perime.
git fetch origin "$BRANCH" || true
git pull --rebase --autostash origin "$BRANCH" || true

# --- 3. Push avec retry ----------------------------------------------------
for i in 1 2 3; do
  if git push origin "HEAD:${BRANCH}"; then
    echo "Pousse sur ${BRANCH} (essai ${i})."
    exit 0
  fi
  echo "::warning::push rejete sur ${BRANCH} (essai ${i}/3), rebase et nouvel essai"
  git fetch origin "$BRANCH" || true
  git pull --rebase --autostash origin "$BRANCH" || true
  sleep 5
done

# --- 4. Dernier recours : le contenu est-il deja en haut ? -----------------
# Cas frequent : le `pull --rebase` a deja applique notre patch (meme contenu,
# autre sha), donc plus rien a pousser et push renvoie "Everything up-to-date"
# en succes. Si on arrive ici, c'est qu'on a vraiment echoue.
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git rev-parse "origin/${BRANCH}" 2>/dev/null || echo none)"
echo "::error::push echoue 3 fois — local=${LOCAL_SHA} distant=${REMOTE_SHA}"
git log --oneline -3
exit 1
