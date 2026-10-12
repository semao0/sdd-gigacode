#!/usr/bin/env bash
# pre-push: запускает ci-check.sh, если в отправляемых коммитах менялся openspec/.
# Остальные push не замедляет. Вызывается из существующего .git/hooks/pre-push.
# git передаёт хуку список ref на stdin один раз - если хуков несколько, сохраните его:
#   input=$(cat)
#   echo "$input" | ./scripts/ktlint-pre-push.sh || exit 1
#   echo "$input" | "$SDD_HOME/scripts/pre-push.sh" || exit 1
# Пропустить разово: SDD_SKIP=1 git push
set -uo pipefail
[ "${SDD_SKIP:-0}" = 1 ] && exit 0
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

changed=0
while read -r _lref lsha _rref rsha; do
  [[ "$lsha" =~ ^0+$ ]] && continue                  # удаление ветки
  if [[ "$rsha" =~ ^0+$ ]]; then                      # новая ветка: сравниваем с main
    rsha="$(git merge-base "$lsha" origin/HEAD 2>/dev/null)" || { changed=1; break; }
  fi
  # 1 - есть изменения, 128 - нет коммита локально: в обоих случаях проверяем
  git diff --quiet "$rsha" "$lsha" -- openspec/ 2>/dev/null || { changed=1; break; }
done
[ "$changed" = 1 ] || exit 0

if ! command -v "${OPENSPEC:-openspec}" >/dev/null; then
  echo "sdd pre-push: openspec не установлен, проверка пропущена" >&2
  exit 0
fi
echo "sdd pre-push: есть изменения в openspec/, запускаю ci-check.sh" >&2
"$DIR/ci-check.sh" && exit 0
echo "sdd pre-push: проверка не прошла. Исправьте или отправьте без неё: SDD_SKIP=1 git push" >&2
exit 1
