#!/usr/bin/env bash
# CI-проверка для store и репозиториев компонентов. Запуск из корня репозитория.
# В CI store должен быть склонирован и зарегистрирован, если на него есть references:
#   git clone "$STORE_REMOTE" ../store && openspec store register ../store
source "$(dirname "$0")/common.sh"
check_openspec
"$OPENSPEC" validate --all --strict
# Каждый implementation-change в компоненте обязан ссылаться на upstream или быть техническим.
shopt -s nullglob
fail=0
# Имя активного change начинается с ключа Jira (см. SDD_CHANGE_ID_RE в common.sh).
for dir in openspec/changes/*/; do
  id="$(basename "$dir")"
  [ "$id" = "archive" ] && continue
  if ! [[ "$id" =~ $SDD_CHANGE_ID_RE ]]; then
    echo "ERROR: change '$id': имя должно быть <jira-key>-<slug>, например shop-142-add-promo-codes"; fail=1
  fi
done
for meta in openspec/changes/*/.openspec.yaml; do
  if grep -q '^schema: impl-' "$meta" && ! grep -q '^initiative:' "$meta"; then
    echo "ERROR: $meta: impl-change без initiative (ссылки на store)"; fail=1
  fi
done
exit $fail
