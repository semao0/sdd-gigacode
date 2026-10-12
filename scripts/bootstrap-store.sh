#!/usr/bin/env bash
# Создаёт store бизнес-спек.
# Использование: bootstrap-store.sh <store-id> <path> [git-remote]
source "$(dirname "$0")/common.sh"
ID="$1"; DIR="$2"; REMOTE="${3:-}"
check_openspec
"$OPENSPEC" store setup "$ID" --path "$DIR" ${REMOTE:+--remote "$REMOTE"}
(cd "$DIR" && "$OPENSPEC" init --tools "$SDD_TOOL" --no-animation . >/dev/null)
copy_schema business "$DIR"
cp "$SDD_ROOT/templates/store/openspec/config.yaml" "$DIR/openspec/config.yaml"
cp "$SDD_ROOT/templates/store/components.yaml" "$DIR/components.yaml"
copy_skills store "$DIR"
touch "$DIR/openspec/specs/.gitkeep" "$DIR/openspec/changes/archive/.gitkeep"
git -C "$DIR" add -A && git -C "$DIR" commit -qm "chore: SDD store bootstrap" || true
echo "Store '$ID' готов: $DIR. Заполните components.yaml и запушьте."
