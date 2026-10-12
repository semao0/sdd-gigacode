# Общие функции bootstrap-скриптов.
set -euo pipefail
SDD_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Stores в OpenSpec - beta: форматы и флаги могут меняться. Версию фиксируем.
OPENSPEC_PINNED="1.14.1"
OPENSPEC="${OPENSPEC:-openspec}"
# AI-ассистент: gigacode (по умолчанию), qwen, claude и др. - см. `openspec init --help`.
SDD_TOOL="${SDD_TOOL:-gigacode}"
# id change: <ключ Jira в нижнем регистре>-<slug>, например shop-142-add-promo-codes.
# У impl-change к нему добавляется -<component>.
SDD_CHANGE_ID_RE="${SDD_CHANGE_ID_RE:-^[a-z][a-z0-9]*-[0-9]+(-[a-z0-9]+)+$}"

check_openspec() {
  command -v "$OPENSPEC" >/dev/null || { echo "openspec не найден: npm i -g @fission-ai/openspec@$OPENSPEC_PINNED" >&2; exit 1; }
  local v; v="$("$OPENSPEC" --version)"
  [ "$v" = "$OPENSPEC_PINNED" ] || echo "ВНИМАНИЕ: openspec $v, методология проверена на $OPENSPEC_PINNED" >&2
}

copy_skills() { # <kind: store|component> <dest repo>
  # Формат SKILL.md (name + description) одинаков у GigaCode, Qwen Code и Claude Code.
  mkdir -p "$2/.$SDD_TOOL/skills"
  cp -r "$SDD_ROOT/templates/$1/.gigacode/skills/." "$2/.$SDD_TOOL/skills/"
}

copy_schema() { # <schema> <dest repo>
  mkdir -p "$2/openspec/schemas"
  rm -rf "$2/openspec/schemas/$1"
  cp -r "$SDD_ROOT/schemas/$1" "$2/openspec/schemas/$1"
}
