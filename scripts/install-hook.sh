#!/usr/bin/env bash
# Подключает SDD-проверку (scripts/pre-push.sh) к pre-push хуку клона store или компонента.
#  - хука нет                         -> ставит свой в .git/hooks (или core.hooksPath);
#  - хук - shell-скрипт               -> вставляет SDD-блок в начало хука. Если хук - копия
#    (Gradle, .githooks/, husky)        файла из репозитория, блок вставляется и в этот файл:
#                                        сборка иначе перезапишет правку. Файл надо закоммитить;
#  - lefthook, не-shell хук           -> ничего не трогает, печатает, что добавить, exit 1.
# Повторный запуск ничего не меняет. Путь к SDD блок берёт из $SDD_HOME или `git config sdd.home`:
# у кого их нет, проверка пропускается, так что коммитить блок в общий хук безопасно.
# Использование: install-hook.sh [repo-path]   (по умолчанию - текущий репозиторий)
source "$(dirname "$0")/common.sh"
DIR="$(cd "${1:-.}" && git rev-parse --show-toplevel)"
HOOKS="$(git -C "$DIR" rev-parse --path-format=absolute --git-path hooks)"   # учитывает core.hooksPath
HOOK="$HOOKS/pre-push"
MARK='# >>> sdd'
# путь к фреймворку для SDD-блока, если в клоне его ещё нет
git -C "$DIR" config sdd.home >/dev/null || git -C "$DIR" config sdd.home "$SDD_ROOT"

block() {
  cat <<'B'
# >>> sdd: проверка openspec/ перед push (см. $SDD_HOME/scripts/install-hook.sh)
_sdd="${SDD_HOME:-$(git config sdd.home 2>/dev/null || true)}"
if [ -x "$_sdd/scripts/pre-push.sh" ]; then
  _sdd_in="$(mktemp)"; cat >"$_sdd_in"
  "$_sdd/scripts/pre-push.sh" "$@" <"$_sdd_in" || { rm -f "$_sdd_in"; exit 1; }
  exec <"$_sdd_in"; rm -f "$_sdd_in"   # stdin git'а - дальше, исходной проверке
fi
# <<< sdd
B
}

is_shell() { # первая строка - shebang sh/bash/zsh/dash/ksh или его нет (husky)
  local l; l="$(head -n1 "$1")"
  [[ "$l" != '#!'* ]] || [[ "$l" =~ ^#!.*(/|env\ +)(ba|z|da|k)?sh([[:space:]]|$) ]]
}

patch() { # вставить блок после shebang
  local f="$1" tmp; tmp="$(mktemp)"
  if [[ "$(head -n1 "$f")" == '#!'* ]]; then
    { head -n1 "$f"; block; tail -n +2 "$f"; } >"$tmp"
  else
    { block; cat "$f"; } >"$tmp"
  fi
  cat "$tmp" >"$f"; rm -f "$tmp"   # cat >, а не mv: сохраняем права и симлинки
}

manual() {
  cat >&2 <<MSG
pre-push хук: $HOOK
$1
Добавьте в начало исходника хука (shell) этот блок:

$(block)
MSG
  exit 1
}

# husky v9: core.hooksPath=.husky/_ - обёртки, сам хук - .husky/pre-push в репозитории
HUSKY=; [[ "$HOOKS" == */.husky/_ ]] && { HUSKY=1; HOOK="$DIR/.husky/pre-push"; [ -e "$HOOK" ] || : >"$HOOK"; }
if [ ! -e "$HOOK" ]; then
  mkdir -p "$HOOKS"
  { echo '#!/bin/sh'; block; } >"$HOOK"; chmod +x "$HOOK"
  echo "pre-push хук установлен: $HOOK"; exit 0
fi
grep -q "$MARK\|scripts/pre-push.sh" "$HOOK" && { echo "pre-push хук уже с SDD: $HOOK"; exit 0; }
grep -q lefthook "$HOOK" && manual "Хук генерирует lefthook. В lefthook.yml добавьте:
  pre-push:
    commands:
      sdd:
        use_stdin: true
        run: '_sdd=\"\${SDD_HOME:-\$(git config sdd.home)}\"; [ -x \"\$_sdd/scripts/pre-push.sh\" ] || exit 0; \"\$_sdd/scripts/pre-push.sh\"'
Или, если хук запускает shell-скрипт из репозитория, - блок ниже в него."

# Исходники хука в репозитории: husky,
# симлинк на файл репозитория, или побайтовая копия отслеживаемого файла (Gradle Copy и т.п.).
SRC=()
real="$(realpath "$HOOK")"
if [ -n "$HUSKY" ]; then
  SRC+=("$HOOK")
elif [[ "$real" == "$DIR"/* && "$real" != "$(git -C "$DIR" rev-parse --path-format=absolute --git-dir)"/* ]]; then
  SRC+=("$real")
else
  h="$(git hash-object "$HOOK")"
  while IFS= read -r f; do SRC+=("$DIR/$f"); done < <(git -C "$DIR" ls-files -s | awk -v h="$h" '$2==h {print $4}')
fi
for f in "$HOOK" "${SRC[@]}"; do
  is_shell "$f" || manual "Хук - не shell-скрипт ($f)."
done

[[ " ${SRC[*]} " == *" $real "* || " ${SRC[*]} " == *" $HOOK "* ]] || patch "$HOOK"
for f in "${SRC[@]}"; do patch "$f"; done
echo "SDD-блок добавлен в pre-push хук: $HOOK"
if [ ${#SRC[@]} -gt 0 ]; then
  printf '  и в его исходник в репозитории - закоммитьте:\n'; printf '    %s\n' "${SRC[@]#$DIR/}"
elif [[ "$HOOK" == "$DIR"/* && "$HOOK" != "$(git -C "$DIR" rev-parse --path-format=absolute --git-dir)"/* ]]; then
  echo "  хук лежит в репозитории - закоммитьте ${HOOK#$DIR/}"
else
  echo "  Если хук генерирует сборка не копированием, правку она перезапишет - добавьте блок в исходник." >&2
fi
