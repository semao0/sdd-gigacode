#!/usr/bin/env bash
# Подключает репозиторий компонента к SDD.
# Использование: bootstrap-component.sh <repo-path> <component-id> <backend|frontend> <store-id> [store-remote]
source "$(dirname "$0")/common.sh"
DIR="$1"; COMP="$2"; KIND="$3"; STORE="$4"; STORE_REMOTE="${5:-}"
case "$KIND" in backend|frontend) ;; *) echo "kind: backend|frontend" >&2; exit 1;; esac
check_openspec
SCHEMA="impl-$KIND"
(cd "$DIR" && "$OPENSPEC" init --tools "$SDD_TOOL" --no-animation . >/dev/null)
copy_schema "$SCHEMA" "$DIR"
sed -e "s/__SCHEMA__/$SCHEMA/" -e "s/__STORE_ID__/$STORE/" -e "s/__COMPONENT__/$COMP/" \
  -e "s|__STORE_REMOTE__|$STORE_REMOTE|" -e "s|__CONTEXT_FILE__|$(context_file)|" \
  "$SDD_ROOT/templates/component/openspec/config.yaml" > "$DIR/openspec/config.yaml"
[ -n "$STORE_REMOTE" ] || sed -i "s|- { id: $STORE, remote: \"\" }|- $STORE|" "$DIR/openspec/config.yaml"
copy_skills component "$DIR"
"$SDD_ROOT/scripts/install-hook.sh" "$DIR" || true
(cd "$DIR" && "$OPENSPEC" doctor) || echo "doctor: зарегистрируйте store: openspec store register <path-to-store>" >&2
[ -f "$DIR/$(context_file)" ] || echo "Нет $(context_file): заведите его - правила проектирования сервиса для агента (см. docs/02-process.md, «Контекст для агента»)." >&2
echo "Компонент '$COMP' подключён к store '$STORE'. Закоммитьте openspec/ и .$SDD_TOOL/."
