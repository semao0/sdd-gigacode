#!/usr/bin/env bash
# Настройка SDD на машине разработчика: один раз на каждый клон store или компонента.
#  1. проверяет openspec;
#  2. компонент: клонирует (рядом, если нет) и регистрирует store из references в openspec/config.yaml;
#     store: регистрирует сам себя;
#  3. git config sdd.home - путь к этому фреймворку (его читает SDD-блок хука);
#  4. подключает pre-push хук (install-hook.sh: свой, Gradle-копия, husky, .githooks...);
#  5. openspec doctor.
# Повторный запуск безопасен. Использование: dev-setup.sh [repo-path...]   (по умолчанию - текущий)
source "$(dirname "$0")/common.sh"
check_openspec
rc=0

registered() { "$OPENSPEC" store list --json | grep -q "\"id\": *\"$1\""; }

setup_one() {
  local dir; dir="$(cd "$1" && git rev-parse --show-toplevel)" || return 1
  echo "== $dir"
  if [ -d "$dir/.openspec-store" ]; then               # store (повторная регистрация - no-op)
    (cd "$dir" && "$OPENSPEC" store register --yes .) | sed -n 's/^Store registered: /store зарегистрирован: /p'
  elif [ -f "$dir/openspec/config.yaml" ]; then        # компонент
    local line id remote path
    while IFS= read -r line; do
      id="$(sed -nE 's/.*id: *([^,} ]+).*/\1/p; t; s/^ *- *([A-Za-z0-9_-]+) *$/\1/p' <<<"$line")"
      remote="$(sed -nE 's/.*remote: *"?([^"}]*)"?.*/\1/p' <<<"$line")"
      [ -n "$id" ] || continue
      if registered "$id"; then echo "store $id: зарегистрирован"; continue; fi
      [ -n "$remote" ] || { echo "store $id: remote не указан - склонируйте и выполните openspec store register <path>" >&2; rc=1; continue; }
      path="$(dirname "$dir")/$(basename "$remote" .git)"
      [ -d "$path/.git" ] || git clone -q "$remote" "$path"
      "$OPENSPEC" store register --yes "$path" >/dev/null && echo "store $id: склонирован/зарегистрирован - $path"
    done < <(sed -n '/^references:/,/^[^ #-]/p' "$dir/openspec/config.yaml" | grep -E '^ *- ')
  else
    echo "не SDD-репозиторий (нет openspec/config.yaml или components.yaml) - пропускаю" >&2; rc=1; return
  fi
  git -C "$dir" config sdd.home "$SDD_ROOT"   # явно: могли переложить фреймворк
  "$SDD_ROOT/scripts/install-hook.sh" "$dir" || rc=1
  if [ -f "$dir/openspec/config.yaml" ]; then (cd "$dir" && "$OPENSPEC" doctor >/dev/null 2>&1) && echo "openspec doctor: ok" || { echo "openspec doctor: есть проблемы, запустите его в $dir" >&2; rc=1; }; fi
}

[ $# -gt 0 ] || set -- .
for d in "$@"; do setup_one "$d" || rc=1; done
exit $rc
