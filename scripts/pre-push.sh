#!/usr/bin/env bash
# pre-push: запускает ci-check.sh, если в ветке менялся openspec/ - во всех её коммитах
# относительно main, а не только в отправляемых. Поэтому ошибку, которая уже на сервере
# в этой ветке, хук ловит на каждом следующем push. Остальные push не замедляет.
# Подключается к pre-push хуку скриптом install-hook.sh (его вызывает dev-setup.sh).
set -uo pipefail
[ -n "${SDD_SKIP:-}" ] && { echo "sdd pre-push: SDD_SKIP задан, проверка пропущена" >&2; exit 0; }
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

changed=0
while read -r _lref lsha _rref rsha; do
  [[ "$lsha" =~ ^0+$ ]] && continue                  # удаление ветки
  # база - точка ответвления от main; для push в сам main это origin/main, то есть
  # проверяются неотправленные коммиты. origin/HEAD нет у репо из init + remote add.
  base="$(git merge-base "$lsha" origin/HEAD 2>/dev/null || git merge-base "$lsha" origin/main 2>/dev/null)"
  [ -n "$base" ] || base="$rsha"                     # main не найден - как раньше, от сервера
  [[ "$base" =~ ^0+$ ]] && { changed=1; break; }
  # 1 - есть изменения, 128 - нет коммита локально: в обоих случаях проверяем
  git diff --quiet "$base" "$lsha" -- openspec/ 2>/dev/null || { changed=1; break; }
done
[ "$changed" = 1 ] || exit 0

if ! command -v "${OPENSPEC:-openspec}" >/dev/null; then
  echo "sdd pre-push: openspec не установлен, проверка пропущена" >&2
  exit 0
fi
echo "sdd pre-push: есть изменения в openspec/, запускаю ci-check.sh" >&2
"$DIR/ci-check.sh" && exit 0
echo "sdd pre-push: проверка не прошла. Исправьте и отправьте снова." >&2
exit 1
